import streamlit as st
from woocommerce import API
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# ============================================
# 1. Initialize WooCommerce Connection
# ============================================
@st.cache_resource
def init_woocommerce():
    return API(
        url=st.secrets["woocommerce"]["store_url"],
        consumer_key=st.secrets["woocommerce"]["consumer_key"],
        consumer_secret=st.secrets["woocommerce"]["consumer_secret"],
        version="wc/v3",
        timeout=30
    )

# ============================================
# 2. Date Range Calculator Based on Business Rules
# ============================================
def get_business_cycles():
    """
    Calculate the current and previous business cycles based on 5pm cutoff
    Returns: (current_cycle_start, current_cycle_end, previous_cycle_start, previous_cycle_end)
    """
    now = datetime.now()
    
    # Adjust to 5pm cutoff
    if now.hour >= 17:  # After 5pm, current cycle starts today 5pm
        current_cycle_end = now.replace(hour=17, minute=0, second=0, microsecond=0)
        current_cycle_start = current_cycle_end - timedelta(days=1)
    else:  # Before 5pm, current cycle started yesterday 5pm
        current_cycle_end = now.replace(hour=17, minute=0, second=0, microsecond=0) - timedelta(days=1)
        current_cycle_start = current_cycle_end - timedelta(days=1)
    
    # Handle Friday weekend
    # If current_cycle_start or end falls on Friday, adjust to Thursday 5pm
    if current_cycle_start.weekday() == 4:  # Friday
        current_cycle_start = current_cycle_start - timedelta(days=1)
    if current_cycle_end.weekday() == 4:
        current_cycle_end = current_cycle_end - timedelta(days=1)
    
    # Previous cycle (same duration, before current cycle)
    previous_cycle_end = current_cycle_start
    previous_cycle_start = previous_cycle_end - (current_cycle_end - current_cycle_start)
    
    # Handle Friday for previous cycle
    if previous_cycle_start.weekday() == 4:
        previous_cycle_start = previous_cycle_start - timedelta(days=1)
    if previous_cycle_end.weekday() == 4:
        previous_cycle_end = previous_cycle_end - timedelta(days=1)
    
    return current_cycle_start, current_cycle_end, previous_cycle_start, previous_cycle_end

# ============================================
# 3. Fetch Orders with Date Filter
# ============================================
def fetch_orders_by_date_range(start_date, end_date):
    """Fetch orders between start and end dates"""
    wcapi = init_woocommerce()
    all_orders = []
    page = 1
    per_page = 50
    
    # Format dates for WooCommerce API
    start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S")
    end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S")
    
    while True:
        response = wcapi.get("orders", params={
            "after": start_str,
            "before": end_str,
            "page": page,
            "per_page": per_page,
            "orderby": "date_created",
            "order": "asc"
        })
        
        if response.status_code != 200:
            st.error(f"API Error: {response.status_code}")
            break
        
        orders = response.json()
        if not orders:
            break
        
        for order in orders:
            # Calculate total items sold
            total_items = sum(item['quantity'] for item in order['line_items'])
            
            order_data = {
                'order_id': order['id'],
                'order_number': order.get('number', order['id']),
                'status': order['status'],
                'date_created': order['date_created'],
                'total': float(order['total']),
                'total_items': total_items,
                'currency': order['currency']
            }
            all_orders.append(order_data)
        
        total_pages = int(response.headers.get('x-wp-totalpages', 1))
        if page >= total_pages:
            break
        page += 1
    
    return pd.DataFrame(all_orders)

# ============================================
# 4. Calculate Metrics for Order Groups
# ============================================
def calculate_metrics(orders_df, order_type="new"):
    """
    Calculate core metrics from orders DataFrame
    order_type: "new" (processing, on-hold, pending) or "shipped" (completed, shipped)
    """
    if orders_df.empty:
        return {
            'items_sold': 0,
            'num_orders': 0,
            'revenue': 0,
            'basket_value': 0
        }
    
    # Filter by status based on order type
    if order_type == "new":
        filtered_df = orders_df[orders_df['status'].isin(['processing', 'on-hold', 'pending'])]
    else:  # shipped
        filtered_df = orders_df[orders_df['status'].isin(['completed', 'shipped'])]
    
    if filtered_df.empty:
        return {
            'items_sold': 0,
            'num_orders': 0,
            'revenue': 0,
            'basket_value': 0
        }
    
    items_sold = filtered_df['total_items'].sum()
    num_orders = len(filtered_df)
    revenue = filtered_df['total'].sum()
    basket_value = revenue / num_orders if num_orders > 0 else 0
    
    return {
        'items_sold': int(items_sold),
        'num_orders': int(num_orders),
        'revenue': revenue,
        'basket_value': basket_value
    }

# ============================================
# 5. Main Dashboard
# ============================================
st.set_page_config(page_title="Order Analytics Dashboard", layout="wide")
st.title("📊 Order Performance Dashboard")

# Sidebar
st.sidebar.header("📅 Business Cycles")
st.sidebar.info(
    """
    **Business Rules:**
    - 📦 **New Orders**: processing, on-hold, pending
    - 🚚 **Shipped Orders**: completed, shipped
    - ⏰ **Cycle**: 5pm to 5pm (next day)
    - 📴 **Weekend**: Friday (no processing)
    """
)

# Get business cycles
current_start, current_end, previous_start, previous_end = get_business_cycles()

# Display current cycles in sidebar
st.sidebar.write(f"**Current Cycle:**")
st.sidebar.write(f"📅 {current_start.strftime('%Y-%m-%d %I:%M %p')} - {current_end.strftime('%Y-%m-%d %I:%M %p')}")
st.sidebar.write(f"**Previous Cycle:**")
st.sidebar.write(f"📅 {previous_start.strftime('%Y-%m-%d %I:%M %p')} - {previous_end.strftime('%Y-%m-%d %I:%M %p')}")

# Manual override for date range (optional)
use_custom_dates = st.sidebar.checkbox("Use Custom Date Range")
if use_custom_dates:
    col1, col2 = st.sidebar.columns(2)
    with col1:
        custom_start = st.date_input("Start Date", current_start)
    with col2:
        custom_end = st.date_input("End Date", current_end)
    current_start = datetime.combine(custom_start, current_start.time())
    current_end = datetime.combine(custom_end, current_end.time())

# Fetch button
if st.sidebar.button("🔄 Fetch Latest Data", type="primary", use_container_width=True):
    st.cache_data.clear()

# Load data with caching
@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_all_orders():
    current_start, current_end, previous_start, previous_end = get_business_cycles()
    
    with st.spinner("Fetching order data..."):
        current_orders = fetch_orders_by_date_range(current_start, current_end)
        previous_orders = fetch_orders_by_date_range(previous_start, previous_end)
    
    return current_orders, previous_orders, current_start, current_end, previous_start, previous_end

current_orders, previous_orders, cs, ce, ps, pe = load_all_orders()

# Calculate metrics
current_new_metrics = calculate_metrics(current_orders, "new")
current_shipped_metrics = calculate_metrics(current_orders, "shipped")
previous_new_metrics = calculate_metrics(previous_orders, "new")
previous_shipped_metrics = calculate_metrics(previous_orders, "shipped")

# ============================================
# 6. Shipped vs New Orders Comparison Tab
# ============================================
tab1, tab2, tab3 = st.tabs(["📊 Shipped vs New Comparison", "📈 Trends & Analytics", "📋 Raw Order Data"])

with tab1:
    st.header("🚚 Last Shipped vs New Orders Comparison")
    
    # Create comparison cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"📦 Current Cycle\n{cs.strftime('%Y-%m-%d')} to {ce.strftime('%Y-%m-%d')}")
        
        # Shipped Orders Card
        st.markdown("---")
        st.markdown("### 🚚 Shipped Orders")
        shipped_col1, shipped_col2, shipped_col3, shipped_col4 = st.columns(4)
        
        with shipped_col1:
            st.metric(
                "📦 Items Sold",
                f"{current_shipped_metrics['items_sold']:,}",
                delta=f"{current_shipped_metrics['items_sold'] - previous_shipped_metrics['items_sold']}",
                delta_color="normal"
            )
        with shipped_col2:
            st.metric(
                "🆔 Number of Orders",
                f"{current_shipped_metrics['num_orders']:,}",
                delta=f"{current_shipped_metrics['num_orders'] - previous_shipped_metrics['num_orders']}",
                delta_color="normal"
            )
        with shipped_col3:
            st.metric(
                "💰 Revenue",
                f"৳{current_shipped_metrics['revenue']:,.2f}",
                delta=f"৳{current_shipped_metrics['revenue'] - previous_shipped_metrics['revenue']:,.2f}",
                delta_color="normal"
            )
        with shipped_col4:
            st.metric(
                "🛒 Basket Value",
                f"৳{current_shipped_metrics['basket_value']:,.2f}",
                delta=f"৳{current_shipped_metrics['basket_value'] - previous_shipped_metrics['basket_value']:,.2f}",
                delta_color="normal"
            )
        
        # New Orders Card
        st.markdown("### 🆕 New Orders (Processing, Hold, Waiting)")
        new_col1, new_col2, new_col3, new_col4 = st.columns(4)
        
        with new_col1:
            st.metric(
                "📦 Items Sold",
                f"{current_new_metrics['items_sold']:,}",
                delta=f"{current_new_metrics['items_sold'] - previous_new_metrics['items_sold']}",
                delta_color="normal"
            )
        with new_col2:
            st.metric(
                "🆔 Number of Orders",
                f"{current_new_metrics['num_orders']:,}",
                delta=f"{current_new_metrics['num_orders'] - previous_new_metrics['num_orders']}",
                delta_color="normal"
            )
        with new_col3:
            st.metric(
                "💰 Revenue",
                f"৳{current_new_metrics['revenue']:,.2f}",
                delta=f"৳{current_new_metrics['revenue'] - previous_new_metrics['revenue']:,.2f}",
                delta_color="normal"
            )
        with new_col4:
            st.metric(
                "🛒 Basket Value",
                f"৳{current_new_metrics['basket_value']:,.2f}",
                delta=f"৳{current_new_metrics['basket_value'] - previous_new_metrics['basket_value']:,.2f}",
                delta_color="normal"
            )
    
    with col2:
        st.subheader(f"📦 Previous Cycle\n{ps.strftime('%Y-%m-%d')} to {pe.strftime('%Y-%m-%d')}")
        
        # Shipped Orders Card
        st.markdown("---")
        st.markdown("### 🚚 Shipped Orders")
        shipped_col1, shipped_col2, shipped_col3, shipped_col4 = st.columns(4)
        
        with shipped_col1:
            st.metric("📦 Items Sold", f"{previous_shipped_metrics['items_sold']:,}")
        with shipped_col2:
            st.metric("🆔 Number of Orders", f"{previous_shipped_metrics['num_orders']:,}")
        with shipped_col3:
            st.metric("💰 Revenue", f"৳{previous_shipped_metrics['revenue']:,.2f}")
        with shipped_col4:
            st.metric("🛒 Basket Value", f"৳{previous_shipped_metrics['basket_value']:,.2f}")
        
        # New Orders Card
        st.markdown("### 🆕 New Orders (Processing, Hold, Waiting)")
        new_col1, new_col2, new_col3, new_col4 = st.columns(4)
        
        with new_col1:
            st.metric("📦 Items Sold", f"{previous_new_metrics['items_sold']:,}")
        with new_col2:
            st.metric("🆔 Number of Orders", f"{previous_new_metrics['num_orders']:,}")
        with new_col3:
            st.metric("💰 Revenue", f"৳{previous_new_metrics['revenue']:,.2f}")
        with new_col4:
            st.metric("🛒 Basket Value", f"৳{previous_new_metrics['basket_value']:,.2f}")
    
    # Comparison Charts
    st.markdown("---")
    st.subheader("📊 Visual Comparison")
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        # Bar chart for comparisons
        comparison_data = pd.DataFrame({
            'Metric': ['Items Sold', 'Number of Orders', 'Revenue (Tk)', 'Basket Value (Tk)'],
            'Current Shipped': [
                current_shipped_metrics['items_sold'],
                current_shipped_metrics['num_orders'],
                current_shipped_metrics['revenue'],
                current_shipped_metrics['basket_value']
            ],
            'Previous Shipped': [
                previous_shipped_metrics['items_sold'],
                previous_shipped_metrics['num_orders'],
                previous_shipped_metrics['revenue'],
                previous_shipped_metrics['basket_value']
            ]
        })
        
        fig = go.Figure(data=[
            go.Bar(name='Current Cycle', x=comparison_data['Metric'], y=comparison_data['Current Shipped']),
            go.Bar(name='Previous Cycle', x=comparison_data['Metric'], y=comparison_data['Previous Shipped'])
        ])
        fig.update_layout(title="Shipped Orders Comparison", barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    
    with chart_col2:
        # New orders comparison chart
        new_comparison = pd.DataFrame({
            'Metric': ['Items Sold', 'Number of Orders', 'Revenue (Tk)', 'Basket Value (Tk)'],
            'Current New': [
                current_new_metrics['items_sold'],
                current_new_metrics['num_orders'],
                current_new_metrics['revenue'],
                current_new_metrics['basket_value']
            ],
            'Previous New': [
                previous_new_metrics['items_sold'],
                previous_new_metrics['num_orders'],
                previous_new_metrics['revenue'],
                previous_new_metrics['basket_value']
            ]
        })
        
        fig2 = go.Figure(data=[
            go.Bar(name='Current Cycle', x=new_comparison['Metric'], y=new_comparison['Current New']),
            go.Bar(name='Previous Cycle', x=new_comparison['Metric'], y=new_comparison['Previous New'])
        ])
        fig2.update_layout(title="New Orders Comparison", barmode='group')
        st.plotly_chart(fig2, use_container_width=True)

with tab2:
    st.header("📈 Trends & Analytics")
    
    # Prepare data for trends
    if not current_orders.empty:
        current_orders['date'] = pd.to_datetime(current_orders['date_created']).dt.date
        daily_shipped = current_orders[current_orders['status'].isin(['completed', 'shipped'])].groupby('date').agg({
            'total': 'sum',
            'total_items': 'sum',
            'order_id': 'count'
        }).reset_index()
        daily_shipped.columns = ['Date', 'Revenue', 'Items Sold', 'Orders']
        
        st.subheader("Daily Shipped Orders Trend")
        col1, col2 = st.columns(2)
        
        with col1:
            st.line_chart(daily_shipped.set_index('Date')['Orders'])
        with col2:
            st.line_chart(daily_shipped.set_index('Date')['Revenue'])
        
        # Status distribution
        st.subheader("Order Status Distribution")
        status_counts = current_orders['status'].value_counts()
        fig_pie = px.pie(values=status_counts.values, names=status_counts.index, title="Current Cycle Order Status")
        st.plotly_chart(fig_pie, use_container_width=True)

with tab3:
    st.header("📋 Raw Order Data")
    
    # Display orders table
    if not current_orders.empty:
        st.dataframe(
            current_orders,
            column_config={
                "order_id": "Order ID",
                "order_number": "Order #",
                "status": "Status",
                "date_created": "Date Created",
                "total": st.column_config.NumberColumn("Total (Tk)", format="৳%.2f"),
                "total_items": "Items",
                "currency": "Currency"
            },
            use_container_width=True,
            height=400
        )
        
        # Export option
        csv = current_orders.to_csv(index=False)
        st.download_button(
            label="📥 Download Current Cycle Orders",
            data=csv,
            file_name=f"orders_{cs.strftime('%Y%m%d')}_to_{ce.strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No orders found in current cycle")

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

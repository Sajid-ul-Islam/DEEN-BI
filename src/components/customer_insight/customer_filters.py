"""Customer filters component - uses EXISTING working data.

Provides UI controls for filtering customers by:
- Product purchases (multi-select from existing data)
- Total purchase amount range
- Total order count range

Note: Date range is controlled globally from the sidebar.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any, Callable

import streamlit as st
import pandas as pd

from BackEnd.core.logging_config import get_logger


logger = get_logger("customer_filters")


def _get_products_from_sales_data() -> pd.DataFrame:
    """Extract unique products from existing sales data in session state.
    
    Returns:
        DataFrame with product_id and name columns
    """
    if "dashboard_data" not in st.session_state:
        return pd.DataFrame()
    
    sales_df = st.session_state.dashboard_data.get("sales_exec", pd.DataFrame())
    if sales_df.empty:
        return pd.DataFrame()
    
    # Extract unique products from sales data
    if "item_name" in sales_df.columns and "sku" in sales_df.columns:
        products = sales_df[["item_name", "sku"]].drop_duplicates()
        products.columns = ["name", "product_id"]
        return products
    
    return pd.DataFrame()


def render_customer_filters(
    on_filter_change: Optional[Callable[[Dict[str, Any]], None]] = None,
    key_prefix: str = "ci_filters",
) -> Dict[str, Any]:
    """Render customer filter controls - HORIZONTAL LAYOUT.
    
    Args:
        on_filter_change: Optional callback when filters change
        key_prefix: Prefix for Streamlit session state keys
        
    Returns:
        Dictionary with filter values
    """
    st.caption("All filters work together with AND logic. Adjust and click Apply.")
    st.info("📅 Date range is controlled from the global sidebar (Business Intelligence > Custom Date Range)")
    
    # Initialize session state defaults
    if f"{key_prefix}_min_amount" not in st.session_state:
        st.session_state[f"{key_prefix}_min_amount"] = 0
    if f"{key_prefix}_max_amount" not in st.session_state:
        st.session_state[f"{key_prefix}_max_amount"] = 1000000
    if f"{key_prefix}_amount_select" not in st.session_state:
        st.session_state[f"{key_prefix}_amount_select"] = "Any amount"
    if f"{key_prefix}_min_orders" not in st.session_state:
        st.session_state[f"{key_prefix}_min_orders"] = 1
    if f"{key_prefix}_max_orders" not in st.session_state:
        st.session_state[f"{key_prefix}_max_orders"] = 1000
    if f"{key_prefix}_orders_select" not in st.session_state:
        st.session_state[f"{key_prefix}_orders_select"] = "Any (1 or more)"
    if f"{key_prefix}_filter_mode" not in st.session_state:
        st.session_state[f"{key_prefix}_filter_mode"] = "Customer total within range"
    # Note: Date range comes from global sidebar (wc_sync_start_date, wc_sync_end_date)
    
    # ROW 1: Products selector (full width for multiselect)
    st.markdown("**📦 Products**")
    st.caption("Leave empty to include all products")
    products_df = _get_products_from_sales_data()
    
    if products_df.empty:
        st.info("ℹ️ Load sales data from dashboard to filter by products.")
        selected_product_ids = []
    else:
        product_options = {f"{row['name']}": row["product_id"] for _, row in products_df.iterrows()}
        selected_products = st.multiselect(
            "Select products",
            options=list(product_options.keys()),
            default=st.session_state.get(f"{key_prefix}_products", []),
            key=f"{key_prefix}_products_select",
            placeholder="Leave empty for all products, or select specific ones...",
            label_visibility="collapsed",
        )
        selected_product_ids = [product_options[p] for p in selected_products] if selected_products else []
        st.session_state[f"{key_prefix}_products"] = selected_products
    
    # ROW 2: Filter Mode (full width)
    st.markdown("**🎯 Filter Mode**")
    st.caption("Choose how Amount and Order filters are applied")
    filter_mode = st.radio(
        "Filter mode",
        options=[
            "Customer total within range",
            "Customer has at least one order in range"
        ],
        index=0,
        key=f"{key_prefix}_filter_mode_radio",
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state[f"{key_prefix}_filter_mode"] = filter_mode
    
    if filter_mode == "Customer total within range":
        st.caption("✅ Only customers whose TOTAL spending/orders are within the selected range")
    else:
        st.caption("✅ Customers who have AT LEAST ONE order within the selected range (may have others outside)")
    
    # ROW 3: Amount and Order Count (2 columns)
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**💰 Amount (৳)**")
        st.caption("Select minimum amount")
        
        # Dropdown for amount selection
        amount_options = [
            "Any amount",
            "Up to ৳1000",
            "Up to ৳1500",
            "Up to ৳2000",
            "Up to ৳2500",
            "Up to ৳3000",
            "Up to ৳3500",
            "Up to ৳4000",
            "Up to ৳5000",
            "Up to ৳7000",
            "Up to ৳10000",
            "Custom range..."
        ]
        
        selected_amount_option = st.selectbox(
            "Amount range",
            options=amount_options,
            index=0,
            key=f"{key_prefix}_amount_select",
            label_visibility="collapsed",
        )
        
        # Set min/max based on selection
        if selected_amount_option == "Any amount":
            min_amount, max_amount = 0, 10000000
        elif selected_amount_option == "Up to ৳1000":
            min_amount, max_amount = 0, 1000
        elif selected_amount_option == "Up to ৳1500":
            min_amount, max_amount = 0, 1500
        elif selected_amount_option == "Up to ৳2000":
            min_amount, max_amount = 0, 2000
        elif selected_amount_option == "Up to ৳2500":
            min_amount, max_amount = 0, 2500
        elif selected_amount_option == "Up to ৳4300":
            min_amount, max_amount = 0, 4300
        else:  # Custom range
            c1, c2 = st.columns(2)
            with c1:
                min_amount = st.number_input(
                    "Min ৳",
                    min_value=0,
                    max_value=1000000,
                    value=st.session_state.get(f"{key_prefix}_min_amount", 0),
                    step=100,
                    key=f"{key_prefix}_min_amount_custom",
                )
            with c2:
                max_amount = st.number_input(
                    "Max ৳",
                    min_value=0,
                    max_value=10000000,
                    value=st.session_state.get(f"{key_prefix}_max_amount", 1000000),
                    step=1000,
                    key=f"{key_prefix}_max_amount_custom",
                )
        
        st.session_state[f"{key_prefix}_min_amount"] = min_amount
        st.session_state[f"{key_prefix}_max_amount"] = max_amount
        st.session_state[f"{key_prefix}_amount_min"] = min_amount
        st.session_state[f"{key_prefix}_amount_max"] = max_amount
    
    with col2:
        st.markdown("**📊 Orders**")
        st.caption("Select order count range")
        
        # Dropdown for order count selection
        order_options = [
            "Any (1 or more)",
            "Exactly 1",
            "Exactly 2",
            "Exactly 3",
            "More than 3",
            "Custom range..."
        ]
        
        selected_order_option = st.selectbox(
            "Order count",
            options=order_options,
            index=0,
            key=f"{key_prefix}_orders_select",
            label_visibility="collapsed",
        )
        
        # Set min/max based on selection
        if selected_order_option == "Any (1 or more)":
            min_orders, max_orders = 1, 50
        elif selected_order_option == "Exactly 1":
            min_orders, max_orders = 1, 1
        elif selected_order_option == "Exactly 2":
            min_orders, max_orders = 2, 2
        elif selected_order_option == "Exactly 3":
            min_orders, max_orders = 3, 3
        elif selected_order_option == "More than 3":
            min_orders, max_orders = 4, 50
        else:  # Custom range
            c1, c2 = st.columns(2)
            with c1:
                min_orders = st.number_input(
                    "Min",
                    min_value=1,
                    max_value=1000,
                    value=st.session_state.get(f"{key_prefix}_min_orders", 1),
                    step=1,
                    key=f"{key_prefix}_min_orders_custom",
                )
            with c2:
                max_orders = st.number_input(
                    "Max",
                    min_value=1,
                    max_value=10000,
                    value=st.session_state.get(f"{key_prefix}_max_orders", 1000),
                    step=10,
                    key=f"{key_prefix}_max_orders_custom",
                )
        
        st.session_state[f"{key_prefix}_min_orders"] = min_orders
        st.session_state[f"{key_prefix}_max_orders"] = max_orders
        st.session_state[f"{key_prefix}_orders_min"] = min_orders
        st.session_state[f"{key_prefix}_orders_max"] = max_orders
    
    # Note: Date range is controlled by global sidebar (Business Intelligence > Custom Date Range)
    # The data is pre-filtered before reaching Customer Insight
    
    # ROW 3: Action Buttons
    st.markdown("---")
    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
    
    with btn_col1:
        apply_clicked = st.button(
            "✅ Apply Filters",
            type="primary",
            use_container_width=True,
            key=f"{key_prefix}_apply",
        )
    
    with btn_col2:
        reset_clicked = st.button(
            "🔄 Reset",
            use_container_width=True,
            key=f"{key_prefix}_reset",
        )
    
    with btn_col3:
        st.caption("📊 Uses existing dashboard data")
    
    if reset_clicked:
        keys_to_clear = [
            f"{key_prefix}_products",
            f"{key_prefix}_min_amount",
            f"{key_prefix}_max_amount",
            f"{key_prefix}_amount_select",
            f"{key_prefix}_amount_min",
            f"{key_prefix}_amount_max",
            f"{key_prefix}_min_orders",
            f"{key_prefix}_max_orders",
            f"{key_prefix}_orders_select",
            f"{key_prefix}_orders_min",
            f"{key_prefix}_orders_max",
            f"{key_prefix}_filter_mode",
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    # Build filter result (date range comes from global sidebar, not local filters)
    filter_mode = st.session_state.get(f"{key_prefix}_filter_mode", "Customer total within range")
    filters = {
        "selected_products": selected_product_ids if 'selected_product_ids' in locals() else [],
        "min_amount": st.session_state.get(f"{key_prefix}_min_amount", 0),
        "max_amount": st.session_state.get(f"{key_prefix}_max_amount", 1000000),
        "min_orders": st.session_state.get(f"{key_prefix}_min_orders", 1),
        "max_orders": st.session_state.get(f"{key_prefix}_max_orders", 1000),
        "filter_mode": filter_mode,
        "applied": apply_clicked,
    }
    
    # Auto-apply if callback provided and filters changed
    if on_filter_change and apply_clicked:
        on_filter_change(filters)
    
    return filters


def apply_customer_filters(
    orders_df: pd.DataFrame,
    filters: Dict[str, Any],
) -> pd.DataFrame:
    """Apply filter criteria to orders DataFrame using EXISTING data.
    
    Args:
        orders_df: DataFrame with orders data from session state
        filters: Filter criteria from render_customer_filters()
        
    Returns:
        Filtered DataFrame with unique customers
    """
    if orders_df.empty:
        return pd.DataFrame()
    
    df = orders_df.copy()
    
    # Note: Date range filtering is handled globally in the sidebar
    # The data in dashboard_data is already filtered by the global date range
    
    filter_mode = filters.get("filter_mode", "Customer total within range")
    
    # Get unique customers who qualify based on filter mode
    if filter_mode == "Customer has at least one order in range" and "order_total" in df.columns:
        # MODE 2: Customer has at least one order in the specified range
        # First, get unique orders with their totals
        unique_orders = df.drop_duplicates(subset=["order_id"]).copy()
        
        # Apply amount filter to unique orders
        min_amt = filters.get("min_amount", 0)
        max_amt = filters.get("max_amount", 10000000)
        
        if min_amt > 0:
            unique_orders = unique_orders[unique_orders["order_total"] >= min_amt]
        if max_amt < 10000000:
            unique_orders = unique_orders[unique_orders["order_total"] <= max_amt]
        
        # Get customers who have at least one qualifying order
        qualifying_customers = unique_orders["customer_key"].unique()
        
        # Filter original df to only these customers
        df = df[df["customer_key"].isin(qualifying_customers)]
        
        # Apply product filter
        if filters.get("selected_products") and "item_name" in df.columns:
            product_filter = df["sku"].isin(filters["selected_products"]) if "sku" in df.columns else False
            if "item_name" in df.columns:
                product_names = [p.lower() for p in filters["selected_products"]]
                name_filter = df["item_name"].str.lower().isin(product_names)
                product_filter = product_filter | name_filter
            df = df[product_filter]
        
        # For orders count in this mode, we count only qualifying orders per customer
        qualifying_order_ids = unique_orders["order_id"].unique()
        df_filtered = df[df["order_id"].isin(qualifying_order_ids)]
        
        # Aggregate to customer level from filtered data
        from BackEnd.services.customer_insights import generate_customer_insights_from_sales
        customers_df = generate_customer_insights_from_sales(df_filtered, include_rfm=True)
        
        # Apply order count filter on qualifying orders only
        min_ord = filters.get("min_orders", 1)
        max_ord = filters.get("max_orders", 10000)
        
        if min_ord > 1:
            customers_df = customers_df[customers_df["total_orders"] >= min_ord]
        if max_ord < 10000:
            customers_df = customers_df[customers_df["total_orders"] <= max_ord]
        
        return customers_df
    
    # MODE 1: Customer total within range (default behavior)
    # 1. Apply product filter (match by item_name or sku)
    if filters.get("selected_products") and "item_name" in df.columns:
        product_filter = df["sku"].isin(filters["selected_products"]) if "sku" in df.columns else False
        if "item_name" in df.columns:
            # Also check item names for partial matches
            product_names = [p.lower() for p in filters["selected_products"]]
            name_filter = df["item_name"].str.lower().isin(product_names)
            product_filter = product_filter | name_filter
        df = df[product_filter]
    
    # 2. Aggregate to customer level
    from BackEnd.services.customer_insights import generate_customer_insights_from_sales
    customers_df = generate_customer_insights_from_sales(df, include_rfm=True)
    
    # Rename columns for consistency
    if "customer_id" in customers_df.columns and "customer_key" not in customers_df.columns:
        customers_df["customer_key"] = customers_df["customer_id"]
    if "primary_name" in customers_df.columns and "name" not in customers_df.columns:
        customers_df["name"] = customers_df["primary_name"]
    if "total_revenue" in customers_df.columns and "total_value" not in customers_df.columns:
        customers_df["total_value"] = customers_df["total_revenue"]
    
    # 3. Apply amount filter
    if filters.get("min_amount", 0) > 0:
        customers_df = customers_df[customers_df["total_value"] >= filters["min_amount"]]
    
    if filters.get("max_amount") and filters["max_amount"] < 10000000:
        customers_df = customers_df[customers_df["total_value"] <= filters["max_amount"]]
    
    # 4. Apply order count filter
    if filters.get("min_orders", 1) > 1:
        customers_df = customers_df[customers_df["total_orders"] >= filters["min_orders"]]
    
    if filters.get("max_orders") and filters["max_orders"] < 10000:
        customers_df = customers_df[customers_df["total_orders"] <= filters["max_orders"]]
    
    logger.info(f"Filtered to {len(customers_df)} customers from {len(orders_df)} orders")
    
    return customers_df


def get_filtered_customers_summary(filters: Dict[str, Any]) -> pd.DataFrame:
    """Get filtered customer summary using EXISTING session state data.
    
    Args:
        filters: Filter criteria dictionary
        
    Returns:
        DataFrame with filtered customer summaries
    """
    # Use EXISTING working data from session state
    if "dashboard_data" not in st.session_state:
        return pd.DataFrame()
    
    sales_df = st.session_state.dashboard_data.get("sales_exec", pd.DataFrame())
    
    if sales_df.empty:
        return pd.DataFrame()
    
    return apply_customer_filters(sales_df, filters)

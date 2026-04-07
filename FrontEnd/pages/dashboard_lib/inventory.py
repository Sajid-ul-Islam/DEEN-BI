import re
from datetime import datetime
import pandas as pd
import streamlit as st
import plotly.express as px
from FrontEnd.components import ui

def get_category(name):
    """Categorizes products based on keywords in their names (v9.5 Expert Rules)."""
    name_str = str(name).lower()

    def has_any(keywords, text):
        return any(
            re.search(rf"\b{re.escape(kw.lower())}\b", text, re.IGNORECASE)
            for kw in keywords
        )

    specific_cats = {
        "Tank Top": ["tank top"],
        "Boxer": ["boxer"],
        "Jeans": ["jeans"],
        "Denim Shirt": ["denim"],
        "Flannel Shirt": ["flannel"],
        "Polo Shirt": ["polo"],
        "Panjabi": ["panjabi", "punjabi"],
        "Trousers": ["trousers", "trouser"],
        "Joggers": ["joggers", "jogger", "track pant"],
        "Twill Chino": ["twill chino", "chino", "twill"],
        "Mask": ["mask"],
        "Leather Bag": ["bag", "backpack"],
        "Water Bottle": ["water bottle"],
        "Contrast Shirt": ["contrast"],
        "Turtleneck": ["turtleneck", "mock neck"],
        "Drop Shoulder": ["drop", "shoulder"],
        "Wallet": ["wallet"],
        "Kaftan Shirt": ["kaftan"],
        "Active Wear": ["active wear"],
        "Jersy": ["jersy"],
        "Sweatshirt": ["sweatshirt", "hoodie", "pullover"],
        "Jacket": ["jacket", "outerwear", "coat"],
        "Belt": ["belt"],
        "Sweater": ["sweater", "cardigan", "knitwear"],
        "Passport Holder": ["passport holder"],
        "Card Holder": ["card holder"],
        "Cap": ["cap"],
    }

    for cat, keywords in specific_cats.items():
        if has_any(keywords, name_str):
            return cat

    fs_keywords = ["full sleeve", "long sleeve", "fs", "l/s"]
    if has_any(["t-shirt", "t shirt", "tee"], name_str):
        return "FS T-Shirt" if has_any(fs_keywords, name_str) else "HS T-Shirt"

    if has_any(["shirt"], name_str):
        return "FS Shirt" if has_any(fs_keywords, name_str) else "HS Shirt"

    return "Others"


def render_inventory_health(stock_df: pd.DataFrame, forecast_df: pd.DataFrame):
    st.subheader("Inventory Health")
    if stock_df is None or stock_df.empty:
        st.info("No live stock snapshot is available yet.")
        return
    inventory = stock_df.copy()
    
    # Initialize missing pillars if the local cache is stale
    for col in ["Regular Price", "Sale Price", "Price"]:
        if col not in inventory.columns:
            inventory[col] = 0.0
            
    inventory["Stock Quantity"] = pd.to_numeric(inventory.get("Stock Quantity", 0), errors="coerce").fillna(0)
    inventory["Price"] = pd.to_numeric(inventory.get("Price", 0), errors="coerce").fillna(0)
    inventory["Value"] = inventory["Stock Quantity"] * inventory["Price"]
    
    # Apply v9.5 Expert Categorization
    if "Name" in inventory.columns:
        inventory["Category"] = inventory["Name"].apply(get_category)
    
    low_stock = inventory[inventory["Stock Quantity"] <= 5]
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Products", f"{len(inventory):,}")
    with m2: st.metric("Low Stock", f"{len(low_stock):,}")
    with m3: st.metric("Inventory Value", f"TK {inventory['Value'].sum():,.0f}")
    
    st.markdown("#### Inventory Strategic Analysis")
    if "Category" in inventory.columns:
        # 1. Advanced Value Calculations
        inventory["Regular Price"] = pd.to_numeric(inventory.get("Regular Price", 0), errors="coerce").fillna(0)
        inventory["Sale Price"] = pd.to_numeric(inventory.get("Sale Price", 0), errors="coerce").fillna(0)
        inventory["Regular Value"] = inventory["Stock Quantity"] * inventory["Regular Price"]
        inventory["Sale Value"] = inventory["Stock Quantity"] * inventory["Sale Price"]

        # 2. Controls for dynamic visualization
        c_filter1, c_filter2 = st.columns([1, 2])
        with c_filter1:
            val_basis = st.radio(
                "Value Basis", 
                ["Market Value", "Regular Value", "Sale Value"], 
                index=0,
                horizontal=True
            )
        
        val_col_map = {
            "Market Value": "Value",
            "Regular Value": "Regular Value",
            "Sale Value": "Sale Value"
        }
        val_col = val_col_map.get(val_basis, "Value")

        # 3. Data Preparation
        cat_agg = inventory.groupby("Category").agg(
            Selected_Value=(val_col, "sum"),
            Total_Units=("Stock Quantity", "sum"),
            SKU_Count=("Name", "count")
        ).reset_index().sort_values("Selected_Value", ascending=False).head(12)
        
        # 4. Interactive Visuals
        t1, t2 = st.tabs(["💰 Value Distribution", "📦 Volume Analysis"])
        
        with t1:
            v1, v2 = st.columns(2)
            with v1:
                # Value Share Donut
                fig_donut = ui.donut_chart(
                    cat_agg, values="Selected_Value", names="Category", 
                    title=f"Category Share by {val_basis}"
                )
                st.plotly_chart(fig_donut, use_container_width=True)
            with v2:
                # Value Bar Chart (High Level)
                fig_val_bar = ui.bar_chart(
                    cat_agg, x="Selected_Value", y="Category",
                    title=f"Absolute {val_basis} per Category",
                    color="Selected_Value", color_scale="Viridis"
                )
                st.plotly_chart(fig_val_bar, use_container_width=True)
                
        with t2:
            v3, v4 = st.columns(2)
            with v3:
                # Unit Volume Bar Chart
                fig_unit_bar = ui.bar_chart(
                    cat_agg.sort_values("Total_Units", ascending=False), 
                    x="Total_Units", y="Category", 
                    title="Total Unit Volume per Category",
                    color="Total_Units", color_scale="Tealgrn"
                )
                st.plotly_chart(fig_unit_bar, use_container_width=True)
            with v4:
                # SKU Complexity Bar Chart
                fig_sku_bar = ui.bar_chart(
                    cat_agg.sort_values("SKU_Count", ascending=False), 
                    x="SKU_Count", y="Category", 
                    title="SKU Breadth per Category",
                    color="SKU_Count", color_scale="Purples"
                )
                st.plotly_chart(fig_sku_bar, use_container_width=True)
    else:
        st.info("Category-wise breakdown is not yet available in the stock cache.")
        
    st.markdown("---")
    
    # 3. Report Summary & Download
    d1, d2 = st.columns([2, 1])
    with d1:
        st.markdown("#### Complete Inventory Snapshot")
        st.caption("Includes all published products across the entire store catalog.")
    with d2:
        excel_bytes = ui.export_to_excel(inventory, "Inventory Health Report")
        st.download_button(
            label="📊 Download Full Report",
            data=excel_bytes,
            file_name=f"deen_inventory_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

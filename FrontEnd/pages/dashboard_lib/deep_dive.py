import pandas as pd
import streamlit as st
import plotly.express as px
from FrontEnd.components import ui
from BackEnd.core.categories import parse_sku_variants, get_clean_product_name, get_master_category_list, format_category_label, get_subcategory_name, classify_velocity_trend, get_densed_name
from BackEnd.core.geo import get_region_display
from FrontEnd.utils.key_manager import KeyManager
from datetime import date, timedelta

def render_deep_dive_tab(df_sales: pd.DataFrame, stock_df: pd.DataFrame, df_prev: pd.DataFrame = None, window_label: str = "period"):

    if "_variant_parsed" not in df_sales.columns:
        parsed_variants = df_sales["item_name"].apply(parse_sku_variants).tolist()
        df_sales["_color"] = [p[0] for p in parsed_variants]
        df_sales["_size"] = [p[1] for p in parsed_variants]
        df_sales["_clean_name"] = df_sales["item_name"].apply(get_clean_product_name)
        
        df_sales["_densed_name"] = df_sales.apply(lambda x: get_densed_name(x["_clean_name"], x["Category"]), axis=1)
        df_sales["_variant_parsed"] = True
        
    if df_prev is not None and not df_prev.empty and "_variant_parsed" not in df_prev.columns:
        parsed_variants_prev = df_prev["item_name"].apply(parse_sku_variants).tolist()
        df_prev["_color"] = [p[0] for p in parsed_variants_prev]
        df_prev["_size"] = [p[1] for p in parsed_variants_prev]
        df_prev["_clean_name"] = df_prev["item_name"].apply(get_clean_product_name)
        df_prev["_densed_name"] = df_prev.apply(lambda x: get_densed_name(x["_clean_name"], x["Category"]), axis=1)
        df_prev["_variant_parsed"] = True

    # --- Trend Type Logic ---
    # Calculate velocity based on current window length
    days_active = (df_sales["order_date"].max() - df_sales["order_date"].min()).days or 1
    v_agg = df_sales.groupby("item_name")["qty"].sum().reset_index()
    v_agg["v_rate"] = v_agg["qty"] / days_active
    
    v_agg["Trend"] = classify_velocity_trend(v_agg["v_rate"])
    if "Trend" not in df_sales.columns:
        df_sales = df_sales.merge(v_agg[["item_name", "Trend"]], on="item_name", how="left")

    # --- Campaign / Coupon logic ---
    if "Coupons" not in df_sales.columns:
        df_sales["Coupons"] = "None"

    # Map precise regions via core geography engine
    df_sales["_region_display"] = df_sales.apply(lambda x: get_region_display(x.get("city", ""), x.get("state", "")), axis=1)

    # MAIN UI LAYOUT
    st.markdown("### 📥 Sales Data Ingestion & Analysis")
    st.caption("Perform high-resolution segment analysis to identify operational opportunities and regional hotspots.")
    
    clean_window = window_label.replace('last ', '').title() if window_label else "Period"

    # CATEGORY PERFORMANCE MATRIX
    c_mat1, c_mat2 = st.columns([3, 1])
    with c_mat1:
        st.markdown("**📊 Category Performance Matrix**")
        st.caption(f"Categories ranked by revenue, comparing current vs previous {clean_window.lower()}.")
    with c_mat2:
        show_master_only = st.toggle("Show Master Category Only", value=False, key=KeyManager.get_key("deep_dive", "cat_matrix_toggle"))

    display_df = pd.DataFrame()
    if not df_sales.empty:
        # Safely cross-reference return loss per line item to calculate category Net Yield
        if "Return_Loss" not in df_sales.columns:
            returns_df = st.session_state.get("returns_data", pd.DataFrame())
            if returns_df.empty:
                try:
                    from FrontEnd.pages.dashboard_lib.returns_tracker import _get_returns_data_with_daily_cache
                    from BackEnd.services.returns_tracker import get_current_sync_window
                    sync_window = get_current_sync_window()
                    returns_df = _get_returns_data_with_daily_cache(sync_window=sync_window, sales_df_full=df_sales)
                    st.session_state["returns_data"] = returns_df
                except Exception:
                    pass
                    
            order_sku_returns = {}
            order_sku_returns_qty = {}
            order_sku_exchanges = {}
            if not returns_df.empty and "order_id" in returns_df.columns:
                for _, r_row in returns_df.iterrows():
                    issue_type = r_row.get("issue_type")
                    if issue_type in ["Paid Return", "Non Paid Return", "Partial"]:
                        items = r_row.get("returned_items", [])
                        oid = str(r_row.get("order_id", "")).strip()
                        if hasattr(items, "tolist"): items = items.tolist()
                        if isinstance(items, list):
                            for item in items:
                                if isinstance(item, dict):
                                    sku = str(item.get("sku", "N/A")).strip().upper()
                                    impact = float(item.get("revenue_impact", 0) or 0.0)
                                    qty = int(pd.to_numeric(item.get("qty", 1), errors="coerce") or 1)
                                    key = f"{oid}_{sku}"
                                    order_sku_returns[key] = order_sku_returns.get(key, 0.0) + impact
                                    order_sku_returns_qty[key] = order_sku_returns_qty.get(key, 0) + qty
                    elif issue_type == "Exchange":
                        items = r_row.get("returned_items", [])
                        oid = str(r_row.get("order_id", "")).strip()
                        if hasattr(items, "tolist"): items = items.tolist()
                        if isinstance(items, list):
                            for item in items:
                                if isinstance(item, dict):
                                    sku = str(item.get("sku", "N/A")).strip().upper()
                                    qty = int(pd.to_numeric(item.get("qty", 1), errors="coerce") or 1)
                                    key = f"{oid}_{sku}"
                                    order_sku_exchanges[key] = order_sku_exchanges.get(key, 0) + qty
            
            keys = df_sales["order_id"].astype(str).str.strip() + "_" + df_sales.get("sku", "").astype(str).str.strip().str.upper()
            df_sales["Return_Loss"] = keys.map(order_sku_returns).fillna(0.0)
            df_sales["Returned_Qty"] = keys.map(order_sku_returns_qty).fillna(0.0)
            df_sales["Exchanged_Qty"] = keys.map(order_sku_exchanges).fillna(0.0)

        df_sales_matrix = df_sales.copy()
        
        # Remove bundles (Combo, Choose Any, etc.) from the performance matrix
        df_sales_matrix = df_sales_matrix[~df_sales_matrix["Category"].astype(str).str.contains("Bundle", case=False, na=False)]
        
        if show_master_only:
            df_sales_matrix["Category"] = df_sales_matrix["Category"].apply(lambda x: str(x).split(" - ")[0] if " - " in str(x) else str(x))

        curr_agg = df_sales_matrix.groupby("Category").agg(
            Total_Sold=("qty", "sum"),
            Total_Revenue=("item_revenue", "sum"),
            Return_Loss=("Return_Loss", "sum"),
            Returned_Qty=("Returned_Qty", "sum"),
            Exchanged_Qty=("Exchanged_Qty", "sum")
        ).reset_index()
        curr_agg["ASP"] = (curr_agg["Total_Revenue"] / curr_agg["Total_Sold"].replace(0, 1)).fillna(0)
        curr_agg["Net_Yield"] = ((curr_agg["Total_Revenue"] - curr_agg["Return_Loss"]) / curr_agg["Total_Revenue"].replace(0, 1) * 100).fillna(100).clip(lower=0, upper=100)
        
        if df_prev is not None and not df_prev.empty:
            df_prev_matrix = df_prev.copy()
            
            # Remove bundles (Combo, Choose Any, etc.) from the performance matrix
            df_prev_matrix = df_prev_matrix[~df_prev_matrix["Category"].astype(str).str.contains("Bundle", case=False, na=False)]
            
            if show_master_only:
                df_prev_matrix["Category"] = df_prev_matrix["Category"].apply(lambda x: str(x).split(" - ")[0] if " - " in str(x) else str(x))

            prev_agg = df_prev_matrix.groupby("Category").agg(
                Prev_Sold=("qty", "sum"),
                Prev_Revenue=("item_revenue", "sum")
            ).reset_index()
            prev_agg["Prev_ASP"] = (prev_agg["Prev_Revenue"] / prev_agg["Prev_Sold"].replace(0, 1)).fillna(0)
            merged = curr_agg.merge(prev_agg, on="Category", how="outer").fillna(0)
        else:
            merged = curr_agg.copy()
            merged["Prev_Sold"] = 0
            merged["Prev_Revenue"] = 0
            merged["Prev_ASP"] = 0

        def format_trend(curr, prev):
            if prev == 0 and curr > 0:
                return "🚀 New"
            elif prev == 0 and curr == 0:
                return "➖"
            diff = curr - prev
            pct = (diff / prev) * 100
            if diff > 0:
                return f"▲ +{pct:.1f}%"
            elif diff < 0:
                return f"▼ {abs(pct):.1f}%"
            else:
                return "➖ 0%"

        merged["Sold Trend"] = merged.apply(lambda x: format_trend(x["Total_Sold"], x["Prev_Sold"]), axis=1)
        merged["Rev Trend"] = merged.apply(lambda x: format_trend(x["Total_Revenue"], x["Prev_Revenue"]), axis=1)
        merged["ASP Trend"] = merged.apply(lambda x: format_trend(x["ASP"], x["Prev_ASP"]), axis=1)
        
        merged["Return %"] = (merged["Returned_Qty"] / merged["Total_Sold"].replace(0, 1)) * 100
        merged["Exchange %"] = (merged["Exchanged_Qty"] / merged["Total_Sold"].replace(0, 1)) * 100
        
        merged["Master Category"] = merged["Category"].apply(lambda x: str(x).split(" - ")[0] if " - " in str(x) else str(x))
        if not show_master_only:
            merged["Sub Category"] = merged["Category"].apply(get_subcategory_name)
        
        merged = merged.sort_values(["Total_Revenue", "Master Category"], ascending=[False, True])
        
        cols_to_disp = ["Master Category"]
        if not show_master_only:
            cols_to_disp.append("Sub Category")
        cols_to_disp.extend(["Total_Sold", "Returned_Qty", "Return %", "Exchanged_Qty", "Exchange %", "Sold Trend", "Total_Revenue", "Rev Trend", "ASP", "ASP Trend", "Net_Yield"])

        display_df = merged[cols_to_disp].rename(columns={
            "Total_Sold": "Total Sold",
            "Returned_Qty": "Returns",
            "Exchanged_Qty": "Exchanges",
            "Total_Revenue": "Total Revenue",
            "Net_Yield": "Net Yield %"
        })
        
        col_cfg = {
            "Master Category": st.column_config.TextColumn("Master Category", width="small"),
            "Total Sold": st.column_config.NumberColumn("Total Sold", format="%d"),
            "Returns": st.column_config.NumberColumn("Returns", format="%d"),
            "Return %": st.column_config.NumberColumn("Return %", format="%.1f%%"),
            "Exchanges": st.column_config.NumberColumn("Exchanges", format="%d"),
            "Exchange %": st.column_config.NumberColumn("Exchange %", format="%.1f%%"),
            "Sold Trend": st.column_config.TextColumn(f"Sold vs Prev {clean_window}"),
            "Total Revenue": st.column_config.NumberColumn("Total Revenue", format="৳%d"),
            "Rev Trend": st.column_config.TextColumn(f"Rev vs Prev {clean_window}"),
            "ASP": st.column_config.NumberColumn("ASP", format="৳%d"),
            "ASP Trend": st.column_config.TextColumn(f"ASP vs Prev {clean_window}"),
            "Net Yield %": st.column_config.ProgressColumn("Net Yield %", format="%.1f%%", min_value=0, max_value=100),
        }
        
        if not show_master_only:
            col_cfg["Sub Category"] = st.column_config.TextColumn("Sub Category", width="small")
        
        def color_trend(val):
            if isinstance(val, str):
                if "▲" in val or "🚀" in val:
                    return "color: #10b981;"  # Emerald Green
                elif "▼" in val:
                    return "color: #ef4444;"  # Red
            return ""

        def color_high_return(val):
            if isinstance(val, (int, float)) and val > 10.0:
                return "color: #ef4444; font-weight: bold; background-color: rgba(239, 68, 68, 0.15);"
            return ""

        def color_high_exchange(val):
            if isinstance(val, (int, float)) and val > 5.0:
                return "color: #f97316; font-weight: bold; background-color: rgba(249, 115, 22, 0.15);"
            return ""

        styler = display_df.style
        if hasattr(styler, "map"):
            styled_df = styler.map(color_trend, subset=["Sold Trend", "Rev Trend", "ASP Trend"])
            styled_df = styled_df.map(color_high_return, subset=["Return %"])
            styled_df = styled_df.map(color_high_exchange, subset=["Exchange %"])
        else:
            styled_df = styler.applymap(color_trend, subset=["Sold Trend", "Rev Trend", "ASP Trend"])
            styled_df = styled_df.applymap(color_high_return, subset=["Return %"])
            styled_df = styled_df.applymap(color_high_exchange, subset=["Exchange %"])
        
        st.dataframe(styled_df, width="stretch", hide_index=True, column_config=col_cfg)
    else:
        st.info("Insufficient data for category matrix generation.")

    st.divider()
    rep_c1, rep_c2 = st.columns([3, 1])
    with rep_c1:
        st.markdown("**📊 Category Report Export**")
    with rep_c2:
        report_show_master = st.toggle("Show Master Category Only", value=False, key=KeyManager.get_key("deep_dive", "rep_master_toggle"))
    
    if not df_sales.empty and "order_date" in df_sales.columns:
        start_dt = pd.to_datetime(df_sales["order_date"]).min().date()
        end_dt = pd.to_datetime(df_sales["order_date"]).max().date()
    else:
        end_dt = date.today()
        start_dt = end_dt - timedelta(days=30)

    st.caption("Generates a unified report combining current inventory units, sales, and returns aggregated by category for the global period.")
    st.info(f"📅 **Global Reporting Period:** {start_dt.strftime('%B %d, %Y')} to {end_dt.strftime('%B %d, %Y')}")
    
    if st.button("Generate Category Report", use_container_width=True, key=KeyManager.get_key("deep_dive", "gen_global_cat_report")):
        with st.spinner("Compiling sub-category report..."):
            # 1. Total Units (Inventory)
            inventory = stock_df.copy() if stock_df is not None else pd.DataFrame()
            subcat_units = pd.DataFrame()
            if not inventory.empty:
                # Force system-defined categories instead of relying on raw WooCommerce tags
                names = inventory.get("Name", pd.Series(dtype=str)).fillna("").astype(str)
                skus = inventory.get("SKU", pd.Series(dtype=str)).fillna("").astype(str)
                from BackEnd.core.categories import get_category_for_sales
                inventory["Category"] = [get_category_for_sales(n + " " + s) for n, s in zip(names, skus)]
                if report_show_master:
                    inventory["Sub Category"] = inventory["Category"].apply(lambda x: str(x).split(" - ")[0] if " - " in str(x) else str(x))
                else:
                    inventory["Sub Category"] = inventory["Category"].apply(get_subcategory_name)
                
                inventory["Stock Quantity"] = pd.to_numeric(inventory.get("Stock Quantity", 0), errors="coerce").fillna(0)
                subcat_units = inventory.groupby("Sub Category")["Stock Quantity"].sum().reset_index()
                subcat_units.rename(columns={"Sub Category": "Sub-Category", "Stock Quantity": "Total_Units"}, inplace=True)
            
            # 2. Total Sold (Sales) using Global Window
            total_orders_in_period = 0
            sales_qty = pd.DataFrame()
            sales_source = df_sales
            
            if sales_source is not None and not sales_source.empty and "sku" in sales_source.columns and "qty" in sales_source.columns:
                sales_df_copy = sales_source.copy()
                
                if "order_id" in sales_df_copy.columns:
                    total_orders_in_period = sales_df_copy["order_id"].nunique()

                if not inventory.empty and "SKU" in inventory.columns:
                    sku_to_subcat = {str(k).upper().strip(): v for k, v in inventory.drop_duplicates("SKU").set_index("SKU")["Sub Category"].to_dict().items()}
                    sales_df_copy["Sub Category"] = sales_df_copy["sku"].astype(str).str.upper().str.strip().map(sku_to_subcat)
                else:
                    sales_df_copy["Sub Category"] = None
                
                missing_subcat = sales_df_copy["Sub Category"].isna()
                if missing_subcat.any():
                    names = sales_df_copy.loc[missing_subcat, "item_name"].fillna("").astype(str)
                    skus = sales_df_copy.loc[missing_subcat, "sku"].fillna("").astype(str)
                    from BackEnd.core.categories import get_category_for_sales
                    cats = [get_category_for_sales(n + " " + s) for n, s in zip(names, skus)]
                    if report_show_master:
                        sales_df_copy.loc[missing_subcat, "Sub Category"] = [str(c).split(" - ")[0] if " - " in str(c) else str(c) for c in cats]
                    else:
                        sales_df_copy.loc[missing_subcat, "Sub Category"] = [get_subcategory_name(c) for c in cats]
                    
                sales_qty = sales_df_copy.groupby("Sub Category")["qty"].sum().reset_index()
                sales_qty.rename(columns={"Sub Category": "Sub-Category", "qty": "Total_Sold"}, inplace=True)
                
            # 3. Total Returned
            returns_qty = pd.DataFrame()
            exchange_qty = pd.DataFrame()
            tot_exchanged = 0
            
            returns_data = st.session_state.get("returns_data", pd.DataFrame())
            if returns_data.empty:
                try:
                    from FrontEnd.pages.dashboard_lib.returns_tracker import _get_returns_data_with_daily_cache
                    from BackEnd.services.returns_tracker import get_current_sync_window
                    sync_window = get_current_sync_window()
                    returns_data = _get_returns_data_with_daily_cache(sync_window=sync_window, sales_df_full=df_sales)
                    st.session_state["returns_data"] = returns_data
                except Exception:
                    pass
                    
            filtered_returns = returns_data.copy()
            if not filtered_returns.empty and "date" in filtered_returns.columns:
                filtered_returns["date"] = pd.to_datetime(filtered_returns["date"], errors="coerce")
                mask = (filtered_returns["date"].dt.date >= start_dt) & (filtered_returns["date"].dt.date <= end_dt)
                filtered_returns = filtered_returns[mask]

            if not filtered_returns.empty and "returned_items" in filtered_returns.columns:
                ret_items = []
                exch_items = []
                for _, row in filtered_returns.iterrows():
                    issue_type = str(row.get("issue_type", ""))
                    
                    if issue_type == "Exchange":
                        items = row.get("returned_items", [])
                        if hasattr(items, "tolist"): items = items.tolist()
                        if isinstance(items, list):
                            for item in items:
                                if isinstance(item, dict):
                                    tot_exchanged += int(pd.to_numeric(item.get("qty", 1), errors="coerce") or 1)
                                    exch_items.append({
                                        "sku": item.get("sku", ""),
                                        "name": item.get("name", ""),
                                        "qty": int(pd.to_numeric(item.get("qty", 1), errors="coerce") or 1)
                                    })
                                    
                    if issue_type in ["Paid Return", "Non Paid Return", "Partial"]:
                        items = row.get("returned_items", [])
                        if hasattr(items, "tolist"): items = items.tolist()
                        if not isinstance(items, list): continue
                        for item in items:
                            if not isinstance(item, dict): continue
                            ret_items.append({
                                "sku": item.get("sku", ""),
                                "name": item.get("name", ""),
                                "qty": int(pd.to_numeric(item.get("qty", 1), errors="coerce") or 1)
                            })
                
                def map_subcats_to_items(items_list):
                    df_res = pd.DataFrame(items_list)
                    if not inventory.empty and "SKU" in inventory.columns:
                        sku_to_subcat = {str(k).upper().strip(): v for k, v in inventory.drop_duplicates("SKU").set_index("SKU")["Sub Category"].to_dict().items()}
                        df_res["Sub Category"] = df_res["sku"].astype(str).str.upper().str.strip().map(sku_to_subcat)
                    else:
                        df_res["Sub Category"] = None
                    
                    missing = df_res["Sub Category"].isna()
                    if missing.any():
                        names = df_res.loc[missing, "name"].fillna("").astype(str)
                        skus = df_res.loc[missing, "sku"].fillna("").astype(str)
                        from BackEnd.core.categories import get_category_for_sales
                        cats = [get_category_for_sales(n + " " + s) for n, s in zip(names, skus)]
                        if report_show_master:
                            df_res.loc[missing, "Sub Category"] = [str(c).split(" - ")[0] if " - " in str(c) else str(c) for c in cats]
                        else:
                            df_res.loc[missing, "Sub Category"] = [get_subcategory_name(c) for c in cats]
                    return df_res.groupby("Sub Category")["qty"].sum().reset_index()

                if ret_items:
                    returns_qty = map_subcats_to_items(ret_items)
                    returns_qty.rename(columns={"Sub Category": "Sub-Category", "qty": "Total_Returned"}, inplace=True)
                    
                if exch_items:
                    exchange_qty = map_subcats_to_items(exch_items)
                    exchange_qty.rename(columns={"Sub Category": "Sub-Category", "qty": "Total_Exchanged"}, inplace=True)

            # 4. Merge Data
            all_subcats = set(subcat_units["Sub-Category"]) if not subcat_units.empty else set()
            if not sales_qty.empty: all_subcats.update(sales_qty["Sub-Category"])
            if not returns_qty.empty: all_subcats.update(returns_qty["Sub-Category"])
            if not exchange_qty.empty: all_subcats.update(exchange_qty["Sub-Category"])
            
            report_df = pd.DataFrame({"Sub-Category": sorted(list(all_subcats))})
            if not subcat_units.empty: report_df = report_df.merge(subcat_units, on="Sub-Category", how="left")
            else: report_df["Total_Units"] = 0
            if not sales_qty.empty: report_df = report_df.merge(sales_qty, on="Sub-Category", how="left")
            else: report_df["Total_Sold"] = 0
            if not returns_qty.empty: report_df = report_df.merge(returns_qty, on="Sub-Category", how="left")
            else: report_df["Total_Returned"] = 0
            if not exchange_qty.empty: report_df = report_df.merge(exchange_qty, on="Sub-Category", how="left")
            else: report_df["Total_Exchanged"] = 0
            
            report_df.fillna(0, inplace=True)
            for col in ["Total_Units", "Total_Sold", "Total_Returned", "Total_Exchanged"]:
                if col in report_df.columns:
                    report_df[col] = report_df[col].astype(int)
                
            report_df["Total_Net_Sold"] = report_df["Total_Sold"] - report_df["Total_Returned"] - report_df["Total_Exchanged"]
            report_df["Return %"] = ((report_df["Total_Returned"] / report_df["Total_Sold"].replace(0, 1)) * 100).round(1)
            report_df["Exchange %"] = ((report_df["Total_Exchanged"] / report_df["Total_Sold"].replace(0, 1)) * 100).round(1)
            
            cols_order = ["Sub-Category", "Total_Units", "Total_Sold", "Total_Net_Sold", "Total_Returned", "Return %", "Total_Exchanged", "Exchange %"]
            report_df = report_df[[c for c in cols_order if c in report_df.columns]]
            
            if report_show_master:
                report_df = report_df.rename(columns={"Sub-Category": "Category"})
                cols_order[0] = "Category"

            tot_sold = int(report_df["Total_Sold"].sum())
            tot_returned = int(report_df["Total_Returned"].sum())
            net_sold = int(report_df["Total_Net_Sold"].sum())
            tot_exchanged_total = int(report_df["Total_Exchanged"].sum())
            ret_rate = (tot_returned / tot_sold * 100) if tot_sold > 0 else 0.0
            st.success(f"📊 **Period Summary:** **{total_orders_in_period:,}** Total Orders | **{tot_sold:,}** Gross Sold | **{net_sold:,}** Net Sold | **{tot_returned:,}** Items Returned | **{tot_exchanged_total:,}** Items Exchanged | **{ret_rate:.1f}%** Return Rate")

            st.dataframe(report_df, use_container_width=True, hide_index=True)
            
            summary_metrics = {
                "Total Orders": total_orders_in_period,
                "Gross Items Sold": tot_sold,
                "Net Items Sold": net_sold,
                "Total Items Returned": tot_returned,
                "Total Items Exchanged": tot_exchanged_total,
                "Return Rate (%)": f"{ret_rate:.1f}%",
                "Report Period": f"{start_dt.strftime('%B %d, %Y')} to {end_dt.strftime('%B %d, %Y')}",
                "Generated On": date.today().strftime('%Y-%m-%d')
            }
            
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                summary_df = pd.DataFrame(list(summary_metrics.items()), columns=["Metric", "Value"])
                summary_df.to_excel(writer, sheet_name="Executive Summary", index=False)
                report_df.to_excel(writer, sheet_name="Sub-Category Report", index=False)
                
                top_5_df = report_df.sort_values("Total_Sold", ascending=False).head(5)
                if not top_5_df.empty:
                    top_5_df.to_excel(writer, sheet_name="Chart Data", index=False)
                    
                    workbook = writer.book
                    ws_summary = writer.sheets["Executive Summary"]
                    ws_report = writer.sheets["Sub-Category Report"]
                    ws_data = writer.sheets["Chart Data"]
                    ws_data.hide()
                    
                    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#4F46E5', 'font_color': 'white'})
                    
                    for col_num, value in enumerate(report_df.columns.values):
                        ws_report.write(0, col_num, value, header_fmt)
                        ws_report.set_column(col_num, col_num, 16)
                    
                    for col_num, value in enumerate(summary_df.columns.values):
                        ws_summary.write(0, col_num, value, header_fmt)
                    ws_summary.set_column(0, 0, 25)
                    ws_summary.set_column(1, 1, 35)
                    
                    chart = workbook.add_chart({'type': 'column'})
                    chart.add_series({
                        'name':       'Total Sold',
                        'categories': ['Chart Data', 1, 0, len(top_5_df), 0],
                        'values':     ['Chart Data', 1, 2, len(top_5_df), 2],
                        'fill':       {'color': '#4F46E5'}
                    })
                    chart.set_title({'name': 'Top 5 Sub-Categories by Sales'})
                    chart.set_x_axis({'name': 'Sub-Category'})
                    chart.set_y_axis({'name': 'Items Sold'})
                    chart.set_style(11)
                    
                    ws_summary.insert_chart('D2', chart, {'x_scale': 1.2, 'y_scale': 1.2})
            
            excel_data = buffer.getvalue()
            
            st.download_button(
                label="📥 Download Category Report (Excel)",
                data=excel_data,
                file_name=f"Category_Report_{date.today().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=KeyManager.get_key("deep_dive", "dl_global_cat_report"),
                use_container_width=True
            )

    # FILTER CONTROL CENTER
    with st.expander("🛠️ Advanced Cluster Filters", expanded=True):
        st.markdown("**📦 Category & Operations**")
        f_c1, f_c2, f_c3, f_c4 = st.columns(4)
        
        with f_c1:
            # 1. Category - use master list for consistent hierarchy display
            cat_list = get_master_category_list()
            sel_cats = st.multiselect("Categories", ["All"] + cat_list, default=["All"], format_func=format_category_label)
            active_cats = [] if "All" in sel_cats or not sel_cats else sel_cats

        with f_c2:
            # Combined Product Name & SKU selection
            if active_cats:
                mask = pd.Series(False, index=df_sales.index)
                for cat in active_cats:
                    mask |= df_sales["Category"].str.startswith(cat, na=False)
                sku_options = df_sales[mask]
            else:
                sku_options = df_sales
            sku_options = sku_options.copy()
            sku_options["_display_name"] = sku_options["_clean_name"] + " [" + sku_options["sku"].astype(str) + "]"
            
            avail_items = sorted([str(s) for s in sku_options["_display_name"].unique() if str(s).strip() and "Unknown" not in str(s)])
            sel_items = st.multiselect("Products (Name + SKU)", ["All"] + avail_items, default=["All"])
            active_items = [] if "All" in sel_items or not sel_items else sel_items

        with f_c3:
            # 3. Size Filter
            if active_items:
                size_options = sku_options[sku_options["_display_name"].isin(active_items)]
            else:
                size_options = sku_options
                
            avail_sizes = sorted([str(s) for s in size_options["_size"].dropna().unique() if str(s).strip()])
            sel_sizes = st.multiselect("Variants (Size)", ["All"] + avail_sizes, default=["All"])
            active_sizes = [] if "All" in sel_sizes or not sel_sizes else sel_sizes

        with f_c4:
            # 4. Trend Filter
            avail_trends = sorted([str(t) for t in df_sales["Trend"].dropna().unique()])
            sel_trends = st.multiselect("Trend Velocity", ["All"] + avail_trends, default=["All"])
            active_trends = [] if "All" in sel_trends or not sel_trends else sel_trends



    # 1. APPLY COMPREHENSIVE FILTERING
    def _apply_cluster_filters(df):
        if df is None or df.empty: return pd.DataFrame()
        temp = df.copy()
        if active_cats:
            mask = pd.Series(False, index=temp.index)
            for cat in active_cats:
                mask |= temp["Category"].str.startswith(cat, na=False)
            temp = temp[mask]
        if active_items:
            temp["_display_name"] = temp["_clean_name"].astype(str) + " [" + temp["sku"].astype(str) + "]"
            temp = temp[temp["_display_name"].isin(active_items)]
        if active_sizes:
            temp = temp[temp["_size"].isin(active_sizes)]
        if active_trends and "Trend" in temp.columns:
            temp = temp[temp["Trend"].isin(active_trends)]
        return temp

    w_df = _apply_cluster_filters(df_sales)
    w_prev = _apply_cluster_filters(df_prev)

    if w_df.empty:
        st.warning("No sales data matches the active filter cluster. Adjust filters to refine your search.")
        return

    # --- Strategic Pulse Calculation ---
    total_items_sold = int(w_df["qty"].sum())
    total_revenue = w_df["item_revenue"].sum()
    avg_item_price = total_revenue / total_items_sold if total_items_sold > 0 else 0
    unique_customers = w_df["customer_key"].nunique()
    
    # Previous stats for delta
    prev_items = int(w_prev["qty"].sum()) if not w_prev.empty else 0
    prev_revenue = w_prev["item_revenue"].sum() if not w_prev.empty else 0
    prev_avg_price = (prev_revenue / prev_items) if prev_items > 0 else 0
    prev_customers = w_prev["customer_key"].nunique() if not w_prev.empty else 0

    def get_delta_data(curr, prev):
        if prev <= 0: return "", 0
        diff = curr - prev
        pct = (diff / prev) * 100
        return f"{abs(pct):.1f}%", diff

    d_items_label, d_items_val = get_delta_data(total_items_sold, prev_items)
    d_rev_label, d_rev_val = get_delta_data(total_revenue, prev_revenue)
    d_price_label, d_price_val = get_delta_data(avg_item_price, prev_avg_price)
    d_cust_label, d_cust_val = get_delta_data(unique_customers, prev_customers)

    # Top Variation logic
    variation_agg = w_df.groupby("_size").agg(Units=("qty", "sum")).reset_index().sort_values("Units", ascending=False)
    top_var_name = variation_agg.iloc[0]["_size"] if not variation_agg.empty else "N/A"
    top_var_units = int(variation_agg.iloc[0]["Units"]) if not variation_agg.empty else 0
    top_var_display = f"{top_var_name} ({top_var_units})"
    
    # VISUALIZATION SUITE
    st.markdown("**⚡ Strategic Pulse**")
    p_c1, p_c2, p_c3, p_c4, p_c5 = st.columns(5, gap="small")
    
    with p_c1: ui.icon_metric("Total Items Sold", f"{total_items_sold:,}", icon="📦", delta=d_items_label, delta_val=d_items_val)
    with p_c2: ui.icon_metric("Top Variation", top_var_display, icon="🎯")
    with p_c3: ui.icon_metric("Gross Revenue", f"৳{total_revenue:,.0f}", icon="💰", delta=d_rev_label, delta_val=d_rev_val)
    with p_c4: ui.icon_metric("Avg Item Price", f"৳{avg_item_price:,.0f}", icon="🏷️", delta=d_price_label, delta_val=d_price_val)
    with p_c5: ui.icon_metric("Unique Buyers", f"{unique_customers:,}", icon="👥", delta=d_cust_label, delta_val=d_cust_val)

    st.markdown(f"🚩 **Strategic Intelligence:** This segment is powered by **{unique_customers:,}** unique customers across **{total_items_sold:,}** total units sold. The dominant variation is **{top_var_name}** accounting for **{top_var_units}** units.")

    # --- Cluster Time Series Analysis ---
    st.divider()
    st.markdown("**📈 Cluster Performance Over Time**")
    
    # Pre-process for Time Series
    ts_df = w_df.copy()
    ts_df['Date'] = pd.to_datetime(ts_df['order_date']).dt.strftime('%Y-%m-%d')
    daily_ts = ts_df.groupby('Date').agg(
        Revenue=("item_revenue", "sum"),
        Units=("qty", "sum")
    ).reset_index().sort_values("Date")
    
    # Dual-axis or simple toggle? Let's go with a beautifully styled revenue line with markers
    fig_ts = px.area(daily_ts, x="Date", y="Revenue", 
                     title="Daily Revenue Trend (Current Cluster)",
                     labels={"Revenue": "Revenue (৳)", "Date": "Timeline"},
                     template="plotly_white")
    
    fig_ts.update_traces(
        line_color="#6366f1", # Indigo
        fillcolor="rgba(99, 102, 241, 0.15)",
        marker=dict(size=6, color="#4338ca"),
        mode='lines+markers'
    )
    
    fig_ts.update_layout(
        hovermode="x unified",
        xaxis=dict(showgrid=False, rangeslider=dict(visible=True, thickness=0.06)),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_ts, width="stretch", key=KeyManager.get_key("deep_dive", "daily_rev_trend"))

    # --- Strategic Visuals & Breakdown ---
    st.divider()
    
    # Pre-calculate bulk propensity for export and visuals
    order_basket = w_df.groupby("order_id")["qty"].sum().reset_index()
    total_orders_in_cluster = len(order_basket)
    p_single, p_bulk, p_other = "N/A", "N/A", "N/A"
    single_piece, bulk_pieces, mid_piece = 0, 0, 0
    if total_orders_in_cluster > 0:
        single_piece = len(order_basket[order_basket["qty"] == 1])
        bulk_pieces = len(order_basket[order_basket["qty"] >= 3])
        mid_piece = total_orders_in_cluster - single_piece - bulk_pieces
        p_single = (single_piece / total_orders_in_cluster) * 100
        p_bulk = (bulk_pieces / total_orders_in_cluster) * 100
        p_other = (mid_piece / total_orders_in_cluster) * 100

    rd1, rd2 = st.columns([3, 1])
    with rd1:
        st.markdown(f"**📊 Strategic Analytics Export**")
        st.caption(f"Generate a professional multi-sheet intelligence report for the **{len(w_df):,}** items in this selection.")
    with rd2:
        from datetime import datetime
        
        cluster_return_loss = w_df["Return_Loss"].sum() if "Return_Loss" in w_df.columns else 0
        if "Exchanged_Qty" in w_df.columns:
            w_df["Exchange_Loss"] = w_df["Exchanged_Qty"] * (w_df["item_revenue"] / w_df["qty"].replace(0, 1))
        cluster_exchange_loss = w_df["Exchange_Loss"].sum() if "Exchange_Loss" in w_df.columns else 0
        cluster_net_rev = total_revenue - cluster_return_loss
        
        # 1. Prepare Strategic Summary Sheet
        summary_data = {
            "Metric": [
                "Gross Revenue", 
                "Return Loss",
                "Exchange Loss",
                "Net Revenue",
                "Total Orders", 
                "Total Units", 
                "Unique Buyers", 
                "Avg Item Price", 
                "Single Piece Propensity (1)", 
                "Mid-Tier Propensity (2)", 
                "Bulk Propensity (3+)",
                "Top Variation"
            ],
            "Value": [
                f"৳{total_revenue:,.0f}", 
                f"৳{cluster_return_loss:,.0f}",
                f"৳{cluster_exchange_loss:,.0f}",
                f"৳{cluster_net_rev:,.0f}",
                total_orders_in_cluster,
                total_items_sold, 
                unique_customers, 
                f"৳{avg_item_price:,.0f}",
                f"{p_single:.1f}%" if isinstance(p_single, (int, float)) else p_single,
                f"{p_other:.1f}%" if isinstance(p_other, (int, float)) else p_other,
                f"{p_bulk:.1f}%" if isinstance(p_bulk, (int, float)) else p_bulk,
                top_var_display
            ],
            "Trend vs Prev": [
                d_rev_label,
                "-",
                "-",
                "-",
                "-",
                d_items_label,
                d_cust_label,
                d_price_label,
                "-",
                "-",
                "-",
                "-"
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        
        # 2. Prepare Data Sheet
        export_df = w_df.drop(columns=[col for col in w_df.columns if col.startswith("_")], errors="ignore")
        
        # 3. Compile AI Strategic Intelligence
        ai_narrative = [
            f"STRATEGIC OVERVIEW: This filtered cluster generated ৳{total_revenue:,.0f} across {unique_customers:,} unique buyers.",
            f"BASKET DYNAMICS: Bulk buying (3+ units) accounts for {p_bulk:.1f}% of transactions." if isinstance(p_bulk, (int, float)) else "",
            f"BASKET DYNAMICS: Single-item purchases make up {p_single:.1f}% of transactions." if isinstance(p_single, (int, float)) else "",
            f"DOMINANT VARIATION: {top_var_name} is driving the cluster with {top_var_units} units sold."
        ]
        ai_df = pd.DataFrame({"AI Strategic Intelligence": [n for n in ai_narrative if n]})
        
        # 4. Prepare SKU Performance Sheet
        sku_perf_df = pd.DataFrame()
        if "sku" in w_df.columns and "item_name" in w_df.columns:
            agg_cols = {"Units_Sold": ("qty", "sum"), "Gross_Revenue": ("item_revenue", "sum")}
            if "Return_Loss" in w_df.columns:
                agg_cols["Return_Loss"] = ("Return_Loss", "sum")
            if "Exchange_Loss" in w_df.columns:
                agg_cols["Exchange_Loss"] = ("Exchange_Loss", "sum")
                
            sku_perf_df = w_df.groupby(["sku", "item_name"]).agg(**agg_cols).reset_index()
            
            if "Return_Loss" not in sku_perf_df.columns:
                sku_perf_df["Return_Loss"] = 0.0
            if "Exchange_Loss" not in sku_perf_df.columns:
                sku_perf_df["Exchange_Loss"] = 0.0
                
            sku_perf_df["Net_Revenue"] = sku_perf_df["Gross_Revenue"] - sku_perf_df["Return_Loss"]
            sku_perf_df = sku_perf_df.sort_values("Gross_Revenue", ascending=False)
            
            for col in ["Gross_Revenue", "Return_Loss", "Exchange_Loss", "Net_Revenue"]:
                sku_perf_df[col] = sku_perf_df[col].apply(lambda x: f"৳{x:,.2f}")

        additional_sheets = {"Summary": summary_df, "AI Insights": ai_df}
        if not sku_perf_df.empty:
            additional_sheets["SKU Performance"] = sku_perf_df

        report_bytes = ui.export_to_excel(export_df, "Cluster Data", additional_sheets=additional_sheets)
        
        st.download_button(
            label="📊 Export Strategic Analysis",
            data=report_bytes,
            file_name=f"deen_strategic_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=KeyManager.get_key("deep_dive", "export_strategic")
        )

    cluster_t1, cluster_t2, cluster_t3, cluster_t4 = st.tabs(["📈 Performance Mix", "🔍 Variant Analysis", "🛒 Basket Context", "📋 Cluster Data Ledger"])
    
    with cluster_t1:
        # Leaderboard Strategy Controls
        lc1, lc2 = st.columns([2, 1])
        with lc1:
            leader_mode = st.radio("Spotlight Strategy", ["💰 Top 10", "💰 Top 20", "📉 Underperformers", "⚙️ Custom Window"],
                                  index=0, horizontal=True, key=KeyManager.get_key("deep_dive", "leader_mode_sel"))
        with lc2:
            granularity = st.radio("Granularity", ["📦 Master Product", "🆔 Variant"], index=0, horizontal=True, key=KeyManager.get_key("deep_dive", "granularity_sel"))
            
        limit = 10
        if leader_mode == "💰 Top 20": limit = 20
        elif leader_mode == "📉 Underperformers": limit = 15
        elif leader_mode == "⚙️ Custom Window":
            limit = st.number_input("Display Limit", 5, 100, 20)
        
        # Prepare Data based on selected granularity
        group_col = "_master_label" if granularity == "📦 Master Product" else "_variant_label"
        w_df["_master_label"] = w_df["_densed_name"] + " [" + w_df["sku"].astype(str) + "]"
        w_df["_variant_label"] = w_df["_densed_name"] + " with Size " + w_df["_size"].astype(str) + " [" + w_df["sku"].astype(str) + "]"
        
        leader_df = w_df.groupby([group_col, "Category"]).agg(
            Units=("qty", "sum"),
            Revenue=("item_revenue", "sum")
        ).reset_index()
        
        if leader_mode == "📉 Underperformers":
            leader_df = leader_df.sort_values("Revenue", ascending=True).head(limit)
            sort_order = 'total descending'
        else:
            leader_df = leader_df.sort_values("Revenue", ascending=False).head(limit)
            sort_order = 'total ascending'

        # Calculate Share % safely
        total_cluster_rev = leader_df["Revenue"].sum()
        leader_df["Revenue Share %"] = (leader_df["Revenue"] / total_cluster_rev * 100).round(1) if total_cluster_rev > 0 else 0
            
        # Strip parent for sub-category hover
        leader_df["Sub-Category"] = leader_df["Category"].apply(get_subcategory_name)
        
        hover_label = "Product Name" if granularity == "📦 Master Product" else "Product (SKU)"
        
        fig = px.bar(leader_df, x="Revenue", y=group_col, 
                     title=f"Products Spotlight ({leader_mode} - {granularity})",
                     orientation='h', color="Units", color_continuous_scale="Viridis",
                     hover_data=["Units", "Revenue", "Sub-Category", "Revenue Share %"],
                     labels={group_col: hover_label, "Revenue": "Gross Revenue (৳)", "Units": "Qty Sold"})
        
        fig.update_layout(yaxis={'categoryorder': sort_order}, height=max(400, limit*25))
        st.plotly_chart(fig, width="stretch", key=KeyManager.get_key("deep_dive", "products_spotlight"))
        
        if st.button("✨ Generate AI Product Summary", use_container_width=True, key=KeyManager.get_key("deep_dive", "ai_prod_summary")):
            with st.spinner("AI is analyzing the top products..."):
                try:
                    from BackEnd.services.nlp_engine import LLMAgent
                    import os
                    agent_type = "Standard"
                    if "OPENROUTER_API_KEY" in st.secrets or os.environ.get("OPENROUTER_API_KEY"):
                        agent_type = "OpenRouter"
                    elif "HUGGINGFACE_API_KEY" in st.secrets or os.environ.get("HUGGINGFACE_API_KEY"):
                        agent_type = "HuggingFace"
                    elif "GROQ_API_KEY" in st.secrets or os.environ.get("GROQ_API_KEY"):
                        agent_type = "Groq"
                    elif "GEMINI_API_KEY" in st.secrets or os.environ.get("GEMINI_API_KEY"):
                        agent_type = "Google Gemini"
                    agent = LLMAgent(agent_type=agent_type)
                    
                    summary_df = leader_df.head(10).copy()
                    prompt = f"Act as an AI Agent. Analyze the following top-selling products data:\n\n{summary_df.to_string()}\n\nProvide a concise 3-bullet insight on what is driving the revenue, pointing out any specific categories or products that stand out. Keep it under 100 words. Format cleanly using markdown."
                    
                    ai_response = agent.query(prompt, {})
                    st.session_state[KeyManager.get_key("deep_dive", "ai_summary_result")] = ai_response
                except Exception as e:
                    st.error(f"Could not generate summary: {e}")
                    
        if KeyManager.get_key("deep_dive", "ai_summary_result") in st.session_state:
            st.markdown(
                f"""
                <div style="background: rgba(99, 102, 241, 0.1); padding: 15px; border-radius: 8px; border-left: 4px solid var(--primary); margin-top: 10px; margin-bottom: 20px;">
                    <div style="color: var(--primary); font-weight: 800; font-size: 0.75rem; letter-spacing: 1px; margin-bottom: 8px;">🤖 AI AGENT TOP 10 SUMMARY</div>
                    <div style="font-size: 0.9rem;">{st.session_state[KeyManager.get_key("deep_dive", "ai_summary_result")]}</div>
                </div>
                """, unsafe_allow_html=True
            )

        c1, c2 = st.columns(2)
        with c1:
            # Trend Revenue Pie - Descending Contribution
            t_rev = w_df.groupby("Trend")["item_revenue"].sum().reset_index().sort_values("item_revenue", ascending=False)
            fig = px.pie(t_rev, values="item_revenue", names="Trend", title="Revenue Contribution by Moving Type",
                         hole=0.4, color_discrete_sequence=px.colors.qualitative.Prism)
            st.plotly_chart(fig, width="stretch", key=KeyManager.get_key("deep_dive", "rev_contrib_pie"))
            
        with c2:
            # Source/Platform Bar - Descending
            s_rev = w_df.groupby("source")["item_revenue"].sum().reset_index().sort_values("item_revenue", ascending=False)
            fig = px.bar(s_rev, x="source", y="item_revenue", title="Revenue by Platform Source",
                         color="item_revenue", color_continuous_scale="Tealgrn")
            fig.update_layout(xaxis={'categoryorder': 'total descending'})
            st.plotly_chart(fig, width="stretch", key=KeyManager.get_key("deep_dive", "rev_by_source_bar"))

        # Operational Category Mix (Sub-Category Focus)
        st.divider()
        st.markdown("**📦 Operational Sub-Category Performance**")
        occ1, occ2 = st.columns(2)
        
        cat_intell = w_df.copy()
        cat_intell["Sub-Cat"] = cat_intell["Category"].apply(get_subcategory_name)
        
        agg_dict = {
            "Revenue": ("item_revenue", "sum"),
            "Units": ("qty", "sum")
        }
        if "Returned_Qty" in cat_intell.columns:
            agg_dict["Returns"] = ("Returned_Qty", "sum")
        if "Exchanged_Qty" in cat_intell.columns:
            agg_dict["Exchanges"] = ("Exchanged_Qty", "sum")
            
        cat_agg = cat_intell.groupby("Sub-Cat").agg(**agg_dict).reset_index().sort_values("Revenue", ascending=False)
        
        with occ1:
            fig_cat_pie = px.pie(cat_agg, values="Revenue", names="Sub-Cat", title="Revenue Mix by Sub-Segment",
                                hole=0.4, color_discrete_sequence=px.colors.qualitative.T10)
            st.plotly_chart(fig_cat_pie, width="stretch", key=KeyManager.get_key("deep_dive", "rev_mix_subcat_pie"))
            
        with occ2:
            plot_cols = ["Units"]
            color_seq = ["#3b82f6"]
            if "Returns" in cat_agg.columns:
                plot_cols.append("Returns")
                color_seq.append("#ef4444")
            if "Exchanges" in cat_agg.columns:
                plot_cols.append("Exchanges")
                color_seq.append("#8b5cf6")
                
            fig_cat_bar = px.bar(cat_agg.sort_values("Units", ascending=True), x=plot_cols, y="Sub-Cat", 
                                 title="Unit Volume, Returns & Exchanges per Sub-Segment",
                                 orientation='h', color_discrete_sequence=color_seq)
            st.plotly_chart(fig_cat_bar, width="stretch", key=KeyManager.get_key("deep_dive", "unit_vol_subcat_bar"))

    with cluster_t2:
        v_c1, v_c2 = st.columns(2)
        with v_c1:
            # Size Distribution
            sz_df = w_df.groupby("_size")["qty"].sum().reset_index()
            fig = px.bar(sz_df, x="_size", y="qty", title="Unit Volume by Size Cluster", 
                         color="qty", color_continuous_scale="Portland")
            st.plotly_chart(fig, width="stretch", key=KeyManager.get_key("deep_dive", "unit_vol_size_bar"))
        with v_c2:
            # Color Distribution
            clr_df = w_df.groupby("_color")["item_revenue"].sum().reset_index()
            fig = px.pie(clr_df, values="item_revenue", names="_color", title="Revenue by Color Palette",
                         color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig, width="stretch", key=KeyManager.get_key("deep_dive", "rev_by_color_pie"))

    with cluster_t3:
        # --- ML Analytics: Bulk Purchase Dynamics ---
        st.markdown("**🧠 Bulk Purchase Dynamics (ML Analysis)**")
        st.caption("Analyzing the propensity for bulk purchasing within this cluster. (Single Piece vs 3+ Units)")
        
        if total_orders_in_cluster > 0:
            # Optimized Columns for readability
            bm1, bm2, bm3 = st.columns(3)
            with bm1: ui.metric_highlight("SINGLE PIECE PROPENSITY", f"{p_single:.1f}%", f"Orders: {single_piece}", icon="🛍️")
            with bm2: ui.metric_highlight("BULK PROPENSITY (3+)", f"{p_bulk:.1f}%", f"Orders: {bulk_pieces}", icon="📦")
            with bm3: ui.metric_highlight("MID-TIER (2 ITEMS)", f"{p_other:.1f}%", f"Balance", icon="✨")
            
            # Distribution Pie
            prop_df = pd.DataFrame({
                "Propensity": ["Single Piece (1)", "Bulk (3+)", "Mid-Tier (2)"],
                "Count": [single_piece, bulk_pieces, mid_piece]
            })
            fig_prop = px.pie(prop_df, values="Count", names="Propensity", hole=0.5, 
                             color_discrete_map={"Single Piece (1)": "#6366f1", "Bulk (3+)": "#10b981", "Mid-Tier (2)": "#f59e0b"},
                             title=f"Basket Size Propensity: {sel_cats[0] if sel_cats and 'All' not in sel_cats else 'Filtered Cluster'}")
            fig_prop.update_layout(height=350, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_prop, width="stretch", key=KeyManager.get_key("deep_dive", "basket_size_prop_pie"))
        
        st.divider()
        b_c1, b_c2 = st.columns(2)
        with b_c1:
            # Quantity Distribution (Basket logic)
            q_dist = w_df.groupby("qty")["order_id"].nunique().reset_index().rename(columns={"qty": "Items in Line", "order_id": "Orders"})
            fig = px.bar(q_dist, x="Items in Line", y="Orders", title="Distribution of Units per Line Item",
                         text_auto=True, color_discrete_sequence=["#F59E0B"])
            st.plotly_chart(fig, width="stretch", key=KeyManager.get_key("deep_dive", "dist_units_per_line_bar"))
        with b_c2:
            # City/Region Mix within this cluster
            city_mix = w_df.groupby("_region_display")["item_revenue"].sum().reset_index().sort_values("item_revenue", ascending=False).head(10)
            fig = px.bar(city_mix, x="item_revenue", y="_region_display", title="Market Hotspots (Regional Density)", 
                         orientation='h', color="item_revenue", color_continuous_scale="Agsunset",
                         labels={"_region_display": "Region/District", "item_revenue": "Revenue (৳)"})
            st.plotly_chart(fig, width="stretch", key=KeyManager.get_key("deep_dive", "market_hotspots_bar"))

    with cluster_t4:
        # Categorization Health Diagnostic
        others_df = w_df[w_df["Category"] == "Others"].copy()
        others_count = len(others_df)
        total_count = len(w_df)
        others_pct = (others_count / total_count * 100) if total_count > 0 else 0
        
        st.markdown("**🛠️ Categorization Health Audit**")
        ac1, ac2 = st.columns([1.2, 2])
        with ac1:
            ui.metric_highlight(
                "Uncategorized Rate", 
                f"{others_pct:.1f}%", 
                f"{others_count} items", 
                delta_type="down" if others_pct > 0 else "up",
                icon="🛡️"
            )
        with ac2:
            if others_count > 0:
                st.warning("Found items in 'Others'. Review the list below to identify missing keyword rules.")
                top_others = others_df.groupby("item_name").agg(
                    Units=("qty", "sum"),
                    Revenue=("item_revenue", "sum")
                ).reset_index().sort_values("Revenue", ascending=False)
                st.write("**All Uncategorized Items (Others):**")
                st.dataframe(
                    top_others, 
                    width="stretch", 
                    hide_index=True,
                    column_config={"Revenue": st.column_config.NumberColumn("Revenue", format="৳%d")}
                )
            else:
                st.success("✅ Perfection: 100% of items in this cluster are successfully categorized!")

        st.divider()
        # Show clean ledger
        ledger_df = w_df[["order_id", "order_date", "item_name", "sku", "qty", "item_revenue", "Trend", "Coupons", "source", "_region_display"]].copy()
        ledger_df = ledger_df.rename(columns={"_region_display": "Location", "item_revenue": "Revenue", "qty": "Units", "item_name": "Product"})
        st.dataframe(ledger_df, width="stretch", hide_index=True)
        
    st.divider()
    st.markdown("**🤖 Deep Dive Contextual AI Agent**")
    st.caption("Ask specific questions about this active cluster of data.")
    from FrontEnd.components.data_display import render_ai_pilot_chat_ui
    returns_data = st.session_state.get("returns_data", pd.DataFrame())
    render_ai_pilot_chat_ui(w_df, returns_df=returns_data, stock_df=stock_df, key_prefix="deep_dive_cluster")

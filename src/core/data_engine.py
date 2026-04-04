import pandas as pd
import streamlit as st
import duckdb
import os
from pathlib import Path
from src.core.paths import DATA_DIR

# Placeholder for the Live Google Sheet CSV URL
# Using the default published CSV export from src/core/sync.py logic if available
LIVE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTBDukmkRJGgHjCRIAAwGmlWaiPwESXSp9UBXm3_sbs37bk2HxavPc62aobmL1cGWUfAKE4Zd6yJySO/pub?output=csv&gid=0"

@st.cache_data(ttl=300)
def load_and_merge_data(force_refresh=False):
    """
    Unions historical Parquet data with live Google Sheet data using DuckDB.
    """
    # 1. Load Live Data
    try:
        # We skip cache if force_refresh is True (though st.cache_data handles part of this)
        df_live = pd.read_csv(LIVE_SHEET_URL)
        df_live['source'] = 'live'
    except Exception as e:
        st.warning(f"Could not fetch live Google Sheet: {e}. Loading local fallback.")
        fallback_path = DATA_DIR / "year=2026" / "data.parquet"
        if fallback_path.exists():
            df_live = pd.read_parquet(fallback_path)
            df_live['source'] = 'fallback_2026'
        else:
            # Create an empty dataframe with expected columns if even fallback is missing
            st.error("Fallback data missing. Creating empty schema.")
            df_live = pd.DataFrame(columns=['Order Date', 'Customer ID', 'Email', 'Phone', 'Revenue', 'Product Name', 'Quantity'])
    
    # 2. Load Historical Data
    historical_dfs = []
    # Look for partitioned years (e.g., 2023, 2024, 2025)
    for year_path in DATA_DIR.glob("year=*"):
        if "2026" in year_path.name: # Already handled by live/fallback
            continue
        parquet_file = year_path / "data.parquet"
        if parquet_file.exists():
            df_h = pd.read_parquet(parquet_file)
            df_h['source'] = f"historical_{year_path.name.split('=')[-1]}"
            historical_dfs.append(df_h)
            
    # 3. DuckDB Union
    con = duckdb.connect(database=':memory:')
    
    # Load into DuckDB
    con.register('live_data', df_live)
    
    if historical_dfs:
        df_hist_all = pd.concat(historical_dfs, ignore_index=True)
        con.register('hist_data', df_hist_all)
        # Use DuckDB to union and ensure schema alignment
        df_all = con.execute("""
            SELECT * FROM live_data
            UNION ALL
            SELECT * FROM hist_data
        """).df()
    else:
        df_all = df_live
        
    # Ensure Order Date is datetime
    if 'Order Date' in df_all.columns:
        df_all['Order Date'] = pd.to_datetime(df_all['Order Date'], errors='coerce')
        
    return df_all

@st.cache_data(ttl=600)
def get_customer_insights(df_all):
    """
    Calculates RFM metrics and segments customers using DuckDB.
    """
    if df_all.empty:
        return pd.DataFrame()
        
    con = duckdb.connect(database=':memory:')
    con.register('orders', df_all)
    
    # Calculate Base Metrics (RFM)
    # Prefer Email over Phone for ID if Customer ID is missing
    df_customers = con.execute("""
        SELECT 
            COALESCE("Customer ID", Email, Phone, 'Unknown') as Customer_ID,
            ANY_VALUE(Email) as Email,
            ANY_VALUE(Phone) as Phone,
            MAX("Order Date") as Last_Purchase,
            COUNT(*) as Total_Orders,
            SUM(Revenue) as Total_Spent,
            SUM(Revenue) / COUNT(*) as AOV,
            CAST(CURRENT_DATE - MAX("Order Date") AS INTEGER) as Recency
        FROM orders
        GROUP BY 1
    """).df()
    
    # Logic for Segmentation
    def segment_logic(row):
        if row['Recency'] > 180:
            return 'Churned'
        if row['Total_Orders'] == 1:
            return 'New'
        if row['Total_Spent'] > 5000 and row['Recency'] < 30: # Custom VIP threshold
            return 'VIP'
        if row['Total_Spent'] > 1000 and row['Recency'] > 60:
            return 'At Risk'
        return 'Active'
        
    df_customers['Segment'] = df_customers.apply(segment_logic, axis=1)
    
    return df_customers

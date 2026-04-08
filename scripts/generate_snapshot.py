import os
import sys
from pathlib import Path
import pandas as pd
import pickle
import json
from datetime import datetime

# Add root to sys.path
root = Path(__file__).parent.parent
sys.path.append(str(root))

from BackEnd.services.hybrid_data_loader import load_hybrid_data, load_cached_woocommerce_stock_data, load_woocommerce_customer_count
from BackEnd.services.customer_insights import generate_customer_insights_from_sales
from BackEnd.services.ml_insights import build_ml_insight_bundle
from BackEnd.core.categories import get_category_for_sales

SNAPSHOT_DIR = root / "data" / "static_snapshot"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

def generate_snapshot():
    print("Starting Static Snapshot Generation...")
    
    # Disable Snapshot Mode temporarily to fetch real data
    os.environ["USE_STATIC_SNAPSHOT_FORCE_OFF"] = "True"
    
    print("Loading Sales Data...")
    from datetime import timedelta
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    df_sales = load_hybrid_data(start_date=start_date, woocommerce_mode="cache_only")
    
    if df_sales.empty:
        print("Error: No sales data found in cache. Run a sync first.")
        return

    # 2. Apply Categories (Baking it in)
    print("Applying Product Categories...")
    df_sales["Category"] = df_sales["item_name"].apply(get_category_for_sales)
    
    # 3. Filter for Executive View (Completed/Shipped)
    valid_statuses = ["completed", "shipped"]
    df_sales_exec = df_sales[df_sales["order_status"].str.lower().isin(valid_statuses)].copy()
    
    # 4. Generate Customer Insights
    print("Generating Customer Insights...")
    df_customers = generate_customer_insights_from_sales(df_sales_exec, include_rfm=True)
    
    # 5. Generate ML Insights
    print("Training ML Ensemble Models (this may take a moment)...")
    ml_bundle = build_ml_insight_bundle(df_sales_exec, df_customers, horizon_days=7)
    ml_bundle["customers"] = df_customers # Include customers in bundle for easier loading
    
    # 6. Load Stock Data
    print("Loading Stock Data...")
    df_stock = load_cached_woocommerce_stock_data()
    
    # 7. Get Customer Count
    customer_count = load_woocommerce_customer_count()
    
    # SAVE EVERYTHING
    print(f"Saving Snapshot to {SNAPSHOT_DIR}...")
    
    df_sales.to_parquet(SNAPSHOT_DIR / "sales.parquet", index=False)
    df_stock.to_parquet(SNAPSHOT_DIR / "stock.parquet", index=False)
    
    with open(SNAPSHOT_DIR / "ml_bundle.pkl", "wb") as f:
        pickle.dump(ml_bundle, f)
        
    metadata = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sales_rows": len(df_sales),
        "customer_count": customer_count,
        "label": "April 2026 Snapshot"
    }
    with open(SNAPSHOT_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print("Snapshot Generation Complete!")

if __name__ == "__main__":
    generate_snapshot()

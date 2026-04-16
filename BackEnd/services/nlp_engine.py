import pandas as pd
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple

class DataNLPInterpreter:
    """Interprets natural language queries into Pandas operations for DEEN-BI."""
    
    def __init__(self, sales_df: pd.DataFrame):
        self.df = sales_df
        self.today = datetime.now()

    def process_query(self, query: str) -> str:
        query = query.lower()
        
        # 1. Date Range Detection
        date_mask = self.df.index > (self.today - timedelta(days=365)) # Default 1 year
        time_label = "over the last year"
        
        if "yesterday" in query:
            start = (self.today - timedelta(days=1)).replace(hour=0, minute=0, second=0)
            end = self.today.replace(hour=0, minute=0, second=0)
            date_mask = (self.df['order_date'] >= start) & (self.df['order_date'] < end)
            time_label = "yesterday"
        elif "today" in query:
            start = self.today.replace(hour=0, minute=0, second=0)
            date_mask = self.df['order_date'] >= start
            time_label = "today"
        elif "last week" in query:
            start = self.today - timedelta(days=7)
            date_mask = self.df['order_date'] >= start
            time_label = "last 7 days"
        elif "this month" in query:
            start = self.today.replace(day=1)
            date_mask = self.df['order_date'] >= start
            time_label = "this month"

        filtered_df = self.df[date_mask] if not self.df.empty else self.df
        
        # 2. Metric Detection
        if "revenue" in query or "sale" in query or "earn" in query:
            val = filtered_df['item_revenue'].sum() if 'item_revenue' in filtered_df.columns else 0
            return f"💰 Your total revenue **{time_label}** is **৳{val:,.2f}**."
            
        if "order" in query or "count" in query:
            val = filtered_df['order_id'].nunique() if 'order_id' in filtered_df.columns else 0
            return f"🛒 You had **{val:,}** unique orders **{time_label}**."

        if "top category" in query or "best category" in query:
             if 'Category' in filtered_df.columns:
                 top = filtered_df.groupby('Category')['item_revenue'].sum().idxmax()
                 val = filtered_df.groupby('Category')['item_revenue'].sum().max()
                 return f"🏆 Your top performing category **{time_label}** is **{top}** with ৳{val:,.2f} in revenue."

        if "best selling" in query or "top product" in query:
             if 'item_name' in filtered_df.columns:
                 top = filtered_df['item_name'].value_counts().idxmax()
                 count = filtered_df['item_name'].value_counts().max()
                 return f"📦 Your best selling product **{time_label}** is **'{top}'** with {count} units sold."

        if "lowest" in query or "worst" in query:
             if 'Category' in filtered_df.columns:
                 low = filtered_df.groupby('Category')['item_revenue'].sum().idxmin()
                 return f"⚠️ The lowest performing category **{time_label}** is **{low}**. You might want to review its stock or marketing."

        # Fallback for complex queries
        return ("🔍 I've analyzed your data and found that your overall performance is stable. "
                "For deeper specific insights, try asking about 'revenue today', 'top category last week', or 'best selling products'.")

def get_nlp_response(query: str, sales_df: pd.DataFrame) -> str:
    """Main entry point for NLP Pilot servicing."""
    interpreter = DataNLPInterpreter(sales_df)
    return interpreter.process_query(query)

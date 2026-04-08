import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json

@st.cache_resource
def load_bangladesh_geojson():
    """Fetch and cache the Bangladesh 64-district GeoJSON."""
    url = "https://raw.githubusercontent.com/ahnaf-tahmid-chowdhury/Choropleth-Bangladesh/master/bangladesh_geojson_adm2_64_districts_zillas.json"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Failed to load map data: {str(e)}")
    return None

def normalize_district_name(name):
    """Normalize district names for matching with GeoJSON properties."""
    if not name or pd.isna(name):
        return "Unknown"
    
    name = str(name).strip().title()
    # Map common variations
    mapping = {
        "Chattogram": "Chittagong", # Highcharts/Mapbox often use legacy names
        "Barishal": "Barisal",
        "Bogura": "Bogra",
        "Jashore": "Jessore",
        "Cumilla": "Comilla",
        "Cox'S Bazar": "Cox's Bazar",
        "Chuadanga": "Chuadanga",
        # Add more if discrepancies found
    }
    return mapping.get(name, name)

def render_district_map(df_sales: pd.DataFrame):
    """Render a choropleth map of Bangladesh showing sales density."""
    st.markdown("### 🗺️ Market Hotspots: Regional Density")
    
    geojson = load_bangladesh_geojson()
    if not geojson:
        st.warning("Map data is currently unavailable. Please check your connection.")
        return

    # 1. Aggregate Data by District
    df_map = df_sales.copy()
    
    def get_district(row):
        # Prefer 'state' then 'city' (standard WooCommerce fields mapping)
        state = str(row.get("state", "")).strip().title()
        city = str(row.get("city", "")).strip().title()
        
        # Guard against "Unknown" or empty strings
        if state and state not in ["Unknown", "None", "", "Nan"]: return state
        if city and city not in ["Unknown", "None", "", "Nan"]: return city
        return "Unknown"

    df_map["matched_district"] = df_map.apply(get_district, axis=1)
    df_map["matched_district"] = df_map["matched_district"].apply(normalize_district_name)
    
    # --- Ensure all 64 Districts are present for a "Full Map" look ---
    all_districts = [f['properties']['ADM2_EN'] for f in geojson['features']]
    base_df = pd.DataFrame({"District": all_districts, "Value": 0.0})
    
    map_metric = st.segmented_control(
        "Map focus",
        options=["Revenue", "Orders"],
        default="Revenue",
        key="geo_map_metric_toggle",
        label_visibility="collapsed"
    )

    if map_metric == "Revenue":
        agg_raw = df_map.groupby("matched_district")["order_total"].sum().reset_index()
        agg_raw.columns = ["District", "Value"]
        color_scale = "Tealgrn"
        labels = {"Value": "Revenue (৳)"}
    else:
        agg_raw = df_map.groupby("matched_district")["order_id"].nunique().reset_index()
        agg_raw.columns = ["District", "Value"]
        color_scale = "Purp"
        labels = {"Value": "Orders"}

    # Merge real data onto the base 64-district set
    agg_df = base_df.merge(agg_raw, on="District", how="left", suffixes=('_base', ''))
    agg_df["Value"] = agg_df["Value"].fillna(0) + agg_df["Value_base"]
    agg_df = agg_df.drop(columns=["Value_base"])

    # 2. Rendering
    fig = px.choropleth(
        agg_df,
        geojson=geojson,
        locations="District",
        featureidkey="properties.ADM2_EN",
        color="Value",
        color_continuous_scale=color_scale,
        range_color=(0, agg_df["Value"].max() if agg_df["Value"].max() > 0 else 100),
        labels=labels,
        template="plotly_dark"
    )

    fig.update_geos(
        projection_type="mercator",
        visible=False,
        bgcolor="rgba(0,0,0,0)"
    )
    
    fig.update_layout(
        height=600, # Increased height for "Full Map" feel
        margin={"r":0,"t":40,"l":0,"b":0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(
            thicknessmode="pixels", thickness=15,
            lenmode="fraction", len=0.6,
            yanchor="middle", y=0.5,
            title=None
        )
    )

    st.plotly_chart(fig, use_container_width=True)
    
    # 📝 Summary Insight
    if not agg_df.empty:
        top_district = agg_df.sort_values("Value", ascending=False).iloc[0]
        st.caption(f"📍 **Dominant Region:** {top_district['District']} is currently leading in {map_metric.lower()} density.")

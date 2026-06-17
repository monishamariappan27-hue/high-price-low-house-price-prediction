"""
House Price Clustering Dashboard
---------------------------------
Interactive Streamlit dashboard visualizing K-Means clustering results
that group houses into "Low Price" and "High Price" segments.

Run with:
    streamlit run app.py

Expects "house_price_clusters_output.csv" in the same folder
(the labeled output produced by the clustering notebook).
If the file isn't found, you can upload it from the sidebar instead.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="House Price Clustering Dashboard",
    page_icon="🏠",
    layout="wide",
)

COLOR_MAP = {"Low": "#4C78A8", "High": "#E45756"}

# ----------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------
@st.cache_data
def load_data(file):
    return pd.read_csv(file)


st.sidebar.title("🏠 Controls")

data_file = "house_price_clusters_output.csv"
uploaded = st.sidebar.file_uploader("Or upload a clustered CSV", type="csv")

try:
    df = load_data(uploaded if uploaded is not None else data_file)
except FileNotFoundError:
    st.error(
        f"Couldn't find `{data_file}` in this folder. "
        "Upload the clustered CSV using the sidebar to continue."
    )
    st.stop()

required_cols = {"price", "price_tier_simple", "price_tier_multifeature"}
if not required_cols.issubset(df.columns):
    st.error(
        "This file is missing the expected clustering columns "
        f"({', '.join(required_cols)}). Please upload the correct output CSV."
    )
    st.stop()

# ----------------------------------------------------------------------
# Sidebar filters
# ----------------------------------------------------------------------
tier_choice = st.sidebar.radio(
    "Clustering method",
    options=["price_tier_multifeature", "price_tier_simple"],
    format_func=lambda x: "Multi-feature (price + size + rooms)"
    if x == "price_tier_multifeature"
    else "Price only",
)

if "city" in df.columns:
    all_cities = sorted(df["city"].dropna().unique().tolist())
    selected_cities = st.sidebar.multiselect("Filter by city", options=all_cities, default=[])
    if selected_cities:
        df = df[df["city"].isin(selected_cities)]

price_min, price_max = int(df["price"].min()), int(df["price"].max())
price_range = st.sidebar.slider(
    "Price range ($)",
    min_value=price_min,
    max_value=price_max,
    value=(price_min, price_max),
    step=10_000,
)
df = df[(df["price"] >= price_range[0]) & (df["price"] <= price_range[1])]

tier_col = tier_choice
df = df[df[tier_col].isin(["Low", "High"])]

if df.empty:
    st.warning("No data matches the current filters. Try widening your selection.")
    st.stop()

# ----------------------------------------------------------------------
# Header + KPIs
# ----------------------------------------------------------------------
st.title("🏠 House Price Clustering Dashboard")
st.caption(
    "K-Means clustering groups houses into **Low Price** and **High Price** "
    "segments automatically, based on the data — no manual thresholds."
)

low_df = df[df[tier_col] == "Low"]
high_df = df[df[tier_col] == "High"]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total Houses", f"{len(df):,}")
c2.metric("Low Price Count", f"{len(low_df):,}")
c3.metric("High Price Count", f"{len(high_df):,}")
c4.metric("Avg Low Price", f"${low_df['price'].mean():,.0f}" if len(low_df) else "—")
c5.metric("Avg High Price", f"${high_df['price'].mean():,.0f}" if len(high_df) else "—")

st.divider()

# ----------------------------------------------------------------------
# Row 1: Price distribution + tier proportion
# ----------------------------------------------------------------------
col1, col2 = st.columns([2, 1])

with col1:
    fig_hist = px.histogram(
        df,
        x="price",
        color=tier_col,
        nbins=60,
        color_discrete_map=COLOR_MAP,
        title="Price Distribution by Cluster",
        labels={"price": "Price ($)", tier_col: "Price Tier"},
    )
    fig_hist.update_layout(bargap=0.05)
    st.plotly_chart(fig_hist, use_container_width=True)

with col2:
    tier_counts = df[tier_col].value_counts().reindex(["Low", "High"]).fillna(0)
    fig_pie = go.Figure(
        data=[
            go.Pie(
                labels=tier_counts.index,
                values=tier_counts.values,
                hole=0.55,
                marker=dict(colors=[COLOR_MAP[t] for t in tier_counts.index]),
            )
        ]
    )
    fig_pie.update_layout(title="Tier Proportion")
    st.plotly_chart(fig_pie, use_container_width=True)

# ----------------------------------------------------------------------
# Row 2: Boxplot + scatter
# ----------------------------------------------------------------------
col3, col4 = st.columns(2)

with col3:
    fig_box = px.box(
        df,
        x=tier_col,
        y="price",
        color=tier_col,
        color_discrete_map=COLOR_MAP,
        category_orders={tier_col: ["Low", "High"]},
        title="Price Range by Cluster",
        labels={"price": "Price ($)", tier_col: "Price Tier"},
    )
    st.plotly_chart(fig_box, use_container_width=True)

with col4:
    if "sqft_living" in df.columns:
        fig_scatter = px.scatter(
            df,
            x="sqft_living",
            y="price",
            color=tier_col,
            color_discrete_map=COLOR_MAP,
            opacity=0.5,
            title="Price vs Living Area, by Cluster",
            labels={"sqft_living": "Living Area (sqft)", "price": "Price ($)", tier_col: "Price Tier"},
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

# ----------------------------------------------------------------------
# Row 3: Property profile comparison
# ----------------------------------------------------------------------
profile_cols = [c for c in ["sqft_living", "bedrooms", "bathrooms"] if c in df.columns]
if profile_cols:
    st.subheader("Property Profile by Cluster")
    profile = df.groupby(tier_col)[profile_cols].mean().reindex(["Low", "High"])

    pcols = st.columns(len(profile_cols))
    for i, feature in enumerate(profile_cols):
        fig_bar = go.Figure(
            data=[
                go.Bar(
                    x=profile.index,
                    y=profile[feature],
                    marker_color=[COLOR_MAP[t] for t in profile.index],
                )
            ]
        )
        fig_bar.update_layout(
            title=f"Avg {feature.replace('_', ' ').title()}",
            height=300,
            margin=dict(t=40, b=20),
        )
        pcols[i].plotly_chart(fig_bar, use_container_width=True)

# ----------------------------------------------------------------------
# Row 4: Top cities by tier composition
# ----------------------------------------------------------------------
if "city" in df.columns:
    st.subheader("Top Cities — High vs Low Price Counts")
    top_cities = df["city"].value_counts().head(10).index
    city_tier = (
        df[df["city"].isin(top_cities)]
        .groupby(["city", tier_col])
        .size()
        .reset_index(name="count")
    )
    fig_city = px.bar(
        city_tier,
        x="city",
        y="count",
        color=tier_col,
        color_discrete_map=COLOR_MAP,
        barmode="stack",
        title="House Counts by Price Tier (Top 10 Cities)",
        labels={"count": "Number of Houses", "city": "City", tier_col: "Price Tier"},
    )
    fig_city.update_xaxes(categoryorder="total descending")
    st.plotly_chart(fig_city, use_container_width=True)

# ----------------------------------------------------------------------
# Data table + download
# ----------------------------------------------------------------------
st.divider()
st.subheader("Filtered Data")
st.dataframe(df, use_container_width=True, height=300)

st.download_button(
    "Download filtered data as CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="filtered_house_price_clusters.csv",
    mime="text/csv",
)
"""
CrossMarket — Japanese Product Market Analysis Dashboard
Interactive Streamlit Application
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Add src to Python path
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from data_processing import run_pipeline
from analysis import (
    get_executive_kpis,
    get_price_summary_by_dimension,
    get_cross_market_parity,
    get_brand_positioning_summary,
    get_coverage_breakdown,
    identify_price_segments_and_hypotheses
)

# Page Configuration
st.set_page_config(
    page_title="CrossMarket | Japanese Product Analysis",
    page_icon="🇯🇵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Executive Theme CSS
st.markdown("""
<style>
    /* Metric Cards */
    [data-testid="stMetricValue"] {
        font-size: 1.85rem !important;
        font-weight: 700 !important;
        color: #0F172A !important;
    }
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-bottom: 12px;
        min-height: 110px;
    }
    .kpi-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
    }
    .kpi-val {
        font-size: 1.7rem;
        font-weight: 700;
        color: #1E293B;
    }
    .kpi-sub {
        font-size: 0.75rem;
        color: #64748B;
        margin-top: 4px;
    }
    /* Section Headings */
    .section-header {
        font-size: 1.3rem;
        font-weight: 700;
        color: #0F172A;
        background: #F8FAFC;
        border-bottom: 2px solid #E2E8F0;
        padding: 8px 12px;
        border-radius: 6px;
        margin-top: 24px;
        margin-bottom: 16px;
    }
    /* Hypothesis Cards */
    .hypo-box {
        background: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-left: 5px solid #2563EB;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 16px;
        color: #334155;
    }
    .hypo-box p {
        color: #334155;
        line-height: 1.5;
    }
    .hypo-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 8px;
    }
    .hypo-tag {
        background: #DBEAFE;
        color: #1E40AF;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 8px;
    }
    .badge-caveat {
        background: #FEF3C7;
        color: #92400E;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    /* Methodology Callout */
    .method-callout {
        background: #EFF6FF;
        border-left: 4px solid #3B82F6;
        padding: 14px 18px;
        border-radius: 6px;
        margin-bottom: 20px;
        font-size: 0.9rem;
        color: #1E3A8A;
    }
    .report-banner {
        background: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-left: 4px solid #64748B;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 18px;
        font-size: 0.85rem;
        color: #334155;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_and_cache_data():
    """Runs data cleaning pipeline and caches results for responsive UI."""
    return run_pipeline()


def main():
    df_clean, data_quality_summary = load_and_cache_data()

    # ==========================================
    # SIDEBAR: INTERACTIVE FILTERS
    # ==========================================
    st.sidebar.title("🗾 CrossMarket")
    st.sidebar.markdown("**Japanese Product Market Analysis**")
    st.sidebar.caption("Retail Intelligence: United States vs. United Kingdom")
    st.sidebar.markdown("---")

    st.sidebar.subheader("Filter Controls")

    # 1. Target Market Filter
    market_options = ["All Markets", "US", "UK"]
    selected_market = st.sidebar.selectbox("Target Market:", market_options)

    # 2. Brand Filter
    available_brands = sorted(df_clean["brand"].unique().tolist())
    selected_brands = st.sidebar.multiselect(
        "Select Brand(s):",
        options=available_brands,
        default=available_brands
    )

    # 3. Category Filter
    available_categories = sorted(df_clean["product_category"].unique().tolist())
    selected_categories = st.sidebar.multiselect(
        "Select Category:",
        options=available_categories,
        default=available_categories
    )

    # 4. Tax Normalization Mode
    st.sidebar.markdown("---")
    st.sidebar.subheader("Tax Normalization Basis")
    vat_mode = st.sidebar.radio(
        "UK Price Display:",
        options=["Nominal (Includes 20% UK VAT)", "Pre-Tax (VAT Removed)"],
        help="UK retail prices legally include 20% VAT; US prices exclude sales tax at checkout. Choose Pre-Tax for like-for-like pre-tax comparison."
    )
    use_ex_vat = (vat_mode == "Pre-Tax (VAT Removed)")
    active_price_col = "price_usd_ex_vat" if use_ex_vat else "price_usd"

    # 5. Price Range Slider (Bounded strictly by active price basis)
    min_p = float(df_clean[active_price_col].min())
    max_p = float(df_clean[active_price_col].max())
    price_range = st.sidebar.slider(
        f"Price Range ({'Pre-Tax USD' if use_ex_vat else 'Nominal USD'}):",
        min_value=min_p,
        max_value=max_p,
        value=(min_p, max_p),
        step=1.0,
        format="$%.2f"
    )

    # 6. Cross-Market Matching Mode Filter
    st.sidebar.markdown("---")
    st.sidebar.subheader("Cross-Market Matching Scope")
    match_scope = st.sidebar.selectbox(
        "Pair Matching Criterion:",
        options=["All Validated Matches (38 pairs)", "Exact SKU & Pack Only (36 pairs)"],
        help="All Validated Matches includes 36 exact SKU/pack pairs plus 2 closely matched regional/size variants (Pilot Metropolitan vs MR Retro Pop, Midori Cotton F0 vs A5)."
    )
    match_mode = "exact_only" if "Exact" in match_scope else "all"

    # Apply Filters to dataset
    filtered_df = df_clean.copy()
    if selected_market != "All Markets":
        filtered_df = filtered_df[filtered_df["target_market"] == selected_market]
    if selected_brands:
        filtered_df = filtered_df[filtered_df["brand"].isin(selected_brands)]
    if selected_categories:
        filtered_df = filtered_df[filtered_df["product_category"].isin(selected_categories)]

    filtered_df = filtered_df[
        (filtered_df[active_price_col] >= price_range[0]) &
        (filtered_df[active_price_col] <= price_range[1])
    ]

    # Sidebar Data Provenance Badge
    st.sidebar.markdown("---")
    validation_color = "#059669" if data_quality_summary["validation_passed"] else "#DC2626"
    validation_label = "PASSED" if data_quality_summary["validation_passed"] else "FAILED"
    st.sidebar.markdown(
        f"""
        <div style="font-size:0.8rem; color:#475569;">
            <b>Active Listings:</b> {len(filtered_df)} / {len(df_clean)} records<br>
            <b>Exchange Rate:</b> 1 GBP = {data_quality_summary['gbp_usd_exchange_rate']} USD<br>
            <b>Series:</b> Bank of England XUDLGBD (4pm Close)<br>
            <b>Date:</b> September 30, 2026<br>
            <b>Rule Validation:</b> <span style="color:{validation_color}; font-weight:600;">{validation_label}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ==========================================
    # MAIN CONTENT: HEADER
    # ==========================================
    st.title("🗾 CrossMarket: Japanese Product Market Analysis Dashboard")
    st.markdown(
        "**Retail pricing dynamics, cross-market parity, brand positioning, and channel opportunities "
        "for Japanese stationery brands in the United States and United Kingdom.**"
    )

    # Methodological Callout
    st.markdown("""
    <div class="method-callout">
        <b>📌 Methodological & Governance Standards:</b> Built on <b>76 manually verified product-market observations</b> 
        from authorized retailers (JetPens, Cult Pens, Amazon US/UK, London Graphic Centre, Yoseka). 
        All foreign exchange conversions use documented central bank benchmark rates. 
        Market opportunities are explicitly formulated as <b>testable business hypotheses</b> rather than definitive proof of market demand.
    </div>
    """, unsafe_allow_html=True)

    # Empty State Guard
    if filtered_df.empty:
        st.warning("⚠️ No products match the current filter selection. Please broaden your filter criteria in the sidebar.")
        return

    # Compute Active Parity and KPIs
    active_parity = get_cross_market_parity(filtered_df, match_mode=match_mode)
    active_kpis = get_executive_kpis(filtered_df, active_parity)

    # ==========================================
    # SECTION 1: EXECUTIVE KPI CARDS
    # ==========================================
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="kpi-title">Active Records</div>
            <div class="kpi-val">{active_kpis['total_observations']}</div>
            <div class="kpi-sub">{active_kpis['unique_products']} distinct product names</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="kpi-title">Brands Active</div>
            <div class="kpi-val">{active_kpis['unique_brands']}</div>
            <div class="kpi-sub">Across {active_kpis['unique_categories']} categories</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="kpi-title">US Median Price</div>
            <div class="kpi-val">${active_kpis['us_median_usd']:.2f}</div>
            <div class="kpi-sub">Pre-tax USD (Mean: ${active_kpis['us_mean_usd']:.2f})</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        uk_med = active_kpis['uk_median_usd_ex_vat'] if use_ex_vat else active_kpis['uk_median_usd']
        uk_mean = active_kpis['uk_mean_usd_ex_vat'] if use_ex_vat else active_kpis['uk_mean_usd']
        sub_text = f"Pre-tax ex-VAT (Mean: ${uk_mean:.2f})" if use_ex_vat else f"Nominal inc-VAT (Mean: ${uk_mean:.2f})"
        st.markdown(f"""
        <div class="metric-card">
            <div class="kpi-title">UK Median Price</div>
            <div class="kpi-val">${uk_med:.2f}</div>
            <div class="kpi-sub">{sub_text}</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        if not active_parity.empty:
            mean_prem = active_parity["vat_adj_premium_pct"].mean() if use_ex_vat else active_parity["nominal_premium_pct"].mean()
            med_prem = active_parity["vat_adj_premium_pct"].median() if use_ex_vat else active_parity["nominal_premium_pct"].median()
            mean_sign = "+" if mean_prem > 0 else ""
            med_sign = "+" if med_prem > 0 else ""
            prem_display = f"{mean_sign}{mean_prem:.1f}%"
            sub_display = f"Median: {med_sign}{med_prem:.1f}% ({len(active_parity)} pairs)"
            prem_color = "#DC2626" if mean_prem > 0 else "#1E293B"
        else:
            prem_display = "N/A"
            sub_display = "0 matched pairs"
            prem_color = "#64748B"

        basis_lbl = "Pre-Tax" if use_ex_vat else "Nominal"
        st.markdown(f"""
        <div class="metric-card">
            <div class="kpi-title">UK Premium ({basis_lbl})</div>
            <div class="kpi-val" style="color: {prem_color};">{prem_display}</div>
            <div class="kpi-sub">{sub_display}</div>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
        <div class="metric-card">
            <div class="kpi-title">Avg Product Rating</div>
            <div class="kpi-val">★ {active_kpis['average_rating']:.2f}</div>
            <div class="kpi-sub">Mean of {active_kpis['rated_products_count']} rated listings ({active_kpis['total_reviews']:,} reviews)</div>
        </div>
        """, unsafe_allow_html=True)

    # ==========================================
    # NAVIGATION TABS
    # ==========================================
    tabs = st.tabs([
        "📊 Market & Pricing Parity",
        "🏷️ Brand & Category Positioning",
        "💡 Opportunities & Hypotheses",
        "🔍 Product Explorer & URLs",
        "📋 Findings Report",
        "🛡️ Data Quality & Methodology"
    ])

    # ----------------------------------------------------
    # TAB 1: MARKET & PRICING PARITY
    # ----------------------------------------------------
    with tabs[0]:
        st.markdown('<div class="section-header">1. Market Price Distributions & Parity Analysis</div>', unsafe_allow_html=True)

        chart_c1, chart_c2 = st.columns([1, 1])

        with chart_c1:
            st.subheader("Price Distribution by Market and Category")
            fig_box = px.box(
                filtered_df,
                x="product_category",
                y=active_price_col,
                color="target_market",
                points="all",
                hover_data=["product_name", "brand", "retailer", "local_price", "currency", "pack_quantity", "unit_price_usd"],
                color_discrete_map={"US": "#2563EB", "UK": "#DC2626"},
                labels={
                    active_price_col: "Price in USD (" + ("Pre-Tax" if use_ex_vat else "Standardized Nominal") + ")",
                    "product_category": "Product Category",
                    "target_market": "Market"
                },
                title="Price Ranges Across Categories (US vs UK)"
            )
            fig_box.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=50, b=20)
            )
            st.plotly_chart(fig_box, use_container_width=True)

        with chart_c2:
            st.subheader("Category Median Price Comparison")
            cat_summary = filtered_df.groupby(["product_category", "target_market"])[active_price_col].median().reset_index()
            fig_bar = px.bar(
                cat_summary,
                x="product_category",
                y=active_price_col,
                color="target_market",
                barmode="group",
                color_discrete_map={"US": "#2563EB", "UK": "#DC2626"},
                labels={
                    active_price_col: "Median Price (USD)",
                    "product_category": "Category",
                    "target_market": "Market"
                },
                text_auto=".2f",
                title="Median Price by Category (US vs UK)"
            )
            fig_bar.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=50, b=20)
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # Cross-Market Matched SKU Parity Section
        st.markdown('<div class="section-header">Matched Cross-Market Parity Comparison</div>', unsafe_allow_html=True)
        if not active_parity.empty:
            prem_col = "vat_adj_premium_pct" if use_ex_vat else "nominal_premium_pct"
            diff_label = "VAT-Adjusted Premium (%)" if use_ex_vat else "Nominal Premium (%)"

            st.caption(
                f"Displaying **{len(active_parity)} verified cross-market matched pairs** "
                f"({match_scope}). Green/Red bars indicate percentage premium of UK retail price over US retail price."
            )

            fig_parity = px.bar(
                active_parity,
                x="product_name",
                y=prem_col,
                color="category",
                hover_data=[
                    "cross_market_match_id", "match_quality", "brand",
                    "us_price_usd", "uk_price_usd", "uk_price_usd_ex_vat",
                    "us_retailer", "uk_retailer", "match_notes"
                ],
                labels={prem_col: diff_label, "product_name": "Matched Product"},
                title=f"Percentage Price Premium in UK vs US by Product ({diff_label})"
            )
            fig_parity.add_hline(y=0, line_dash="dash", line_color="black", annotation_text="Price Parity (0%)")
            fig_parity.update_layout(
                xaxis_tickangle=-45,
                margin=dict(l=20, r=20, t=50, b=140),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_parity, use_container_width=True)

            with st.expander("🔍 View Complete Matched Pairs Parity Table & Audit Notes"):
                disp_parity = active_parity[[
                    "cross_market_match_id", "match_quality", "product_name", "brand", "category", "pack_quantity",
                    "us_price_usd", "uk_price_gbp", "uk_price_usd", "uk_price_usd_ex_vat",
                    "nominal_premium_pct", "vat_adj_premium_pct",
                    "us_retailer", "uk_retailer", "match_notes"
                ]].rename(columns={
                    "cross_market_match_id": "Match ID",
                    "match_quality": "Match Quality",
                    "product_name": "Product Name",
                    "brand": "Brand",
                    "category": "Category",
                    "pack_quantity": "Pack Qty",
                    "us_price_usd": "US Price ($)",
                    "uk_price_gbp": "UK Price (£)",
                    "uk_price_usd": "UK Price ($ Nom.)",
                    "uk_price_usd_ex_vat": "UK Price ($ Pre-Tax)",
                    "nominal_premium_pct": "Nominal Premium (%)",
                    "vat_adj_premium_pct": "VAT-Adj. Premium (%)",
                    "us_retailer": "US Retailer",
                    "uk_retailer": "UK Retailer",
                    "match_notes": "Comparability Audit Notes"
                })
                st.dataframe(disp_parity, use_container_width=True)
        else:
            st.info("No cross-market matched product pairs found in the current filter selection.")

    # ----------------------------------------------------
    # TAB 2: BRAND & CATEGORY POSITIONING
    # ----------------------------------------------------
    with tabs[1]:
        st.markdown('<div class="section-header">2. Brand Positioning & Coverage Matrix</div>', unsafe_allow_html=True)

        brand_pos = get_brand_positioning_summary(filtered_df)

        b_c1, b_c2 = st.columns([1, 1])

        with b_c1:
            st.subheader("Brand Positioning: Median Price vs Average Rating")
            fig_scatter = px.scatter(
                brand_pos,
                x="median_price_usd",
                y="average_rating",
                size="total_reviews",
                color="brand_origin",
                text="brand",
                hover_data=["primary_category", "product_count", "positioning_tier", "rated_products", "total_reviews"],
                labels={
                    "median_price_usd": "Brand Median Price (USD)",
                    "average_rating": "Average Rating (out of 5.0)",
                    "brand_origin": "Origin Group",
                    "total_reviews": "Total Reviews Logged"
                },
                color_discrete_map={
                    "Japanese Heritage": "#DC2626",
                    "Western Competitor Benchmark": "#2563EB"
                },
                title="Brand Matrix (Bubble Size = Review Volume)"
            )
            fig_scatter.update_traces(textposition="top center")
            fig_scatter.update_layout(
                yaxis_range=[4.4, 5.0],
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=50, b=20)
            )
            st.plotly_chart(fig_scatter, use_container_width=True)

        with b_c2:
            st.subheader("Brand Median Price Ranking")
            fig_brand_bar = px.bar(
                brand_pos.sort_values(by="median_price_usd", ascending=True),
                x="median_price_usd",
                y="brand",
                orientation="h",
                color="brand_origin",
                color_discrete_map={
                    "Japanese Heritage": "#DC2626",
                    "Western Competitor Benchmark": "#2563EB"
                },
                text_auto=".2f",
                labels={"median_price_usd": "Median Price (USD)", "brand": "Brand"},
                title="Median Product Price by Brand"
            )
            fig_brand_bar.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=50, b=20)
            )
            st.plotly_chart(fig_brand_bar, use_container_width=True)

        # Brand Portfolio Summary Table
        st.subheader("Brand Portfolio Summary Table")
        st.caption("Ratings represent listing-level public review averages; review totals are summed across active listings.")
        st.dataframe(
            brand_pos[[
                "brand", "brand_origin", "positioning_tier", "primary_category",
                "product_count", "us_count", "uk_count",
                "median_price_usd", "average_rating", "total_reviews"
            ]].rename(columns={
                "brand": "Brand",
                "brand_origin": "Origin",
                "positioning_tier": "Positioning Tier",
                "primary_category": "Primary Category",
                "product_count": "Total SKUs",
                "us_count": "US SKUs",
                "uk_count": "UK SKUs",
                "median_price_usd": "Median Price ($)",
                "average_rating": "Avg Rating",
                "total_reviews": "Total Reviews Logged"
            }),
            use_container_width=True
        )

        # Retailer and Brand Summary Table
        coverage = get_coverage_breakdown(filtered_df)
        st.subheader("Retailer & Category Coverage Breakdown")
        ret_c1, ret_c2 = st.columns([1, 1])
        with ret_c1:
            st.markdown("**Category Representation by Market**")
            st.dataframe(coverage["category_market"], use_container_width=True)
        with ret_c2:
            st.markdown("**Retailer Product Counts & Ratings**")
            st.dataframe(coverage["retailer_summary"], use_container_width=True)

    # ----------------------------------------------------
    # TAB 3: STRATEGIC HYPOTHESES & OPPORTUNITIES
    # ----------------------------------------------------
    with tabs[2]:
        st.markdown('<div class="section-header">3. Strategic Hypotheses & Market Opportunities</div>', unsafe_allow_html=True)

        st.markdown("""
        > **⚠️ Analytical Protocol & Ethics Disclosure:**  
        > The strategic opportunities below are derived from empirical price comparisons, customer reviews, 
        > and retailer presence across the verified sample. In strict accordance with professional research standards, 
        > **these are explicitly presented as testable hypotheses for brand management to investigate, NOT definitive proof of market demand.**
        """)

        hypo_results = identify_price_segments_and_hypotheses(filtered_df, active_parity)

        for h in hypo_results["hypotheses"]:
            st.markdown(f"""
            <div class="hypo-box">
                <span class="hypo-tag">{h['id']}</span>
                <div class="hypo-title">{h['title']}</div>
                <p><b>Empirical Observation:</b> {h['observation']}</p>
                <p><b>Strategic Hypothesis:</b> {h['hypothesis']}</p>
                <p><b>Data Evidence:</b> <i>{h['evidence']}</i></p>
                <p><b>Recommended Testable Action:</b> 🎯 {h['testable_action']}</p>
                <div style="margin-top:10px;">
                    <span class="badge-caveat">⚠️ Methodological Boundary: {h['limitation_note']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ----------------------------------------------------
    # TAB 4: PRODUCT EXPLORER & URLS
    # ----------------------------------------------------
    with tabs[3]:
        st.markdown('<div class="section-header">4. Verified Product Explorer with Provenance Data</div>', unsafe_allow_html=True)
        st.markdown(
            "Inspect every verified listing in the dataset. All source URLs link directly to public retail listings. "
            "Verification status, seller type, and pack quantities are recorded per row."
        )

        search_query = st.text_input("Search by product name, brand, features, or materials:", "")
        explorer_df = filtered_df.copy()
        if search_query:
            query = search_query.lower()
            explorer_df = explorer_df[
                explorer_df["product_name"].str.lower().str.contains(query) |
                explorer_df["brand"].str.lower().str.contains(query) |
                explorer_df["product_features"].str.lower().str.contains(query) |
                explorer_df["material"].str.lower().str.contains(query)
            ]

        display_cols = [
            "product_id", "cross_market_match_id", "match_quality", "product_name", "brand",
            "product_category", "target_market", "retailer", "seller_type", "pack_quantity",
            "local_price", "currency", "price_usd", "price_usd_ex_vat", "unit_price_usd",
            "product_rating", "review_count", "verification_status", "collection_date", "product_url"
        ]

        st.dataframe(
            explorer_df[display_cols].rename(columns={
                "product_id": "ID",
                "cross_market_match_id": "Match ID",
                "match_quality": "Match Quality",
                "product_name": "Product Name",
                "brand": "Brand",
                "product_category": "Category",
                "target_market": "Market",
                "retailer": "Retailer",
                "seller_type": "Seller Type",
                "pack_quantity": "Pack",
                "local_price": "Local Price",
                "currency": "Curr",
                "price_usd": "Price (USD)",
                "price_usd_ex_vat": "Price USD (ex-VAT)",
                "unit_price_usd": "Unit Price ($)",
                "product_rating": "Rating",
                "review_count": "Reviews",
                "verification_status": "Verification",
                "collection_date": "Date",
                "product_url": "Source Listing URL"
            }),
            column_config={
                "Source Listing URL": st.column_config.LinkColumn(
                    "Source Listing URL",
                    display_text="Open Listing ↗"
                ),
                "Price (USD)": st.column_config.NumberColumn(format="$%.2f"),
                "Price USD (ex-VAT)": st.column_config.NumberColumn(format="$%.2f"),
                "Unit Price ($)": st.column_config.NumberColumn(format="$%.2f"),
                "Rating": st.column_config.NumberColumn(format="★ %.1f"),
                "Reviews": st.column_config.NumberColumn(format="%d"),
            },
            use_container_width=True,
            height=450
        )

        csv_data = explorer_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Products CSV (with Provenance)",
            data=csv_data,
            file_name="crossmarket_products_filtered.csv",
            mime="text/csv"
        )

    # ----------------------------------------------------
    # TAB 5: FINDINGS REPORT
    # ----------------------------------------------------
    with tabs[4]:
        st.markdown('<div class="section-header">5. Business Findings & Strategic Report</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="report-banner">
            <b>ℹ️ Baseline Study Document:</b> The report below documents the comprehensive baseline findings 
            from the full 76-observation study across US and UK retail channels. For dynamic, filter-specific calculations, 
            refer to the interactive <b>Market & Pricing Parity</b> and <b>Brand Positioning</b> tabs.
        </div>
        """, unsafe_allow_html=True)

        report_path = Path(__file__).resolve().parent / "reports" / "findings.md"
        if report_path.exists():
            with open(report_path, "r", encoding="utf-8") as f:
                report_content = f.read()
            st.markdown(report_content)
        else:
            st.error("Report file not found at `reports/findings.md`.")

    # ----------------------------------------------------
    # TAB 6: DATA QUALITY & METHODOLOGY
    # ----------------------------------------------------
    with tabs[5]:
        st.markdown('<div class="section-header">6. Data Quality, Verification Audit & Limitations</div>', unsafe_allow_html=True)

        audit_c1, audit_c2 = st.columns([1, 1])

        with audit_c1:
            st.subheader("Data Quality & Rule Validation Audit")
            status_color = "#059669" if data_quality_summary["validation_passed"] else "#DC2626"
            status_text = "PASSED (Zero Schema or Rule Violations)" if data_quality_summary["validation_passed"] else "FAILED"
            
            st.markdown(f"""
            - **Total Verified Observations:** {data_quality_summary['clean_row_count']}
            - **Distinct Product Models:** {data_quality_summary['unique_product_names']}
            - **Cross-Market Match Pairs:** {data_quality_summary['unique_match_keys']} (36 Exact SKU + 2 Regional Variants)
            - **Duplicate Product IDs:** {data_quality_summary['duplicate_id_count']}
            - **Semantic Duplicate Listings:** {data_quality_summary['semantic_duplicate_count']}
            - **Target Markets Covered:** {", ".join(data_quality_summary['target_markets'])}
            - **Documented FX Benchmark:** 1 GBP = {data_quality_summary['gbp_usd_exchange_rate']} USD
            - **FX Source Series:** {data_quality_summary['fx_source']}
            - **Multi-Rule Validation Status:** <span style="color:{status_color}; font-weight:bold;">{status_text}</span>
            """, unsafe_allow_html=True)

            st.markdown("**Enforced Multi-Rule Checks:**")
            st.markdown("""
            1. ✔️ Required schema columns present (`cross_market_match_id`, `verification_status`, etc.)
            2. ✔️ Market codes strictly restricted to `{'US', 'UK'}`
            3. ✔️ Currency codes restricted to valid currencies `{'USD', 'GBP', 'JPY'}`
            4. ✔️ All prices strictly positive (`local_price > 0`)
            5. ✔️ All ratings within `[1.0, 5.0]` (or null)
            6. ✔️ All review counts non-negative integers (or null)
            7. ✔️ All source URLs valid HTTP/HTTPS links
            8. ✔️ Zero duplicate product IDs
            """)

            st.markdown("**Missing Fields Summary:**")
            if data_quality_summary["missing_fields"]:
                missing_df = pd.DataFrame.from_dict(data_quality_summary["missing_fields"], orient="index")
                st.dataframe(missing_df, use_container_width=True)
            else:
                st.success("No missing fields detected.")

        with audit_c2:
            st.subheader("Methodological Protocol & Tax Treatment")
            st.markdown("""
            **1. Source Verification Protocol:**  
            All listings were manually verified against live product pages on JetPens, Cult Pens, Amazon US, Amazon UK, London Graphic Centre, and Yoseka Stationery. Source URLs, pack quantities, and seller types are preserved for full verification.
            
            **2. Currency Standardization:**  
            Listed prices in GBP were converted to USD using the Bank of England daily 4pm close reference rate of `1.3050` as of September 30, 2026 (Series `XUDLGBD`, cross-reconciled with Federal Reserve H.10 release `DEXUSUK`).
            
            **3. Structural Tax Differences:**  
            - **UK Listings:** Under UK law, displayed prices are inclusive of 20% Value-Added Tax (VAT).
            - **US Listings:** Displayed prices exclude local state sales taxes.
            - To prevent misleading conclusions regarding price premiums, the dashboard provides both *Nominal* and *Pre-Tax (VAT Removed)* comparisons.
            
            **4. Null Value Integrity:**  
            Items lacking published customer ratings or reviews (Kokuyo Campus Soft Ring UK Cult Pens listing) are preserved as `NaN` (null) and are omitted from rating averages rather than coerced to zero.
            """)

        st.markdown("---")
        st.subheader("Analytical Scope & Known Limitations")
        st.markdown("""
        1. **Sample Size & Coverage:** This dataset covers 76 product-market observations across 38 matched pairs. While sufficient for category comparisons and hypothesis generation, it does not represent an exhaustive census of all Japanese stationery imports.
        2. **Retail Listing Price vs. Realized Sales:** Prices reflect public listing prices (MSRP). Realized sales volumes, promotional clearances, and wholesale invoice prices are proprietary to retailers.
        3. **Specialist Channel Skew:** Retailers like JetPens and Cult Pens cater to design and stationery enthusiasts who may exhibit higher price tolerance than general hypermarket shoppers.
        4. **Testable Hypotheses Disclaimer:** All identified market white spaces and pricing opportunities are explicitly framed as hypotheses for management to validate through distributor discussions or localized pilot testing.
        """)


if __name__ == "__main__":
    main()

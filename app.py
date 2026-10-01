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
    page_title="CrossMarket | US-UK Launch Screening",
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
    total_project_categories = int(df_clean["product_category"].nunique())

    # ==========================================
    # SIDEBAR: INTERACTIVE FILTERS
    # ==========================================
    st.sidebar.title("🗾 CrossMarket")
    st.sidebar.markdown("**US–UK Launch Screening**")
    st.sidebar.caption("A first-pass pricing and retail-entry research shortlist")
    st.sidebar.markdown("---")

    st.sidebar.subheader("Filter Controls")

    # 1. Brand Filter
    available_brands = sorted(df_clean["brand"].unique().tolist())
    selected_brands = st.sidebar.multiselect(
        "Select Brand(s):",
        options=available_brands,
        default=available_brands
    )

    # 2. Category Filter
    available_categories = sorted(df_clean["product_category"].unique().tolist())
    selected_categories = st.sidebar.multiselect(
        "Select Category:",
        options=available_categories,
        default=available_categories
    )

    # 3. Tax Normalization Mode
    st.sidebar.markdown("---")
    st.sidebar.subheader("Tax Normalization Basis")
    vat_mode = st.sidebar.radio(
        "UK Price Display:",
        options=["Nominal (Includes 20% UK VAT)", "Pre-Tax (VAT Removed)"],
        help="UK retail prices legally include 20% VAT; US prices exclude sales tax at checkout. Choose Pre-Tax for like-for-like pre-tax comparison."
    )
    use_ex_vat = (vat_mode == "Pre-Tax (VAT Removed)")
    active_price_col = "price_usd_ex_vat" if use_ex_vat else "price_usd"

    # 4. Price Range Slider (Bounded strictly by active price basis)
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

    # 5. Cross-Market Matching Mode Filter
    st.sidebar.markdown("---")
    st.sidebar.subheader("Which recorded pair labels should be included?")
    match_scope = st.sidebar.selectbox(
        "Include pair labels:",
        options=["All recorded labels", "Only labels marked exact SKU & pack"],
        help="These labels come from the source CSV. The source audit found that pair equivalence is not independently established for every pair; review the methodology tab before interpreting comparisons."
    )
    match_mode = "exact_only" if "Only labels" in match_scope else "all"

    # Apply Filters to dataset
    filtered_df = df_clean.copy()
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
    st.title("🗾 CrossMarket: US–UK Launch Screening")
    st.markdown(
        "**A first-pass screen to identify which Japanese stationery products and categories deserve deeper US/UK pricing and retail-entry research.**"
    )

    # Methodological Callout
    st.markdown("""
    <div class="method-callout">
        <b>Decision goal:</b> Use a <b>curated sample of retail listings</b> from JetPens, Cult Pens, Amazon US/UK, London Graphic Centre, and Yoseka as a first screen for where a Japanese stationery brand might investigate US/UK pricing and retail entry. 
        <b>These results are exploratory hypotheses, not proof of demand.</b> Some links, prices, stock states, and product matches remain unverified.
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
    premium_column = "vat_adj_premium_pct" if use_ex_vat else "nominal_premium_pct"
    premium_label = "Pre-tax" if use_ex_vat else "Nominal"
    category_premiums = (
        active_parity.groupby("category")[premium_column].mean()
        if not active_parity.empty else pd.Series(dtype=float)
    )
    categories_above_parity = int((category_premiums > 0).sum())
    mean_sample_premium = float(active_parity[premium_column].mean()) if not active_parity.empty else None

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
        <div class="kpi-title">Listings in current selection</div>
            <div class="kpi-val">{active_kpis['total_observations']}</div>
            <div class="kpi-sub">{active_kpis['unique_products']} distinct product names</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
        <div class="kpi-title">Matched pairs in current selection</div>
            <div class="kpi-val">{len(active_parity)}</div>
            <div class="kpi-sub">Recorded US–UK match IDs in current filters</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        premium_display = f"{mean_sample_premium:+.1f}%" if mean_sample_premium is not None else "N/A"
        st.markdown(f"""
        <div class="metric-card">
        <div class="kpi-title">Average UK price difference ({premium_label})</div>
            <div class="kpi-val">{premium_display}</div>
            <div class="kpi-sub">Mean across currently compared pairs</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
        <div class="kpi-title">Categories with higher UK average</div>
            <div class="kpi-val">{categories_above_parity}/{total_project_categories}</div>
            <div class="kpi-sub">Categories above parity within selected filters</div>
        </div>
        """, unsafe_allow_html=True)

    # ==========================================
    # NAVIGATION TABS
    # ==========================================
    tabs = st.tabs([
        "📊 US–UK Pricing Screen",
        "🏷️ Brand & Retail Coverage",
        "💡 What to Investigate Next",
        "🔍 Compare Sample Listings",
        "📋 Findings Report",
        "🛡️ Data Quality & Methodology"
    ])

    # ----------------------------------------------------
    # TAB 1: MARKET & PRICING PARITY
    # ----------------------------------------------------
    with tabs[0]:
        st.markdown('<div class="section-header">1. Where should the company investigate pricing first?</div>', unsafe_allow_html=True)
        st.caption("Start with broad category price patterns, then use matched listings to identify specific products for follow-up. Every result describes this exploratory sample only.")

        if not active_parity.empty:
            st.subheader("How do average listed prices compare between the UK and US?")
            st.caption("This is a signed comparison: bars right of 0% mean UK prices are higher; bars left of 0% mean UK prices are lower. Category averages can hide individual products that go the other way.")
            cat_summary = (
                active_parity.groupby("category")[premium_column]
                .agg(["mean", "count"]).reset_index()
                .rename(columns={"category": "Product Category", "mean": "Average UK–US Price Difference (%)", "count": "Compared Pairs"})
                .sort_values("Average UK–US Price Difference (%)", ascending=True)
            ) if not active_parity.empty else pd.DataFrame(columns=["Product Category", "Average UK–US Price Difference (%)", "Compared Pairs"])
            fig_bar = px.bar(
                cat_summary,
                x="Average UK–US Price Difference (%)",
                y="Product Category",
                orientation="h",
                color="Average UK–US Price Difference (%)",
                color_continuous_scale=["#2563EB", "#94A3B8", "#DC2626"],
                color_continuous_midpoint=0,
                labels={
                    "Average UK–US Price Difference (%)": f"Average UK–US price difference ({premium_label}, %)",
                    "Product Category": "Category"
                },
                hover_data=["Compared Pairs"],
                text=cat_summary["Average UK–US Price Difference (%)"].map(lambda value: f"{value:+.1f}%"),
                title=f"Which categories are cheaper or more expensive in the UK? ({premium_label})"
            )
            fig_bar.add_vline(x=0, line_dash="dash", line_color="#64748B", annotation_text="Price parity (0%)")
            fig_bar.update_layout(
                coloraxis_showscale=False,
                uniformtext_minsize=10,
                uniformtext_mode="hide",
                margin=dict(l=20, r=20, t=50, b=20)
            )
            fig_bar.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(fig_bar, width="stretch")
        else:
            st.info("No recorded US–UK matched pairs remain in this selection. Broaden the brand, category, or price filters to continue the comparison.")

        # Cross-Market Matched SKU Parity Section
        st.markdown('<div class="section-header">Which recorded products are worth a closer price check?</div>', unsafe_allow_html=True)
        if not active_parity.empty:
            prem_col = "vat_adj_premium_pct" if use_ex_vat else "nominal_premium_pct"
            diff_label = "VAT-Adjusted Premium (%)" if use_ex_vat else "Nominal Premium (%)"

            st.caption(f"Displaying **{len(active_parity)} recorded pair comparisons** ({match_scope}). Bars to the right of 0% have a higher UK listed price; bars to the left have a lower UK listed price. Use this as a shortlist for source checks, not as proof of demand or profit.")

            fig_parity = px.bar(
                active_parity,
                x=prem_col,
                y="product_name",
                orientation="h",
                color=prem_col,
                color_continuous_scale=["#2563EB", "#94A3B8", "#DC2626"],
                color_continuous_midpoint=0,
                hover_data=[
                    "cross_market_match_id", "match_quality", "brand",
                    "us_price_usd", "uk_price_usd", "uk_price_usd_ex_vat",
                    "us_retailer", "uk_retailer", "match_notes"
                ],
                labels={prem_col: diff_label, "product_name": "Matched Product"},
                title=f"Which matched products are cheaper or more expensive in the UK? ({diff_label})"
            )
            fig_parity.add_vline(x=0, line_dash="dash", line_color="black", annotation_text="Price parity (0%)")
            fig_parity.update_layout(
                yaxis={"categoryorder": "total ascending"},
                height=max(650, min(1450, 30 * len(active_parity) + 180)),
                margin=dict(l=20, r=20, t=50, b=40),
                coloraxis_colorbar=dict(title=f"UK–US<br>difference (%)")
            )
            st.plotly_chart(fig_parity, width="stretch")

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
                st.dataframe(disp_parity, width="stretch")
        else:
            st.info("No cross-market matched product pairs found in the current filter selection.")

    # ----------------------------------------------------
    # TAB 2: BRAND & CATEGORY POSITIONING
    # ----------------------------------------------------
    with tabs[1]:
        st.markdown('<div class="section-header">2. Which brands and retailers appear in the sample?</div>', unsafe_allow_html=True)
        st.caption("Use this view to see where the sample has enough US/UK brand and retailer coverage to investigate further. Counts describe collected rows only; they are not market shares or proof of distribution.")

        brand_pos = get_brand_positioning_summary(filtered_df)

        b_c1, b_c2 = st.columns([1, 1])

        with b_c1:
            st.subheader("How many listings per brand were recorded in each market?")
            brand_coverage = brand_pos.melt(
                id_vars="brand",
                value_vars=["us_count", "uk_count"],
                var_name="market",
                value_name="Sample listings"
            )
            brand_coverage["market"] = brand_coverage["market"].map({"us_count": "US", "uk_count": "UK"})
            brand_order = brand_pos.sort_values("product_count", ascending=True)["brand"].tolist()
            fig_coverage = px.bar(
                brand_coverage,
                x="Sample listings",
                y="brand",
                color="market",
                barmode="group",
                orientation="h",
                text="Sample listings",
                category_orders={"brand": brand_order, "market": ["US", "UK"]},
                color_discrete_map={"US": "#2563EB", "UK": "#DC2626"},
                labels={"brand": "Brand", "market": "Market"},
                title="How many sampled listings per brand are recorded in the US and UK?"
            )
            fig_coverage.update_layout(
                height=max(500, 34 * len(brand_order) + 100),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=50, b=20),
                yaxis_title=None
            )
            fig_coverage.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(fig_coverage, width="stretch")

        with b_c2:
            st.subheader("How do brands' median listed prices compare in this sample?")
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
                title="What is the median recorded price for each brand?"
            )
            fig_brand_bar.update_layout(
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=50, b=20)
            )
            st.plotly_chart(fig_brand_bar, width="stretch")

        # Brand Portfolio Summary Table
        st.subheader("What sample counts and prices sit behind the brand comparison?")
        st.caption("Counts describe only rows in this curated sample. They do not measure market share, actual availability, or sales.")
        st.dataframe(
            brand_pos[[
                "brand", "brand_origin", "positioning_tier", "primary_category",
                "product_count", "us_count", "uk_count", "median_price_usd"
            ]].rename(columns={
                "brand": "Brand",
                "brand_origin": "Origin",
                "positioning_tier": "Positioning Tier",
                "primary_category": "Primary Category",
                "product_count": "Sample rows",
                "us_count": "US sample rows",
                "uk_count": "UK sample rows",
                "median_price_usd": "Median Price ($)"
            }),
            width="stretch"
        )

        # Retailer and Brand Summary Table
        coverage = get_coverage_breakdown(filtered_df)
        st.subheader("How are sample listings distributed across categories and retailers?")
        ret_c1, ret_c2 = st.columns([1, 1])
        with ret_c1:
            st.markdown("**How many listings were sampled in each category and market?**")
            st.dataframe(coverage["category_market"], width="stretch")
        with ret_c2:
            st.markdown("**What listing counts, brand counts, and median prices are recorded per retailer?**")
            retailer_display = coverage["retailer_summary"][[
                "retailer", "target_market", "product_count", "brands_carried", "median_price_usd"
            ]].rename(columns={
                "retailer": "Retailer",
                "target_market": "Market",
                "product_count": "Sample rows",
                "brands_carried": "Brands in sample",
                "median_price_usd": "Median listed price ($)"
            })
            st.dataframe(retailer_display, width="stretch")

    # ----------------------------------------------------
    # TAB 3: STRATEGIC HYPOTHESES & OPPORTUNITIES
    # ----------------------------------------------------
    with tabs[2]:
        st.markdown('<div class="section-header">3. What should the company investigate next?</div>', unsafe_allow_html=True)

        st.markdown("""
        > **How to use this section:** These are research questions based on the recorded sample, not recommendations or proof of demand. The dataset contains listing prices and sample coverage; it does not contain sales, costs, or customer experiments.
        """)

        st.caption("Recommended sequence: confirm source listings and exact variants, broaden retailer coverage, then collect sales, cost, and customer evidence before making a pricing or launch decision.")
        hypo_results = identify_price_segments_and_hypotheses(filtered_df, active_parity)

        relevant_hypotheses = [h for h in hypo_results["hypotheses"] if h["id"] != "HYP-03"]
        for display_number, h in enumerate(relevant_hypotheses, start=1):
            st.markdown(f"""
            <div class="hypo-box">
                <span class="hypo-tag">NEXT-{display_number:02d}</span>
                <div class="hypo-title">{h['title']}</div>
                <p><b>What the sample shows:</b> {h['observation']}</p>
                <p><b>What it does not establish:</b> {h['hypothesis']}</p>
                <p><b>Evidence scope:</b> <i>{h['evidence']}</i></p>
                <p><b>Practical next check:</b> 🎯 {h['testable_action']}</p>
                <div style="margin-top:10px;">
                    <span class="badge-caveat">⚠️ Methodological Boundary: {h['limitation_note']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ----------------------------------------------------
    # TAB 4: PRODUCT EXPLORER & URLS
    # ----------------------------------------------------
    with tabs[3]:
        st.markdown('<div class="section-header">4. Which recorded listings need checking?</div>', unsafe_allow_html=True)
        st.markdown(
            "Use this evidence table to check the US and UK listing, seller, pack size, price, and source URL behind a comparison before treating it as a real pricing opportunity. Some URLs may be stale or inaccessible, and not every variant has been independently rechecked."
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
            width="stretch",
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
        st.markdown('<div class="section-header">5. Baseline findings behind the screening decision</div>', unsafe_allow_html=True)
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
        st.markdown('<div class="section-header">6. How reliable is this analysis, and what are its limits?</div>', unsafe_allow_html=True)

        audit_c1, audit_c2 = st.columns([1, 1])

        with audit_c1:
            st.subheader("Do the recorded rows pass the data rules?")
            status_color = "#059669" if data_quality_summary["validation_passed"] else "#DC2626"
            status_text = "PASSED (Zero Schema or Rule Violations)" if data_quality_summary["validation_passed"] else "FAILED"
            
            st.markdown(f"""
            - **Rows Passing Data-Quality Rules:** {data_quality_summary['clean_row_count']} (schema/calculations only; not retailer verification)
            - **Distinct Product Models:** {data_quality_summary['unique_product_names']}
            - **Recorded Cross-Market Pair Keys:** {data_quality_summary['unique_match_keys']} (CSV labels: 36 exact, 2 variants; not all pair equivalence rechecked)
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
                st.dataframe(missing_df, width="stretch")
            else:
                st.success("No missing fields detected.")

        with audit_c2:
            st.subheader("How were prices standardized and what was verified?")
            st.markdown("""
            **1. Source Verification Protocol:**  
            The CSV records source URLs and collection claims for listings attributed to JetPens, Cult Pens, Amazon US, Amazon UK, London Graphic Centre, and Yoseka Stationery. A later partial source audit found stale links and could not independently reproduce every listing, price, seller, variant, or stock claim. See `reports/source_verification_audit.md`. Treat these records as a curated exploratory sample, not a fully re-verified live-price dataset.
            
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
        st.subheader("What can this sample not tell us?")
        st.markdown("""
        1. **Sample Size & Coverage:** This dataset contains 76 recorded product-market observations across 38 proposed match pairs. It is a curated exploratory sample, not an exhaustive census; some pair matches and source fields remain unverified.
        2. **Retail Listing Price vs. Realized Sales:** Prices reflect public listing prices (MSRP). Realized sales volumes, promotional clearances, and wholesale invoice prices are proprietary to retailers.
        3. **Specialist Channel Skew:** Retailers like JetPens and Cult Pens cater to design and stationery enthusiasts who may exhibit higher price tolerance than general hypermarket shoppers.
        4. **Testable Hypotheses Disclaimer:** All identified market white spaces and pricing opportunities are explicitly framed as hypotheses for management to validate through distributor discussions or localized pilot testing.
        """)


if __name__ == "__main__":
    main()


"""
CrossMarket - Japanese Product Market Analysis Dashboard
src/analysis.py: Rigorous Cross-Market Matching, Parity Calculations, Positioning, and Dynamic Hypothesis Generation
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
import numpy as np


def _format_percentage(value: float) -> str:
    """Format percentages consistently, including exact half-tenth values."""
    rounded = Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{rounded:+}%"


def get_cross_market_parity(df: pd.DataFrame, match_mode: str = "all") -> pd.DataFrame:
    """
    Identifies and pairs identical or closely matched products across US and UK markets
    using the stable 'cross_market_match_id'.
    
    Validates that:
    1. The match key exists in both markets.
    2. Brands match across the pair.
    3. Pack quantities match across the pair.
    
    Args:
        df: Cleaned dataframe.
        match_mode: 'all' (all 38 validated pairs) or 'exact_only' (36 exact SKU & pack matches).
        
    Returns:
        DataFrame of paired cross-market comparisons with nominal and VAT-adjusted metrics.
    """
    us_df = df[df["target_market"] == "US"].copy()
    uk_df = df[df["target_market"] == "UK"].copy()

    if "cross_market_match_id" not in df.columns:
        raise ValueError("Missing 'cross_market_match_id' column in dataset.")

    # Merge on stable match key
    merged = pd.merge(
        us_df,
        uk_df,
        on="cross_market_match_id",
        suffixes=("_us", "_uk")
    )

    if merged.empty:
        return pd.DataFrame()

    results = []
    for _, row in merged.iterrows():
        # Quality check: ensure brand matches
        if row["brand_us"] != row["brand_uk"]:
            continue
        # Quality check: ensure pack quantity matches
        if int(row.get("pack_quantity_us", 1)) != int(row.get("pack_quantity_uk", 1)):
            continue

        match_qual = row.get("match_quality_us", "Exact SKU & Pack Match")
        if match_mode == "exact_only" and match_qual != "Exact SKU & Pack Match":
            continue

        us_price = float(row["price_usd_us"])
        uk_price_nominal = float(row["price_usd_uk"])
        uk_price_ex_vat = float(row.get("price_usd_ex_vat_uk", round(uk_price_nominal / 1.20, 2)))
        uk_price_local = float(row["local_price_uk"])
        pack_q = int(row.get("pack_quantity_us", 1))

        nominal_diff = round(uk_price_nominal - us_price, 2)
        nominal_pct = round(((uk_price_nominal - us_price) / us_price) * 100, 1) if us_price > 0 else 0.0

        vat_adj_diff = round(uk_price_ex_vat - us_price, 2)
        vat_adj_pct = round(((uk_price_ex_vat - us_price) / us_price) * 100, 1) if us_price > 0 else 0.0

        results.append({
            "cross_market_match_id": row["cross_market_match_id"],
            "match_quality": match_qual,
            "match_notes": row.get("match_notes_us", ""),
            "product_name_us": row["product_name_us"],
            "product_name_uk": row["product_name_uk"],
            "product_name": row["product_name_us"],  # Canonical display name
            "brand": row["brand_us"],
            "category": row["product_category_us"],
            "pack_quantity": pack_q,
            "us_price_usd": us_price,
            "uk_price_gbp": uk_price_local,
            "uk_price_usd": uk_price_nominal,
            "uk_price_usd_ex_vat": uk_price_ex_vat,
            "us_unit_price_usd": round(us_price / pack_q, 2),
            "uk_unit_price_usd": round(uk_price_nominal / pack_q, 2),
            "nominal_diff_usd": nominal_diff,
            "nominal_premium_pct": nominal_pct,
            "vat_adj_diff_usd": vat_adj_diff,
            "vat_adj_premium_pct": vat_adj_pct,
            "us_retailer": row["retailer_us"],
            "uk_retailer": row["retailer_uk"],
            "us_seller_type": row.get("seller_type_us", "Retailer"),
            "uk_seller_type": row.get("seller_type_uk", "Retailer"),
            "us_rating": row["product_rating_us"],
            "uk_rating": row["product_rating_uk"],
            "us_url": row["product_url_us"],
            "uk_url": row["product_url_uk"]
        })

    parity_df = pd.DataFrame(results)
    if not parity_df.empty:
        parity_df = parity_df.sort_values(by="nominal_premium_pct", ascending=False)
    return parity_df


def get_executive_kpis(df: pd.DataFrame, parity_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    Computes top-level executive KPIs from the cleaned catalog and paired observations.
    Clearly distinguishes distinct metrics (unique product names vs matched pairs).
    """
    us_mask = df["target_market"] == "US"
    uk_mask = df["target_market"] == "UK"

    if parity_df is None:
        try:
            parity_df = get_cross_market_parity(df, match_mode="all")
        except Exception:
            parity_df = pd.DataFrame()

    matched_pairs_total = len(parity_df)
    matched_exact = len(parity_df[parity_df["match_quality"] == "Exact SKU & Pack Match"]) if not parity_df.empty else 0
    matched_variants = matched_pairs_total - matched_exact

    # Premium metrics
    if not parity_df.empty:
        mean_nom_prem = round(float(parity_df["nominal_premium_pct"].mean()), 1)
        median_nom_prem = round(float(parity_df["nominal_premium_pct"].median()), 1)
        mean_vat_prem = round(float(parity_df["vat_adj_premium_pct"].mean()), 1)
        median_vat_prem = round(float(parity_df["vat_adj_premium_pct"].median()), 1)
    else:
        mean_nom_prem = median_nom_prem = mean_vat_prem = median_vat_prem = 0.0

    rated_subset = df["product_rating"].dropna()
    avg_rating = round(float(rated_subset.mean()), 2) if not rated_subset.empty else 0.0
    rated_count = int(len(rated_subset))

    return {
        "total_observations": int(len(df)),
        "us_observations": int(us_mask.sum()),
        "uk_observations": int(uk_mask.sum()),
        "unique_brands": int(df["brand"].nunique()),
        "unique_products": int(df["product_name"].nunique()),
        "unique_categories": int(df["product_category"].nunique()),
        "unique_retailers": int(df["retailer"].nunique()),
        "overall_median_usd": round(float(df["price_usd"].median()), 2),
        "overall_mean_usd": round(float(df["price_usd"].mean()), 2),
        "us_median_usd": round(float(df[us_mask]["price_usd"].median()), 2) if us_mask.any() else 0.0,
        "us_mean_usd": round(float(df[us_mask]["price_usd"].mean()), 2) if us_mask.any() else 0.0,
        "uk_median_usd": round(float(df[uk_mask]["price_usd"].median()), 2) if uk_mask.any() else 0.0,
        "uk_mean_usd": round(float(df[uk_mask]["price_usd"].mean()), 2) if uk_mask.any() else 0.0,
        "uk_median_usd_ex_vat": round(float(df[uk_mask]["price_usd_ex_vat"].median()), 2) if uk_mask.any() else 0.0,
        "uk_mean_usd_ex_vat": round(float(df[uk_mask]["price_usd_ex_vat"].mean()), 2) if uk_mask.any() else 0.0,
        "average_rating": avg_rating,
        "rated_products_count": rated_count,
        "total_reviews": int(df["review_count"].dropna().sum()),
        "matched_pairs_total": matched_pairs_total,
        "matched_pairs_exact_sku": matched_exact,
        "matched_pairs_variant": matched_variants,
        "mean_nominal_premium_pct": mean_nom_prem,
        "median_nominal_premium_pct": median_nom_prem,
        "mean_vat_adj_premium_pct": mean_vat_prem,
        "median_vat_adj_premium_pct": median_vat_prem
    }


def get_price_summary_by_dimension(df: pd.DataFrame, dimension: str = "brand") -> pd.DataFrame:
    """
    Calculates aggregated pricing statistics (mean, median, min, max, std)
    grouped by brand, product_category, target_market, or retailer.
    """
    if dimension not in df.columns:
        raise ValueError(f"Dimension '{dimension}' not found in dataframe columns.")

    summary = df.groupby(dimension).agg(
        product_count=("product_id", "count"),
        mean_price_usd=("price_usd", "mean"),
        median_price_usd=("price_usd", "median"),
        min_price_usd=("price_usd", "min"),
        max_price_usd=("price_usd", "max"),
        std_price_usd=("price_usd", "std")
    ).reset_index()

    for col in ["mean_price_usd", "median_price_usd", "min_price_usd", "max_price_usd", "std_price_usd"]:
        summary[col] = summary[col].round(2).fillna(0.0)

    summary = summary.sort_values(by="median_price_usd", ascending=False)
    return summary


def get_brand_positioning_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarizes brand positioning metrics: median price, average rating,
    review volume, catalog breadth, and origin tier.
    """
    records = []
    for brand, group in df.groupby("brand"):
        median_p = round(float(group["price_usd"].median()), 2)
        mean_p = round(float(group["price_usd"].mean()), 2)
        rated = group["product_rating"].dropna()
        avg_rating = round(float(rated.mean()), 2) if not rated.empty else np.nan
        total_rev = int(group["review_count"].dropna().sum())
        count = len(group)
        us_count = len(group[group["target_market"] == "US"])
        uk_count = len(group[group["target_market"] == "UK"])
        origin = group["brand_origin"].iloc[0] if "brand_origin" in group.columns else "Unknown"
        top_cat = group["product_category"].mode().iloc[0] if not group["product_category"].empty else "Mixed"

        if median_p < 7.0:
            positioning = "Mass Utility & Value"
        elif median_p <= 15.0:
            positioning = "Accessible Design & Writing"
        elif median_p <= 35.0:
            positioning = "Premium Functional / Journaling"
        else:
            positioning = "Luxury / Specialist Heritage"

        records.append({
            "brand": brand,
            "brand_origin": origin,
            "primary_category": top_cat,
            "product_count": count,
            "us_count": us_count,
            "uk_count": uk_count,
            "median_price_usd": median_p,
            "mean_price_usd": mean_p,
            "average_rating": avg_rating,
            "rated_products": len(rated),
            "total_reviews": total_rev,
            "positioning_tier": positioning
        })

    pos_df = pd.DataFrame(records)
    return pos_df.sort_values(by="median_price_usd", ascending=False)


def get_coverage_breakdown(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Computes cross-tabulated coverage breakdowns across markets, categories, and retailers.
    """
    cat_market = pd.crosstab(
        df["product_category"],
        df["target_market"],
        margins=True,
        margins_name="Total"
    ).reset_index()

    retailer_summary = df.groupby(["retailer", "target_market"]).agg(
        product_count=("product_id", "count"),
        brands_carried=("brand", "nunique"),
        median_price_usd=("price_usd", "median"),
        avg_rating=("product_rating", "mean")
    ).reset_index()
    retailer_summary["median_price_usd"] = retailer_summary["median_price_usd"].round(2)
    retailer_summary["avg_rating"] = retailer_summary["avg_rating"].round(2)

    return {
        "category_market": cat_market,
        "retailer_summary": retailer_summary.sort_values(by="product_count", ascending=False)
    }


def identify_price_segments_and_hypotheses(
    df: pd.DataFrame,
    parity_df: Optional[pd.DataFrame] = None
) -> Dict[str, Any]:
    """
    Evaluates price tier distribution and generates dynamic, mathematically reconciled
    business hypotheses regarding price markups, category white spaces, and retailer positioning.
    
    IMPORTANT: All opportunities are explicitly framed as hypotheses rather than proof of market demand.
    """
    if parity_df is None or parity_df.empty:
        try:
            parity_df = get_cross_market_parity(df, match_mode="all")
        except Exception:
            parity_df = pd.DataFrame()

    tier_counts = df.groupby(["price_tier", "target_market"]).size().unstack(fill_value=0).reset_index()

    # Dynamic metrics from active parity table
    if not parity_df.empty:
        n_pairs = len(parity_df)
        mean_nom = parity_df["nominal_premium_pct"].mean()
        med_nom = parity_df["nominal_premium_pct"].median()
        mean_vat = parity_df["vat_adj_premium_pct"].mean()
        med_vat = parity_df["vat_adj_premium_pct"].median()
        
        # Category specific calculations
        cat_stats = parity_df.groupby("category").agg(
            nom_mean=("nominal_premium_pct", "mean"),
            vat_mean=("vat_adj_premium_pct", "mean"),
            count=("nominal_premium_pct", "count")
        ).to_dict("index")
    else:
        n_pairs = 0
        mean_nom = med_nom = mean_vat = med_vat = 0.0
        cat_stats = {}

    # Keep rating claims specific to Japanese brands, and label the denominator
    # as listings because the same product may appear in both markets.
    japanese = df[df.get("brand_origin", pd.Series(index=df.index, dtype=object)) == "Japanese Heritage"]
    japanese_ratings = japanese["product_rating"].dropna()
    japanese_rated_count = len(japanese_ratings)
    japanese_avg_rating = round(float(japanese_ratings.mean()), 2) if japanese_rated_count else None
    japanese_reviews = int(japanese["review_count"].dropna().sum())
    japanese_high_rating_pct = (
        round(float((japanese_ratings >= 4.6).mean()) * 100, 1)
        if japanese_rated_count else None
    )

    def category_premium(category: str) -> str:
        stats = cat_stats.get(category)
        if not stats:
            return "not available in this selection"
        return (
            f"{_format_percentage(stats['nom_mean'])} nominal / "
            f"{_format_percentage(stats['vat_mean'])} VAT-adjusted (n={int(stats['count'])})"
        )

    if n_pairs:
        overall_observation = (
            f"Across {n_pairs} matched pairs, UK listed prices average {_format_percentage(mean_nom)} nominal "
            f"({_format_percentage(mean_vat)} VAT-adjusted) higher than US prices; medians are "
            f"{_format_percentage(med_nom)} and {_format_percentage(med_vat)} respectively."
        )
    else:
        overall_observation = "No matched US/UK pairs are present in the current filter selection."

    writing = df[df["product_category"] == "Pens & Writing"]
    writing_counts = writing.groupby("target_market").size().to_dict()
    writing_ranges = {}
    for market in ("US", "UK"):
        prices = writing.loc[writing["target_market"] == market, "price_usd"].dropna()
        writing_ranges[market] = (
            f"${prices.min():.2f}–${prices.max():.2f} across {len(prices)} listings"
            if len(prices) else "no listings in this selection"
        )

    desk_counts = df.groupby("target_market").size()
    desk_listings = df[df["product_category"] == "Desk Accessories"].groupby("target_market").size()
    desk_coverage = {}
    for market in ("US", "UK"):
        total = int(desk_counts.get(market, 0))
        count = int(desk_listings.get(market, 0))
        share = f"{100 * count / total:.1f}%" if total else "n/a"
        desk_coverage[market] = f"{count}/{total} listings ({share})"

    hypotheses = [
        {
            "id": "HYP-01",
            "title": "UK Import Premium Disparity on Specialty Paper & Art Markers",
            "observation": (
                f"{overall_observation} Category results in this selection: Highlighters & Markers "
                f"{category_premium('Highlighters & Markers')}; Notebooks & Pads "
                f"{category_premium('Notebooks & Pads')}."
            ),
            "hypothesis": (
                "UK consumers and boutique stockists demonstrate higher price tolerance for imported Japanese specialty paper and art supplies "
                "due to fewer domestic direct-import channels, suggesting Japanese paper mills could capture higher gross margin through dedicated UK distribution."
            ),
            "evidence": f"Computed from the {n_pairs} matched pairs currently in the selection; category sample sizes are shown with each result.",
            "testable_action": (
                "Pilot direct-to-consumer (DTC) UK storefronts and specialized university/art school wholesale accounts to test volume elasticity at current price points."
            ),
            "limitation_note": (
                "Hypothesis only. Reflects advertised retail prices at specialist stockists; does not measure sales volume, inventory clearance, or wholesale margin."
            )
        },
        {
            "id": "HYP-02",
            "title": "Mass-Market Ballpoint/Gel Pen Price Elasticity Ceiling (<$5)",
            "observation": (
                f"Pens & Writing listing prices span {writing_ranges['US']} in the US and "
                f"{writing_ranges['UK']} in the UK ({int(writing_counts.get('US', 0)) + int(writing_counts.get('UK', 0))} listings total). "
                "Listing prices and review counts alone do not measure price elasticity."
            ),
            "hypothesis": (
                "Everyday writing instruments face sharp price elasticity in both markets due to entrenched Western commodity pens (Sharpie S-Gel, BIC). "
                "Japanese brands cannot command premium pricing on single pens without bundling or emphasizing specialized ergonomic features."
            ),
            "evidence": f"Current filtered sample: {int(writing_counts.get('US', 0))} US and {int(writing_counts.get('UK', 0))} UK Pens & Writing listings.",
            "testable_action": (
                "Prioritize bundled aesthetic multi-packs (e.g., Sarasa Vintage 5-pack) and university bookstore distribution rather than single-pen pegboard displays."
            ),
            "limitation_note": (
                "Amazon review counts reflect cumulative multi-year sales and do not distinguish third-party reseller listings from official MSRP."
            )
        },
        {
            "id": "HYP-03",
            "title": (
                f"Japanese Listing Satisfaction (★ {japanese_avg_rating} Average)"
                if japanese_avg_rating is not None else "Japanese Listing Satisfaction (no rated listings)"
            ),
            "observation": (
                f"Japanese-brand listings average ★ {japanese_avg_rating} / 5.0 across {japanese_rated_count} rated listings "
                f"and {japanese_reviews:,} logged listing reviews. "
                + (f"{japanese_high_rating_pct}% of those listings score 4.6 or higher."
                   if japanese_rated_count else "No Japanese-brand ratings are present in this selection.")
            ),
            "hypothesis": (
                "Product quality, paper performance (bleed resistance with fountain pens), and mechanical precision "
                "create high organic brand advocacy, reducing the need for aggressive brand awareness ad spend if distributor retail placement is secured."
            ),
            "evidence": f"Japanese-brand subset: {japanese_rated_count} rated listings and {japanese_reviews:,} logged listing reviews.",
            "testable_action": (
                "Focus retail buyer pitches on high customer satisfaction and repeat purchase retention rather than competing on initial shelf-space price discounting."
            ),
            "limitation_note": (
                "Review distributions may exhibit self-selection bias: consumers purchasing imported Japanese stationery from specialty retailers (JetPens, Cult Pens) "
                "are stationery enthusiasts with an existing predisposition toward positive evaluations."
            )
        },
        {
            "id": "HYP-04",
            "title": "Specialty Desk Accessories & Eco-Stationery Availability Gaps",
            "observation": (
                f"Desk Accessories account for {desk_coverage['US']} in the US and "
                f"{desk_coverage['UK']} in the UK within the current filtered sample. These curated listing counts do not establish market-wide availability."
            ),
            "hypothesis": (
                "A product category white space exists in the UK for innovative, eco-conscious desk accessories (e.g. stapleless binding, precision drafting erasers), "
                "where consumer novelty and sustainability appeal could open boutique retail channels."
            ),
            "evidence": f"Current filtered sample: US {desk_coverage['US']}; UK {desk_coverage['UK']}.",
            "testable_action": (
                "Present eco-stationery lines to UK design, museum, and corporate gift retailers (e.g., London Graphic Centre, Conran Shop)."
            ),
            "limitation_note": (
                "Lower observed product count in this sample may reflect sample collection focus on core writing and paper SKUs rather than true distributor absence."
            )
        }
    ]

    return {
        "tier_distribution": tier_counts,
        "hypotheses": hypotheses
    }


if __name__ == "__main__":
    from data_processing import run_pipeline
    df_clean, summary = run_pipeline()
    parity = get_cross_market_parity(df_clean, match_mode="all")
    kpis = get_executive_kpis(df_clean, parity)
    print("=== Executive KPIs (Audited & Reconciled) ===")
    for k, v in kpis.items():
        print(f"  {k}: {v}")

    print(f"\nTotal Matched Pairs: {kpis['matched_pairs_total']} (Exact SKU: {kpis['matched_pairs_exact_sku']}, Variants: {kpis['matched_pairs_variant']})")
    print(f"Nominal Premium (All 38 pairs) -> Mean: {kpis['mean_nominal_premium_pct']}%, Median: {kpis['median_nominal_premium_pct']}%")
    print(f"VAT-Adjusted Premium (All 38 pairs) -> Mean: {kpis['mean_vat_adj_premium_pct']}%, Median: {kpis['median_vat_adj_premium_pct']}%")

    parity_exact = get_cross_market_parity(df_clean, match_mode="exact_only")
    print(f"\nExact SKU Matches Only: {len(parity_exact)} pairs")
    print(f"Nominal Premium (36 exact pairs) -> Mean: {parity_exact['nominal_premium_pct'].mean():.1f}%, Median: {parity_exact['nominal_premium_pct'].median():.1f}%")
    print(f"VAT-Adjusted Premium (36 exact pairs) -> Mean: {parity_exact['vat_adj_premium_pct'].mean():.1f}%, Median: {parity_exact['vat_adj_premium_pct'].median():.1f}%")

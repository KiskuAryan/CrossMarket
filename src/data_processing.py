"""
CrossMarket - Japanese Product Market Analysis Dashboard
src/data_processing.py: Strict Data Loading, Cleaning, Multi-Rule Validation, and Currency Standardization
"""

from pathlib import Path
from typing import Dict, Tuple, Any, Optional, List
import pandas as pd
import numpy as np


def get_default_data_dir() -> Path:
    """Returns the default data directory relative to this script."""
    return Path(__file__).resolve().parent.parent / "data"


def load_data(data_dir: Optional[Path] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads raw product catalog and documented foreign exchange rates from CSV files.
    Strictly verifies that required files exist.
    """
    if data_dir is None:
        data_dir = get_default_data_dir()
    else:
        data_dir = Path(data_dir)

    products_path = data_dir / "products.csv"
    fx_path = data_dir / "fx_rates.csv"

    if not products_path.exists():
        raise FileNotFoundError(f"Missing required products dataset at: {products_path}")
    if not fx_path.exists():
        raise FileNotFoundError(f"Missing required FX rates dataset at: {fx_path}")

    df_products = pd.read_csv(products_path)
    df_fx = pd.read_csv(fx_path)

    if df_products.empty:
        raise ValueError(f"Products dataset at {products_path} is empty.")
    if df_fx.empty:
        raise ValueError(f"FX rates dataset at {fx_path} is empty.")

    return df_products, df_fx


def clean_and_validate_products(
    df_products: pd.DataFrame,
    df_fx: pd.DataFrame,
    strict_raise: bool = False
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Cleans raw product records, validates prices and currencies, computes standardized USD
    prices using documented exchange rates, detects duplicate records, and computes a detailed
    data quality and audit report.

    Args:
        df_products: Raw products dataframe.
        df_fx: Documented exchange rates dataframe.
        strict_raise: If True, raises ValueError upon any validation failure.

    Returns:
        Tuple of (df_clean, data_quality_summary)
    """
    df = df_products.copy()
    initial_row_count = len(df)
    validation_errors: List[str] = []

    # 1. Enforce Required Schema Columns
    required_cols = [
        "product_id", "cross_market_match_id", "match_quality", "product_name",
        "brand", "product_category", "target_market", "retailer", "local_price",
        "currency", "product_url", "verification_status", "pack_quantity"
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        err = f"Schema error: Missing required column(s): {missing_cols}"
        validation_errors.append(err)
        if strict_raise:
            raise ValueError(err)

    # 2. Text Normalization and Stripping
    string_cols = [
        "product_id", "cross_market_match_id", "match_quality", "match_notes",
        "product_name", "brand", "product_category", "product_type",
        "country_of_origin", "target_market", "retailer", "seller_type",
        "availability_status", "verification_status", "verification_notes",
        "product_url", "collection_date", "currency", "material",
        "product_features", "product_description", "data_quality_notes"
    ]
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    for col in ("product_id", "cross_market_match_id", "match_quality", "verification_status"):
        if col in df.columns:
            blank_mask = df[col].str.casefold().isin({"", "nan", "none"})
            if blank_mask.any():
                validation_errors.append(f"Found {int(blank_mask.sum())} row(s) with blank {col}.")

    # 3. Standardize Market and Currency Casing
    if "target_market" in df.columns:
        df["target_market"] = df["target_market"].str.upper()
    if "currency" in df.columns:
        df["currency"] = df["currency"].str.upper()

    # 4. Numeric Conversions
    for num_col in ["local_price", "product_rating", "review_count", "pack_quantity"]:
        if num_col in df.columns:
            df[num_col] = pd.to_numeric(df[num_col], errors="coerce")

    # Preserve invalid or missing pack quantities so validation can reject them.
    if "pack_quantity" not in df.columns:
        df["pack_quantity"] = np.nan
    else:
        df["pack_quantity"] = pd.to_numeric(df["pack_quantity"], errors="coerce")

    # 5. Strict Domain Validation Checks
    # Market domain
    valid_markets = {"US", "UK"}
    invalid_markets = df[~df["target_market"].isin(valid_markets)]["target_market"].unique().tolist()
    if invalid_markets:
        validation_errors.append(f"Invalid market code(s) detected: {invalid_markets}. Expected {valid_markets}.")

    # Currency domain
    valid_currencies = {"USD", "GBP", "JPY"}
    invalid_currencies = df[~df["currency"].isin(valid_currencies)]["currency"].unique().tolist()
    if invalid_currencies:
        validation_errors.append(f"Invalid currency code(s) detected: {invalid_currencies}. Expected {valid_currencies}.")

    allowed_match_quality = {"Exact SKU & Pack Match", "Closely Matched Regional Variant"}
    invalid_match_quality = sorted(set(df["match_quality"]) - allowed_match_quality)
    if invalid_match_quality:
        validation_errors.append(f"Invalid match_quality value(s): {invalid_match_quality}.")

    # Price validation: Must be strictly positive
    invalid_prices = df[df["local_price"].isna() | (df["local_price"] <= 0)]
    if not invalid_prices.empty:
        validation_errors.append(f"Found {len(invalid_prices)} row(s) with non-positive or null local_price.")

    # Rating validation: Must be between 1.0 and 5.0 (or null)
    rated_rows = df[df["product_rating"].notna()]
    out_of_bounds_ratings = rated_rows[(rated_rows["product_rating"] < 1.0) | (rated_rows["product_rating"] > 5.0)]
    if not out_of_bounds_ratings.empty:
        validation_errors.append(f"Found {len(out_of_bounds_ratings)} row(s) with product_rating outside [1.0, 5.0].")

    # Review count validation: Must be non-negative integer (or null)
    reviewed_rows = df[df["review_count"].notna()]
    invalid_reviews = reviewed_rows[
        (reviewed_rows["review_count"] < 0) | (reviewed_rows["review_count"] % 1 != 0)
    ]
    if not invalid_reviews.empty:
        validation_errors.append(f"Found {len(invalid_reviews)} row(s) with invalid review_count; counts must be non-negative integers.")

    invalid_packs = df[
        df["pack_quantity"].isna()
        | ~np.isfinite(df["pack_quantity"])
        | (df["pack_quantity"] <= 0)
        | (df["pack_quantity"] % 1 != 0)
    ]
    if not invalid_packs.empty:
        validation_errors.append(
            f"Found {len(invalid_packs)} row(s) with missing, non-positive, or non-integer pack_quantity."
        )
    else:
        df["pack_quantity"] = df["pack_quantity"].astype(int)

    # URL validation: Must be valid HTTP/HTTPS link
    invalid_urls = df[~df["product_url"].str.startswith(("http://", "https://"))]
    if not invalid_urls.empty:
        validation_errors.append(f"Found {len(invalid_urls)} row(s) with malformed or missing product_url.")

    # 6. Audit Missing Values (Distinguish True Nulls from Zero)
    missing_audit = {}
    for col in df.columns:
        null_count = int(df[col].isna().sum())
        if null_count > 0:
            missing_audit[col] = {
                "missing_count": null_count,
                "pct_missing": round((null_count / initial_row_count) * 100, 2)
            }

    # 7. Check for Duplicates
    dup_id_mask = df.duplicated(subset=["product_id"], keep=False)
    dup_id_count = int(dup_id_mask.sum())
    if dup_id_count > 0:
        validation_errors.append(f"Found {dup_id_count} duplicate product_id occurrences.")

    # Each match key must identify exactly one US and one UK record with
    # consistent brand and pack size. A key is the unit of parity analysis.
    match_errors = []
    if "cross_market_match_id" in df.columns:
        for match_id, group in df.groupby("cross_market_match_id", dropna=False):
            markets = group["target_market"].tolist()
            if len(group) != 2 or set(markets) != {"US", "UK"}:
                match_errors.append(f"{match_id}: expected exactly one US and one UK row")
                continue
            if group["brand"].nunique(dropna=False) != 1:
                match_errors.append(f"{match_id}: brand differs across paired rows")
            if group["pack_quantity"].nunique(dropna=False) != 1:
                match_errors.append(f"{match_id}: pack_quantity differs across paired rows")
            if group["match_quality"].nunique(dropna=False) != 1:
                match_errors.append(f"{match_id}: match_quality differs across paired rows")
            elif (
                group["match_quality"].iloc[0] == "Exact SKU & Pack Match"
                and group["product_name"].nunique(dropna=False) != 1
            ):
                match_errors.append(f"{match_id}: exact-match product names differ across paired rows")
    if match_errors:
        validation_errors.append(
            f"Found invalid cross-market match key(s): {'; '.join(match_errors[:10])}."
        )

    semantic_dup_mask = df.duplicated(subset=["product_name", "target_market", "retailer"], keep="first")
    semantic_dup_count = int(semantic_dup_mask.sum())
    if semantic_dup_count > 0:
        df = df[~semantic_dup_mask].copy()

    # 8. Documented FX Exchange Rate Extraction & Conversion
    # Do not silently fall back to arbitrary constants. Verify against df_fx.
    fx_rates = {"USD": 1.0}
    fx_sources = []
    for _, rate_row in df_fx.iterrows():
        base = str(rate_row.get("base_currency", "")).upper()
        quote = str(rate_row.get("quote_currency", "")).upper()
        rate = pd.to_numeric(rate_row.get("rate"), errors="coerce")
        if quote == "USD" and base in {"GBP", "JPY"}:
            if pd.isna(rate) or not np.isfinite(rate) or rate <= 0:
                validation_errors.append(f"Invalid {base}/USD exchange rate in FX data.")
            else:
                fx_rates[base] = float(rate)
                fx_sources.append(str(rate_row.get("source", "")))

    used_currencies = set(df["currency"].dropna().unique())
    missing_rates = sorted(currency for currency in used_currencies if currency not in fx_rates)
    if missing_rates:
        validation_errors.append(f"Missing documented USD conversion rate(s) for: {missing_rates}.")
        if strict_raise:
            raise ValueError(validation_errors[-1])

    gbp_usd_rate = fx_rates.get("GBP", np.nan)
    fx_source = "; ".join(source for source in fx_sources if source) or "No documented conversion rates"

    # Compute standardized USD price
    def compute_usd(row):
        curr = str(row["currency"]).upper()
        lp = row["local_price"]
        if pd.isna(lp):
            return np.nan
        rate = fx_rates.get(curr)
        if rate is None or pd.isna(rate):
            return np.nan
        return round(float(lp) * rate, 2)

    df["price_usd"] = df.apply(compute_usd, axis=1)

    # Compute VAT-exclusive USD price for like-for-like pre-tax comparison
    # UK prices include 20% statutory VAT; US prices exclude point-of-sale tax
    def compute_usd_ex_vat(row):
        p_usd = row["price_usd"]
        if pd.isna(p_usd):
            return np.nan
        if row["target_market"] == "UK":
            return round(p_usd / 1.20, 2)
        return p_usd

    df["price_usd_ex_vat"] = df.apply(compute_usd_ex_vat, axis=1)

    # Compute Unit Prices (Price / Pack Quantity)
    df["unit_price_usd"] = (df["price_usd"] / df["pack_quantity"]).round(2)
    df["unit_price_usd_ex_vat"] = (df["price_usd_ex_vat"] / df["pack_quantity"]).round(2)

    # 9. Price Tier Segmentation
    def assign_price_tier(price):
        if pd.isna(price):
            return "Unknown"
        if price < 10.0:
            return "Budget (<$10)"
        elif price <= 25.0:
            return "Mid-Range ($10-$25)"
        elif price <= 50.0:
            return "Premium ($25-$50)"
        return "Luxury ($50+)"

    df["price_tier"] = df["price_usd"].apply(assign_price_tier)

    # 10. Brand Origin Classification
    japanese_brands = {
        "MIDORI", "KOKUYO", "PILOT", "ZEBRA", "UNI (MITSUBISHI PENCIL)",
        "TOMBOW", "MARUMAN", "PLATINUM", "HOBONICHI"
    }
    df["brand_origin"] = df["brand"].apply(
        lambda b: "Japanese Heritage" if str(b).upper() in japanese_brands else "Western Competitor Benchmark"
    )

    # 11. Compile Data Quality Audit Summary
    validation_passed = (len(validation_errors) == 0)
    if strict_raise and not validation_passed:
        raise ValueError(f"Data validation failed with {len(validation_errors)} error(s): {validation_errors}")

    data_quality_summary = {
        "initial_row_count": initial_row_count,
        "clean_row_count": len(df),
        "unique_product_names": int(df["product_name"].nunique()),
        "unique_brands": int(df["brand"].nunique()),
        "unique_match_keys": int(df["cross_market_match_id"].nunique()) if "cross_market_match_id" in df.columns else 0,
        "target_markets": sorted(df["target_market"].unique().tolist()),
        "missing_fields": missing_audit,
        "duplicate_id_count": dup_id_count,
        "semantic_duplicate_count": semantic_dup_count,
        "gbp_usd_exchange_rate": gbp_usd_rate,
        "fx_source": fx_source,
        "validation_errors": validation_errors,
        "validation_passed": validation_passed
    }

    return df, data_quality_summary


def run_pipeline(data_dir: Optional[Path] = None, strict_raise: bool = True) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Executes the end-to-end data pipeline: loading, cleaning, validation, and enrichment.
    """
    df_raw, df_fx = load_data(data_dir)
    return clean_and_validate_products(df_raw, df_fx, strict_raise=strict_raise)


if __name__ == "__main__":
    df_clean, summary = run_pipeline()
    print("=== CrossMarket Data Processing Pipeline Verification ===")
    print(f"Total Verified Observations: {summary['clean_row_count']}")
    print(f"Unique Brands: {summary['unique_brands']}")
    print(f"Unique Cross-Market Match Keys: {summary['unique_match_keys']}")
    print(f"Target Markets: {summary['target_markets']}")
    print(f"Missing Fields: {summary['missing_fields']}")
    print(f"Validation Passed: {summary['validation_passed']} (Errors: {len(summary['validation_errors'])})")
    print(f"FX Benchmark: 1 GBP = {summary['gbp_usd_exchange_rate']} USD ({summary['fx_source']})")

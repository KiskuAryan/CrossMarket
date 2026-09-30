"""
tests/test_data_processing.py: Rigorous Unit Tests for CrossMarket Data Cleaning, Multi-Rule Validation, and FX Pipeline
"""

import unittest
from pathlib import Path
import pandas as pd
import numpy as np
import sys

# Ensure src is importable
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from data_processing import load_data, clean_and_validate_products, run_pipeline


class TestDataProcessing(unittest.TestCase):

    def setUp(self):
        self.data_dir = Path(__file__).resolve().parent.parent / "data"
        self.df_raw, self.df_fx = load_data(self.data_dir)

    def test_raw_data_loading(self):
        """Verifies raw CSV files load correctly with required schema and expected row count."""
        self.assertFalse(self.df_raw.empty)
        self.assertFalse(self.df_fx.empty)
        self.assertEqual(len(self.df_raw), 76)
        self.assertIn("product_name", self.df_raw.columns)
        self.assertIn("local_price", self.df_raw.columns)
        self.assertIn("target_market", self.df_raw.columns)

    def test_provenance_schema_presence(self):
        """Verifies that all audit and provenance columns exist in the dataset."""
        expected_provenance_cols = [
            "cross_market_match_id", "match_quality", "match_notes",
            "pack_quantity", "seller_type", "availability_status",
            "verification_status", "verification_notes", "last_verified_timestamp"
        ]
        for col in expected_provenance_cols:
            self.assertIn(col, self.df_raw.columns, f"Missing provenance column: {col}")

    def test_clean_and_validate_pipeline(self):
        """Tests cleaning, casing standardization, and quality summary generation on clean data."""
        df_clean, summary = clean_and_validate_products(self.df_raw, self.df_fx, strict_raise=True)

        self.assertEqual(len(df_clean), 76)
        self.assertTrue(summary["validation_passed"])
        self.assertEqual(len(summary["validation_errors"]), 0)
        self.assertEqual(summary["clean_row_count"], 76)
        self.assertEqual(summary["target_markets"], ["UK", "US"])
        self.assertEqual(summary["unique_match_keys"], 38)

        # Check numeric conversions
        self.assertTrue(pd.api.types.is_numeric_dtype(df_clean["local_price"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(df_clean["price_usd"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(df_clean["price_usd_ex_vat"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(df_clean["unit_price_usd"]))

    def test_missing_values_preservation(self):
        """Ensures missing ratings or reviews are preserved as NaN and not falsely converted to 0."""
        df_clean, summary = clean_and_validate_products(self.df_raw, self.df_fx)
        missing_ratings = df_clean["product_rating"].isna().sum()
        self.assertEqual(missing_ratings, 1, "Exactly one missing rating must be preserved as null")
        self.assertIn("product_rating", summary["missing_fields"])
        self.assertEqual(summary["missing_fields"]["product_rating"]["missing_count"], 1)

    def test_fx_conversion_math(self):
        """Verifies that GBP prices are accurately converted to USD using documented FX rate (1.3050)."""
        df_clean, summary = clean_and_validate_products(self.df_raw, self.df_fx)
        rate = summary["gbp_usd_exchange_rate"]
        self.assertAlmostEqual(rate, 1.3050, places=4)

        uk_rows = df_clean[df_clean["target_market"] == "UK"]
        for _, row in uk_rows.iterrows():
            expected_usd = round(row["local_price"] * rate, 2)
            self.assertAlmostEqual(row["price_usd"], expected_usd, places=1)

    def test_vat_structural_adjustment(self):
        """Verifies that UK pre-tax price equals price_usd / 1.20 and US prices remain unmodified."""
        df_clean, _ = clean_and_validate_products(self.df_raw, self.df_fx)
        uk_row = df_clean[df_clean["target_market"] == "UK"].iloc[0]
        self.assertAlmostEqual(uk_row["price_usd_ex_vat"], round(uk_row["price_usd"] / 1.20, 2), places=1)

        us_row = df_clean[df_clean["target_market"] == "US"].iloc[0]
        self.assertEqual(us_row["price_usd_ex_vat"], us_row["price_usd"])

    def test_pack_quantity_and_unit_pricing(self):
        """Verifies pack quantities and derived unit pricing."""
        df_clean, _ = clean_and_validate_products(self.df_raw, self.df_fx)
        multi_packs = df_clean[df_clean["pack_quantity"] > 1]
        self.assertGreaterEqual(len(multi_packs), 10)
        for _, row in multi_packs.iterrows():
            expected_unit = round(row["price_usd"] / row["pack_quantity"], 2)
            self.assertAlmostEqual(row["unit_price_usd"], expected_unit, places=2)

    def test_duplicate_absence(self):
        """Verifies that there are zero duplicate product IDs in the verified catalog."""
        df_clean, summary = clean_and_validate_products(self.df_raw, self.df_fx)
        self.assertEqual(summary["duplicate_id_count"], 0)
        self.assertEqual(summary["semantic_duplicate_count"], 0)

    def test_validation_failure_on_invalid_price(self):
        """Asserts that records with non-positive local_price fail validation."""
        bad_df = self.df_raw.copy()
        bad_df.loc[0, "local_price"] = -5.00
        _, summary = clean_and_validate_products(bad_df, self.df_fx, strict_raise=False)
        self.assertFalse(summary["validation_passed"])
        self.assertTrue(any("non-positive" in err for err in summary["validation_errors"]))

        with self.assertRaises(ValueError):
            clean_and_validate_products(bad_df, self.df_fx, strict_raise=True)

    def test_validation_failure_on_invalid_market(self):
        """Asserts that records with unapproved target market codes fail validation."""
        bad_df = self.df_raw.copy()
        bad_df.loc[0, "target_market"] = "FR"
        _, summary = clean_and_validate_products(bad_df, self.df_fx, strict_raise=False)
        self.assertFalse(summary["validation_passed"])
        self.assertTrue(any("Invalid market code" in err for err in summary["validation_errors"]))

    def test_validation_failure_on_out_of_bounds_rating(self):
        """Asserts that rating outside [1.0, 5.0] fails validation."""
        bad_df = self.df_raw.copy()
        bad_df.loc[0, "product_rating"] = 5.8
        _, summary = clean_and_validate_products(bad_df, self.df_fx, strict_raise=False)
        self.assertFalse(summary["validation_passed"])
        self.assertTrue(any("product_rating outside [1.0, 5.0]" in err for err in summary["validation_errors"]))

    def test_validation_failure_on_invalid_pack_quantity(self):
        """Missing, fractional, or non-positive pack counts must not silently become one."""
        for invalid_pack in (0, -2, 1.5, None):
            with self.subTest(pack_quantity=invalid_pack):
                bad_df = self.df_raw.copy()
                bad_df["pack_quantity"] = bad_df["pack_quantity"].astype(float)
                bad_df.loc[0, "pack_quantity"] = invalid_pack
                _, summary = clean_and_validate_products(bad_df, self.df_fx)
                self.assertFalse(summary["validation_passed"])
                self.assertTrue(any("pack_quantity" in err for err in summary["validation_errors"]))

    def test_validation_failure_on_broken_match_key(self):
        """A match key must contain exactly one row from each market."""
        bad_df = self.df_raw.copy()
        bad_df.loc[0, "cross_market_match_id"] = "ORPHAN_MATCH"
        _, summary = clean_and_validate_products(bad_df, self.df_fx)
        self.assertFalse(summary["validation_passed"])
        self.assertTrue(any("invalid cross-market match" in err for err in summary["validation_errors"]))

        bad_exact_names = self.df_raw.copy()
        bad_exact_names.loc[1, "product_name"] = "Different model mislabeled as exact"
        _, name_summary = clean_and_validate_products(bad_exact_names, self.df_fx)
        self.assertFalse(name_summary["validation_passed"])
        self.assertTrue(any("exact-match product names differ" in err for err in name_summary["validation_errors"]))

        bad_exact_names = self.df_raw.copy()
        bad_exact_names.loc[1, "product_name"] = "Different model mislabeled as exact"
        _, name_summary = clean_and_validate_products(bad_exact_names, self.df_fx)
        self.assertFalse(name_summary["validation_passed"])
        self.assertTrue(any("exact-match product names differ" in err for err in name_summary["validation_errors"]))

    def test_missing_fx_rate_fails_strict_pipeline(self):
        """Required currency conversions must come from the FX file, without constants as fallback."""
        fx_without_gbp = self.df_fx[self.df_fx["base_currency"] != "GBP"].copy()
        with self.assertRaisesRegex(ValueError, "GBP"):
            clean_and_validate_products(self.df_raw, fx_without_gbp, strict_raise=True)

    def test_jpy_conversion_uses_documented_fx_rate(self):
        """JPY conversion must use the supplied rate table rather than a code constant."""
        products = self.df_raw.copy()
        products.loc[0, "currency"] = "JPY"
        products.loc[0, "local_price"] = 1000
        fx = self.df_fx.copy()
        fx.loc[fx["base_currency"] == "JPY", "rate"] = 0.01
        cleaned, _ = clean_and_validate_products(products, fx, strict_raise=True)
        self.assertEqual(cleaned.loc[0, "price_usd"], 10.0)


if __name__ == "__main__":
    unittest.main()

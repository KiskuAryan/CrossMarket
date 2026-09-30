"""
tests/test_analysis.py: Rigorous Unit Tests Reconciling All Published Analytical Figures, Parity Math, and Hypotheses
"""

import unittest
from pathlib import Path
import pandas as pd
import sys

# Ensure src is importable
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
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


class TestAnalysis(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        data_dir = Path(__file__).resolve().parent.parent / "data"
        cls.df_clean, cls.summary = run_pipeline(data_dir)
        cls.parity38 = get_cross_market_parity(cls.df_clean, match_mode="all")
        cls.parity36 = get_cross_market_parity(cls.df_clean, match_mode="exact_only")
        cls.kpis = get_executive_kpis(cls.df_clean, cls.parity38)

    def test_executive_kpis_reconciliation(self):
        """Asserts that computed headline KPIs exactly reconcile with published figures."""
        self.assertEqual(self.kpis["total_observations"], 76)
        self.assertEqual(self.kpis["us_observations"], 38)
        self.assertEqual(self.kpis["uk_observations"], 38)
        self.assertEqual(self.kpis["unique_brands"], 14)
        self.assertEqual(self.kpis["unique_products"], 40)
        self.assertEqual(self.kpis["unique_categories"], 5)
        self.assertEqual(self.kpis["unique_retailers"], 6)

        # Exact medians
        self.assertEqual(self.kpis["overall_median_usd"], 13.10)
        self.assertEqual(self.kpis["us_median_usd"], 9.12)
        self.assertEqual(self.kpis["uk_median_usd"], 14.84)
        self.assertEqual(self.kpis["uk_median_usd_ex_vat"], 12.37)

        # Ratings and reviews
        self.assertEqual(self.kpis["average_rating"], 4.75)
        self.assertEqual(self.kpis["rated_products_count"], 75)
        self.assertEqual(self.kpis["total_reviews"], 335669)

        # Matched pairs count
        self.assertEqual(self.kpis["matched_pairs_total"], 38)
        self.assertEqual(self.kpis["matched_pairs_exact_sku"], 36)
        self.assertEqual(self.kpis["matched_pairs_variant"], 2)

    def test_cross_market_parity_reconciliation(self):
        """Asserts that published overall parity figures reconcile exactly with computed math."""
        # 1. All 38 matched pairs
        self.assertEqual(len(self.parity38), 38)
        self.assertEqual(self.kpis["mean_nominal_premium_pct"], 38.9)
        self.assertEqual(self.kpis["median_nominal_premium_pct"], 38.9)
        self.assertEqual(self.kpis["mean_vat_adj_premium_pct"], 15.8)
        self.assertEqual(self.kpis["median_vat_adj_premium_pct"], 15.8)

        # 2. Exact SKU & Pack matches only (36 pairs)
        self.assertEqual(len(self.parity36), 36)
        mean_36_nom = round(float(self.parity36["nominal_premium_pct"].mean()), 1)
        med_36_nom = round(float(self.parity36["nominal_premium_pct"].median()), 1)
        mean_36_vat = round(float(self.parity36["vat_adj_premium_pct"].mean()), 1)
        med_36_vat = round(float(self.parity36["vat_adj_premium_pct"].median()), 1)

        self.assertEqual(mean_36_nom, 39.5)
        self.assertEqual(med_36_nom, 38.9)
        self.assertEqual(mean_36_vat, 16.3)
        self.assertEqual(med_36_vat, 15.8)

    def test_parity_matching_integrity(self):
        """Asserts that every matched pair enforces brand and pack configuration equality."""
        for _, row in self.parity38.iterrows():
            self.assertIn(row["match_quality"], ["Exact SKU & Pack Match", "Closely Matched Regional Variant"])
            self.assertGreater(row["us_price_usd"], 0)
            self.assertGreater(row["uk_price_usd"], 0)
            self.assertGreater(row["pack_quantity"], 0)
            # Mathematical consistency: nominal diff must exceed VAT-adjusted diff
            self.assertGreater(row["nominal_diff_usd"], row["vat_adj_diff_usd"])

    def test_category_parity_reconciliation(self):
        """Asserts that category parity calculations reconcile with report tables."""
        cat_map = self.parity38.groupby("category").agg(
            nom_mean=("nominal_premium_pct", lambda s: round(s.mean(), 1)),
            vat_mean=("vat_adj_premium_pct", lambda s: round(s.mean(), 1)),
            count=("nominal_premium_pct", "count")
        ).to_dict("index")

        # Desk accessories (3 pairs)
        self.assertEqual(cat_map["Desk Accessories"]["count"], 3)
        self.assertEqual(cat_map["Desk Accessories"]["nom_mean"], 47.4)
        self.assertEqual(cat_map["Desk Accessories"]["vat_mean"], 22.8)

        # Highlighters & Markers (2 pairs)
        self.assertEqual(cat_map["Highlighters & Markers"]["count"], 2)
        self.assertEqual(cat_map["Highlighters & Markers"]["nom_mean"], 106.4)
        self.assertEqual(cat_map["Highlighters & Markers"]["vat_mean"], 72.0)
        full_hypothesis = identify_price_segments_and_hypotheses(self.df_clean, self.parity38)["hypotheses"][0]
        self.assertIn("+106.4% nominal / +72.0% VAT-adjusted", full_hypothesis["observation"])

        # Notebooks & Pads (12 pairs)
        self.assertEqual(cat_map["Notebooks & Pads"]["count"], 12)
        self.assertEqual(cat_map["Notebooks & Pads"]["nom_mean"], 32.4)
        self.assertEqual(cat_map["Notebooks & Pads"]["vat_mean"], 10.3)

        # Pens & Writing (16 pairs)
        self.assertEqual(cat_map["Pens & Writing"]["count"], 16)
        self.assertEqual(cat_map["Pens & Writing"]["nom_mean"], 39.3)
        self.assertEqual(cat_map["Pens & Writing"]["vat_mean"], 16.1)

        # Planners & Diaries (5 pairs)
        self.assertEqual(cat_map["Planners & Diaries"]["count"], 5)
        self.assertEqual(cat_map["Planners & Diaries"]["nom_mean"], 21.4)
        self.assertEqual(cat_map["Planners & Diaries"]["vat_mean"], 1.1)

    def test_brand_positioning_reconciliation(self):
        """Verifies brand positioning tier categorization and metrics reconciliation."""
        pos = get_brand_positioning_summary(self.df_clean)
        self.assertEqual(len(pos), 14)

        # Check Hobonichi luxury positioning
        hobo = pos[pos["brand"] == "Hobonichi"].iloc[0]
        self.assertEqual(hobo["positioning_tier"], "Luxury / Specialist Heritage")
        self.assertEqual(hobo["median_price_usd"], 35.31)
        self.assertEqual(hobo["average_rating"], 4.86)

        # Check Uni mass utility positioning
        uni = pos[pos["brand"] == "Uni (Mitsubishi Pencil)"].iloc[0]
        self.assertEqual(uni["positioning_tier"], "Mass Utility & Value")
        self.assertEqual(uni["median_price_usd"], 5.69)
        self.assertEqual(uni["average_rating"], 4.71)

        # All brands have positive median price and rating >= 4.4
        self.assertTrue(all(pos["median_price_usd"] > 0))
        self.assertTrue(all(pos["average_rating"] >= 4.4))

    def test_hypotheses_integrity_and_caveats(self):
        """Verifies that all hypotheses contain testable actions and limitation notes."""
        result = identify_price_segments_and_hypotheses(self.df_clean, self.parity38)
        hypotheses = result["hypotheses"]
        self.assertEqual(len(hypotheses), 4)

        for h in hypotheses:
            self.assertIn("title", h)
            self.assertIn("observation", h)
            self.assertIn("hypothesis", h)
            self.assertIn("evidence", h)
            self.assertIn("testable_action", h)
            self.assertIn("limitation_note", h)
            self.assertTrue(len(h["limitation_note"]) > 20, "Limitation note must be substantive")

    def test_hypothesis_metrics_follow_active_selection(self):
        """Filtered hypothesis text uses only selected listings and never falls back to full-sample values."""
        pens = self.df_clean[self.df_clean["product_category"] == "Pens & Writing"]
        pens_parity = get_cross_market_parity(pens)
        result = identify_price_segments_and_hypotheses(pens, pens_parity)
        hypotheses = {item["id"]: item for item in result["hypotheses"]}

        self.assertIn("not available in this selection", hypotheses["HYP-01"]["observation"])
        self.assertNotIn("48k+", hypotheses["HYP-02"]["observation"])
        japanese = pens[pens["brand_origin"] == "Japanese Heritage"]
        expected_japanese_rating = round(japanese["product_rating"].dropna().mean(), 2)
        self.assertIn(f"Japanese-brand listings average ★ {expected_japanese_rating}", hypotheses["HYP-03"]["observation"])
        self.assertIn("US 0/", hypotheses["HYP-04"]["evidence"])

        full_hypotheses = identify_price_segments_and_hypotheses(self.df_clean, self.parity38)["hypotheses"]
        full_japanese_rating_text = next(h["observation"] for h in full_hypotheses if h["id"] == "HYP-03")
        self.assertIn("across 65 rated listings and 202,459 logged listing reviews", full_japanese_rating_text)
        self.assertIn("95.4%", full_japanese_rating_text)

        western = self.df_clean[self.df_clean["brand_origin"] != "Japanese Heritage"]
        no_jp = identify_price_segments_and_hypotheses(western, get_cross_market_parity(western))
        japanese_hypothesis = next(item for item in no_jp["hypotheses"] if item["id"] == "HYP-03")
        self.assertIn("no rated listings", japanese_hypothesis["title"])
        self.assertIn("No Japanese-brand ratings", japanese_hypothesis["observation"])


if __name__ == "__main__":
    unittest.main()

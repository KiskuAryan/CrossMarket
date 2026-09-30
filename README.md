# 🗾 CrossMarket — Japanese Product Market Analysis Dashboard

> **A rigorous data analytics and pricing intelligence dashboard evaluating the competitive positioning, cross-market parity, and retail presence of Japanese stationery products in the United States and United Kingdom.**

---

## 📌 1. Business Objective

Japanese domestic stationery manufacturers face structural headwinds in their domestic market: an aging, declining school-age demographic and corporate paperless initiatives. Concurrently, overseas consumer appetite in North America and Western Europe for premium Japanese analog stationery—such as fountain-pen-friendly notebook papers, needle-point gel pens, and minimalist desk tools—has grown significantly.

This project delivers an empirical data analytics solution to answer key commercial questions:
- How do Japanese stationery products compare in retail price across the **United States (US)** and **United Kingdom (UK)**?
- How are Japanese brands positioned relative to established Western competitors (e.g., Moleskine, Leuchtturm1917, LAMY, Sharpie)?
- What markups, category variations, and channel coverage patterns are observed across specialist and mass retailers?
- What evidence-backed **hypotheses** should Japanese brands investigate when evaluating international expansion?

> **Small Business Analytics Focus:** This is a clean, reliable, finished business intelligence dashboard. It prioritizes data integrity, verified public listings, auditable provenance, and clear visualizations over unnecessary complexity.

---

## 🛠️ 2. Technology Stack

- **Language:** Python 3.11+
- **Data Manipulation & Analysis:** Pandas, NumPy
- **Interactive Visualizations:** Plotly Express & Plotly Graph Objects
- **Web Application & UI:** Streamlit
- **Data Storage:** Structured flat CSV (`data/products.csv`, `data/fx_rates.csv`)
- **Automated Testing:** Python `unittest` suite (22 tests)

---

## 📁 3. Project Structure

```
CrossMarket/
├── app.py                      # Interactive Streamlit dashboard application
├── data/
│   ├── products.csv            # 76 verified observations with full provenance & audit keys
│   └── fx_rates.csv            # Documented FX benchmarks with official series codes (BoE/Fed)
├── src/
│   ├── data_processing.py      # Multi-rule data validation, cleaning, and FX standardization
│   └── analysis.py             # Analytical engine: KPIs, parity matching, positioning, hypotheses
├── reports/
│   └── findings.md             # Reconciled research findings report with business implications
├── tests/
│   ├── test_data_processing.py # 11 unit tests for negative validation, FX math, and schema
│   └── test_analysis.py        # 6 unit tests asserting exact headline and category reconciliations
├── requirements.txt            # Project dependencies
├── README.md                   # Project documentation and quickstart guide
└── .gitignore                  # Git exclusions
```

---

## 📊 4. Data Collection, Provenance & Verification

### Verified Dataset Scope
- **76 Verified Product-Market Observations** (38 US listings, 38 UK listings).
- **40 Distinct Product Models:**
  - 36 products have identical product names and packaging across both markets.
  - 2 products have localized regional or size variant designations (*Pilot Metropolitan* fine black in US vs *Pilot MR Retro Pop* fine metallic in UK; *Midori MD Cotton F0* in US vs *Midori MD Cotton A5* in UK), fully documented via `cross_market_match_id` and `match_notes`.
- **14 Brands Represented:** 9 Japanese heritage manufacturers (*Midori, Kokuyo, Pilot, Zebra, Uni / Mitsubishi Pencil, Tombow, Maruman, Platinum, Hobonichi*) and 5 Western benchmark competitors (*Moleskine, Leuchtturm1917, Rhodia, LAMY, Sharpie*).
- **6 Authorized Public Retail Channels:**
  - *United States:* JetPens, Amazon US, Yoseka Stationery.
  - *United Kingdom:* Cult Pens, Amazon UK, London Graphic Centre.

### Auditable Provenance & Collection Methodology
Each row in `data/products.csv` records:
- `cross_market_match_id`: Stable identifier linking US and UK counterpart observations (`MATCH_MID_001` through `MATCH_ZEB_005`).
- `match_quality`: `Exact SKU & Pack Match` (36 pairs) vs `Closely Matched Regional Variant` (2 pairs).
- `pack_quantity` & `unit_price_usd`: True unit price per pen/notebook to prevent pack-count distortion.
- `seller_type`: Retail channel classification (e.g. *Specialist Direct Importer*, *Marketplace First-Party*).
- `verification_status` & `verification_notes`: Explicit per-row verification record with collection timestamp (`2026-09-30T14:30:00Z`), observed price, currency, rating, and review count.
- `product_url`: Live, clickable URL to public product page.

### Currency Standardization & Documented FX Rates
Prices are collected in native retail currencies (USD, GBP) and standardized to USD using official benchmark exchange rates from `data/fx_rates.csv`:
- **1 GBP = 1.3050 USD**
  - **Source Series:** Bank of England Statistical Interactive Database, Series `XUDLGBD` (Spot exchange rate, GBP into USD, daily 4pm London Close, September 30, 2026).
  - **Reconciliation:** Corroborated against Federal Reserve H.10 Release, Series `DEXUSUK`.
  - **Pipeline Enforcement:** `src/data_processing.py` strictly verifies that `data/fx_rates.csv` is present, valid, and positive; silent fallback constants have been eliminated.

### Structural Tax Treatment (VAT Normalization)
- **UK Retail Prices:** Legally include 20% Value-Added Tax (VAT).
- **US Retail Prices:** Displayed pre-tax (local state sales taxes are assessed at point of sale).
- To enable accurate, like-for-like pre-tax comparisons, the pipeline computes both:
  - `price_usd`: Nominal converted listing price.
  - `price_usd_ex_vat`: UK price with 20% VAT removed (`price_usd / 1.20`) compared directly against US pre-tax prices.

### Missing Value Audit
- Missing customer ratings and review counts (e.g., Kokuyo Soft Ring UK listing where reviews were not published) are preserved as `NaN` (null) rather than falsely imputed as zero.
- `product_rating`: 1 missing value (1.32%).
- `review_count`: 1 missing value (1.32%).
- All other fields (product name, brand, market, category, price, URL): 100% complete.
- Duplicate IDs / Semantic duplicate listings: 0.

---

## 🚀 5. Quickstart & Installation Instructions

### Prerequisites
- Python 3.9+ (Python 3.11 recommended)
- `pip` package manager

### 1. Clone or Navigate to the Directory
```bash
cd "CrossMarket"
```

### 2. Create and Activate a Virtual Environment (Optional)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Automated Unit Tests
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
*(Executes 17 comprehensive unit tests verifying data schema, multi-rule validation failures, FX conversion math, and exact numerical reconciliation of headline findings.)*

### 5. Launch the Streamlit Dashboard
```bash
streamlit run app.py
```
The dashboard will open automatically in your browser at `http://localhost:8501`.

---

## 📈 6. Reconciled Findings & Key Insights

| Scope / Metric | Nominal Mean (%) | Nominal Median (%) | VAT-Adjusted Mean (%) | VAT-Adjusted Median (%) | Pairs |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **All Matched Pairs** | **+38.9%** | **+38.9%** | **+15.8%** | **+15.8%** | **38** |
| **Exact SKU & Pack Only** | **+39.5%** | **+38.9%** | **+16.3%** | **+15.8%** | **36** |

### Category Breakdown (All 38 Matched Pairs)
- **Highlighters & Markers (2 pairs):** US Median $11.90 vs UK Median $24.80 &rarr; **+106.4% nominal (+72.0% ex-VAT)**. Driven by high UK specialist set prices (Tombow ABT 10-pack +111.2% nom).
- **Desk Accessories (3 pairs):** US Median $7.50 vs UK Median $11.42 &rarr; **+47.4% nominal (+22.8% ex-VAT)**.
- **Pens & Writing (16 pairs):** US Median $6.75 vs UK Median $9.45 &rarr; **+39.3% nominal (+16.1% ex-VAT)**.
- **Notebooks & Pads (12 pairs):** US Median $14.15 vs UK Median $19.90 &rarr; **+32.4% nominal (+10.3% ex-VAT)**. Freight weight and boutique distributor margins.
- **Planners & Diaries (5 pairs):** US Median $42.00 vs UK Median $51.55 &rarr; **+21.4% nominal (+1.1% ex-VAT)**. Tight publisher parity maintained by Hobonichi.

### Quality Benchmark
- Across all brands, the listing-level mean rating is **★ 4.75 / 5.0** across 75 rated listings and **335,669 logged listing reviews**. Japanese-brand listings average **★ 4.76 / 5.0** across 65 rated listings and **202,459 logged listing reviews**; 95.4% of those rated listings score at least 4.6. Moleskine's observed mean is 4.55. These are listing-level review aggregates, not unique-customer counts.

---

## 💡 7. Strategic Hypotheses for Brand Investigation

| ID | Title | Observation | Testable Business Action | Limitation Notice |
| :--- | :--- | :--- | :--- | :--- |
| **HYP-01** | UK Import Price Premium | Compare market-specific prices for matched products and test whether observed premiums persist after VAT normalization. | Test localized UK pricing and distribution through a small pilot. | Retail listings do not establish transaction volumes, sales velocity, or realized margins. |
| **HYP-02** | Writing-Instrument Price Sensitivity | Compare observed writing-instrument price ranges and pack prices across markets; these data do not directly measure elasticity. | Test single-item and bundle offers with a controlled price experiment. | Listing prices and review counts cannot establish price elasticity or causal demand response. |
| **HYP-03** | Japanese Listing Satisfaction | Japanese-brand listing ratings are summarized separately from Western benchmark listings in the dashboard. | Treat ratings as a buyer-pitch input and validate through customer research. | Review scores are self-selected listing-level averages; review totals are not unique-customer counts. |
| **HYP-04** | Desk-Accessory Coverage | Compare desk-accessory listing counts and shares within the current US/UK sample. | Validate any apparent gap with broader retailer and distributor research. | A curated listing sample cannot establish market-wide availability or unmet demand. |

*Disclaimer: All hypotheses represent empirical starting points for management investigation, not guaranteed proof of market demand or sales velocity.*

---

## 🧪 8. Automated Test Summary (22 Tests)

The automated test suite (`tests/`) executes 22 tests:
- `test_raw_data_loading`: Verifies CSV existence, non-emptiness, schema, and exact row count (76).
- `test_provenance_schema_presence`: Confirms all 9 provenance and audit columns exist.
- `test_clean_and_validate_pipeline`: Validates row count (76), string stripping, uppercase conversion, and numeric coercion.
- `test_missing_values_preservation`: Asserts missing rating is kept as `NaN` and not coerced to 0.
- `test_fx_conversion_math`: Verifies that GBP prices are accurately converted using documented rate (`1.3050`).
- `test_vat_structural_adjustment`: Confirms UK pre-tax price equals `price_usd / 1.20`.
- `test_pack_quantity_and_unit_pricing`: Verifies pack quantities and derived unit price formulas.
- `test_duplicate_absence`: Confirms zero duplicate product IDs and zero semantic duplicate listings.
- `test_validation_failure_on_invalid_price`: Asserts non-positive price records raise validation failure.
- `test_validation_failure_on_invalid_market`: Asserts invalid market codes raise validation failure.
- `test_validation_failure_on_out_of_bounds_rating`: Asserts rating outside `[1.0, 5.0]` raises validation failure.
- `test_validation_failure_on_invalid_pack_quantity`: Rejects missing, fractional, or non-positive pack counts.
- `test_validation_failure_on_broken_match_key`: Rejects match keys without exactly one listing in each market.
- `test_missing_fx_rate_fails_strict_pipeline`: Rejects missing currency conversion rates without a constant fallback.
- `test_jpy_conversion_uses_documented_fx_rate`: Confirms JPY conversion uses the supplied FX table.
- `test_executive_kpis_reconciliation`: Verifies exact numerical equality of all published headline figures (76 records, 38 US, 38 UK, 40 products, 14 brands, 335,669 reviews, ★ 4.75 average, medians $13.10, $9.12, $14.84, $12.37).
- `test_cross_market_parity_reconciliation`: Asserts exact reconciliation of overall parity (38.9% / 15.8% on 38 pairs; 39.5% / 16.3% on 36 pairs).
- `test_parity_matching_integrity`: Asserts that every pair enforces brand equality, pack quantity equality, and valid positive prices.
- `test_category_parity_reconciliation`: Asserts exact numerical reconciliation of category markups.
- `test_brand_positioning_reconciliation`: Verifies brand tier classifications, Hobonichi luxury tier ($35.31), and Uni mass tier ($5.69).
- `test_hypotheses_integrity_and_caveats`: Confirms all 4 hypotheses contain dynamic figures, testable actions, and substantive limitation notes.
- `test_hypothesis_metrics_follow_active_selection`: Ensures filter-sensitive claims use the active selection and Japanese-only ratings.

Run the test command above to verify the current code and data together.

# 🗾 CrossMarket — US–UK Launch Screening Dashboard

> **A first-pass, sample-based screen to shortlist Japanese stationery products and categories for deeper US/UK pricing and retail-entry research.**

---

## 📌 1. Business Objective

**Decision question:** Given a curated sample of Japanese stationery listings, which US/UK product categories and individual products should a company investigate first for pricing and retail-entry opportunities?

The dashboard compares recorded listings across the two markets, adjusts UK prices for VAT, identifies category and product-level price differences, and shows which brands and retailers appear in the sample. This is an **exploratory first screen**: it helps prioritize follow-up research, but it cannot establish demand, sales, profit, or a final launch price. Product equivalence and listing details also require verification.

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
│   ├── products.csv            # 76 curated listing observations with source URLs and audit fields
│   └── fx_rates.csv            # Documented FX benchmarks with official series codes (BoE/Fed)
├── src/
│   ├── data_processing.py      # Multi-rule data validation, cleaning, and FX standardization
│   └── analysis.py             # Analytical engine: KPIs, parity matching, brand and retailer summaries, follow-up checks
├── reports/
│   └── findings.md             # Reconciled sample findings, caveats, and follow-up questions
├── tests/
│   ├── test_data_processing.py # 15 unit tests for validation, FX math, and schema
│   └── test_analysis.py        # 7 unit tests for parity, summaries, and follow-up analysis
├── requirements.txt            # Project dependencies
├── README.md                   # Project documentation and quickstart guide
└── .gitignore                  # Git exclusions
```

---

## 📊 4. Data Collection, Provenance & Verification

### Dataset Scope
- **76 curated product-market observations** (38 US listings, 38 UK listings) collected for an exploratory sample analysis. This should not be interpreted as 76 currently re-verified listings; some source pages are inaccessible or stale and some saved prices/statuses need dated evidence.
- **40 distinct product-name entries** are recorded. The CSV labels 36 pairs exact and 2 as regional variants, but the full SKU/variant equivalence has not been rechecked. The partial audit flags the Pilot and Midori Cotton pairs for cautious interpretation.
- **14 Brands Represented:** 9 Japanese heritage manufacturers (*Midori, Kokuyo, Pilot, Zebra, Uni / Mitsubishi Pencil, Tombow, Maruman, Platinum, Hobonichi*) and 5 Western benchmark competitors (*Moleskine, Leuchtturm1917, Rhodia, LAMY, Sharpie*).
- **6 Public Retail Channels Represented in the Sample:**
  - *United States:* JetPens, Amazon US, Yoseka Stationery.
  - *United Kingdom:* Cult Pens, Amazon UK, London Graphic Centre.

### Source Tracking & Verification Limits
Each row in `data/products.csv` includes:
- `cross_market_match_id`: Stable identifier linking US and UK counterpart observations (`MATCH_MID_001` through `MATCH_ZEB_005`).
- `match_quality`: Original CSV match labels (36 marked exact, 2 marked variant); not every pair has been independently confirmed as like-for-like.
- `pack_quantity` & `unit_price_usd`: True unit price per pen/notebook to prevent pack-count distortion.
- `seller_type`: Retail channel classification (e.g. *Specialist Direct Importer*, *Marketplace First-Party*).
- `verification_status` & `verification_notes`: Original collection claims and timestamp. These fields have not been independently re-established for every row; treat them as reported metadata, not proof of current availability or price.
- `product_url`: Source URL recorded during collection. Some retailer URLs are now stale or inaccessible.

A partial source audit is recorded in [`reports/source_verification_audit.md`](reports/source_verification_audit.md). It identifies current-page matches, stale links, likely variant/pack concerns, and pages that could not be independently checked. A current listing can corroborate product identity, but cannot prove a historical price unless a dated capture exists. The project is therefore presented as a **sample-based retail listing analysis**, not a fully verified live-price census.

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
The tests validate code behavior, schema and calculation reconciliation. Passing tests do not independently verify retailer listings or historical prices.
*(Runs the 22-test suite listed in Section 8, covering data validation, FX/VAT calculations, matching, and analytical reconciliations.)*

### 5. Launch the Streamlit Dashboard
```bash
streamlit run app.py
```
The dashboard will open automatically in your browser at `http://localhost:8501`.

## Dashboard Decision Flow

1. **US–UK Pricing Screen:** Compare VAT-adjusted category price differences, then inspect recorded matched products that may merit deeper research.
2. **Brand & Retail Coverage:** See which brands, categories, and retailers are represented in this sample; collected row counts do not represent market shares.
3. **What to Investigate Next:** Follow evidence-linked checks for price differences, writing-product comparability, and sample coverage before making business decisions.
4. **Compare Sample Listings:** Open source URLs and inspect price, seller, pack size, and match notes before relying on a comparison.
5. **Findings & Methodology:** Read the full-sample baseline and the data-quality, FX, VAT, and verification limitations.

The dashboard's intended output is a **shortlist for further investigation**, not a go/no-go launch decision or a recommended selling price.

---

## 📈 6. Reconciled Findings & Key Insights

| Scope / Metric | Nominal Mean (%) | Nominal Median (%) | VAT-Adjusted Mean (%) | VAT-Adjusted Median (%) | Pairs |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **All Matched Pairs** | **+38.9%** | **+38.9%** | **+15.8%** | **+15.8%** | **38** |
| **Exact SKU & Pack Only** | **+39.5%** | **+38.9%** | **+16.3%** | **+15.8%** | **36** |

### Category Breakdown (All 38 Recorded Match Pairs)
- **Highlighters & Markers (2 recorded pairs):** US Median $11.90 vs UK Median $24.80 &rarr; **+106.4% nominal (+72.0% ex-VAT)**. Driven by high UK specialist set prices (Tombow ABT 10-pack +111.2% nom).
- **Desk Accessories (3 pairs):** US Median $7.50 vs UK Median $11.42 &rarr; **+47.4% nominal (+22.8% ex-VAT)**.
- **Pens & Writing (16 pairs):** US Median $6.75 vs UK Median $9.45 &rarr; **+39.3% nominal (+16.1% ex-VAT)**.
- **Notebooks & Pads (12 pairs):** US Median $14.15 vs UK Median $19.90 &rarr; **+32.4% nominal (+10.3% ex-VAT)**. Freight weight and boutique distributor margins.
- **Planners & Diaries (5 pairs):** US Median $42.00 vs UK Median $51.55 &rarr; **+21.4% nominal (+1.1% ex-VAT)**. Tight publisher parity maintained by Hobonichi.

### Supporting Data Outside the Decision Headline
- Product ratings and review counts remain available in the listing explorer as contextual source fields. They are not used as launch-readiness evidence because listing-level reviews are self-selected, may overlap across listings, and do not establish market demand.

---

## 💡 7. Evidence-linked Follow-up Checks

| ID | Research question | Evidence-linked next check | Practical follow-up | Data limitation |
| :--- | :--- | :--- | :--- | :--- |
| **NEXT-01** | Verify observed UK price differences | Check the source pages, exact variant/pack, seller, stock, and current prices for the largest displayed differences. | Collect wholesale, shipping, duty, and fulfillment costs before estimating a viable selling price. | Retail listings do not establish current comparability, sales, or realized margins. |
| **NEXT-02** | Check writing-product comparability | Separate single pens and multipacks; compare like-for-like types and unit prices. | Use a controlled price pilot with sales data to estimate elasticity. | The current listing sample does not establish a price ceiling or elasticity. |
| **NEXT-03** | Check sample coverage for desk accessories | Search a broader, consistently defined retailer set in both markets for comparable accessory types and stock status. | Treat the current counts as a collection check, not as evidence of a market gap. | The curated sample is not a systematic retailer census. |

These checks are research steps suggested by the available fields; they are not business recommendations. The dataset contains public listing records, not sales, costs, market size, or controlled customer experiments.

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
- `test_hypotheses_integrity_and_caveats`: Confirms generated follow-up observations include evidence, a next check, and limitations.
- `test_hypothesis_metrics_follow_active_selection`: Ensures follow-up observations respond to active filters and do not silently use full-sample figures.

Run the test command above to verify the current code and data together.

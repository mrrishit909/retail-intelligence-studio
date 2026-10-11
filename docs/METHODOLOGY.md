# Methodology

All numbers below are produced by `uv run python -m pipelines.run_all` (about one minute after the first download) and are
reproducible: fixed seed 20261011, no wall clock in analytics. Figures quoted are from the committed artifacts in `site/public/data/`.

## 1. Star schema (dbt-duckdb)
`dbt-duckdb` installs cleanly on Python 3.12 (dbt-duckdb 1.11.0, DuckDB 1.5.6), so the layer is a real dbt project in `dbt/`:
`stg_raw` (the 1,067,371 workbook rows), `stg_lines` (classification and exclusions), `dim_product`, `dim_customer` (anonymised key only),
`dim_date`, `dim_country`, `fact_lines`, `fact_refund_match`, plus the seed `product_family_rules.csv`. Python runs between two dbt stages
(LIFO refund matching writes `main.refund_matches`, which `fact_refund_match` reads). `dbt test` runs 20 generic tests (unique, not null,
relationships, accepted values) and 2 singular tests (revenue reconciles to line items; row ledger closes).

## 2. Cleaning and reconciliation
| Step | Rows | GBP |
|---|---|---|
| Raw (both sheets) | 1,067,371 | 19,287,250.57 |
| Excluded: overlap duplicates (sheet 1 rows dated 2010-12-01 or later; identical copies in sheet 2) | 22,523 | 377,488.45 |
| Excluded: exact duplicates (all eight columns equal to an earlier row) | 11,812 | 54,228.42 |
| **Kept in fact_lines** | **1,033,036** | **18,855,533.70** |

Kept lines by class: sale 1,003,294 lines (GBP 19,643,299.89); refund 17,914 (GBP -716,425.97); nonproduct 5,873 (GBP -71,340.22);
stock_adjustment 5,955 (GBP 0, quantity -320,673 net). Guest (no Customer ID): 22.8% of lines, 13.6% of GBP; kept for revenue and baskets, excluded from RFM, cohorts, CLV.
Nine identities (rows, GBP, classes, months, customer+guest, refund quantity, sheet counts, overlap) are recomputed in `reconciliation.json` and tests.

## 3. Refunds
`C` invoices are refunds (17,914 lines on 7,405 credit notes, GBP 716,426 or 3.65% of sale value). Each line is allocated LIFO to earlier sale lines of the
same customer and SKU with unrefunded quantity. 89.3% of lines are at least partly matched, 96.3% of refunded units are matched; 328 lines have no
Customer ID and 1,711 lines have unmatched residual quantity (no earlier sale in the ledger, which starts in December 2009, or over-refund).
Refunds reduce monetary value, never count as purchases.

## 4. RFM
Snapshot 2011-12-10. Recency in days; frequency = distinct sale invoices; monetary = sale minus credit-note GBP. Recency and monetary use quintile edges (numpy.quantile
at 0.2 to 0.8; recency edges 20, 59, 187, 409 days); frequency uses fixed bins 1, 2, 3-4, 5-8, 9+ because quantiles tie. Nine segments by first-matching rule (Champions, Loyal, At risk, New customers,
Potential loyalists, Promising, Need attention, About to sleep, Lost). 5,852 customers: Champions are 21.3% of customers and 68.6% of net GBP; the top decile of customers holds 63.2% of GBP.

## 5. Cohorts
Cohort = month of first sale invoice. 24 cohorts (2009-12 to 2011-11). Median month-1 retention 20.8%, median month-12 retention 17.3%; month-3 retention ranges 9.2% to 42.5%.
The 2009-12 cohort contains pre-existing customers (left-censoring). Cells beyond 2011-11 are null.

## 6. Baskets
39,516 invoices with a sale line, SKU as item, minimum support 0.5% (198 baskets), minimum confidence 0.4, lift > 1, itemsets up to 3 (own Apriori with sparse matrix counting).
1,451 frequent items, 4,458 rules (1,433 cross-family). The top lift (150) is herb markers: variants of one product. The featured list shows non-variant rules first
and flags variants. The top 15 rules are recounted from raw baskets in validation.

## 7. CLV (BG/NBD + Gamma-Gamma, PREDICTED)
Own implementation (the `lifetimes` package is unmaintained); correctness shown by simulation (parameter recovery and conditional expectation vs simulated futures).
Transaction = customer purchase day. Calibration 2009-12-01 to 2011-06-09 (4,944 customers), holdout 2011-06-10 to 2011-12-09 (26.1 weeks).
BG/NBD r=0.683, alpha=9.48, a=0.152, b=3.31. Holdout: predicted 7,645 purchase days vs actual 7,753 (-1.4%); per-customer correlation 0.85, MAE 1.05 vs 1.86 for the population-rate baseline
(1.09 for each customer's own rate); decile mean absolute error 9.0%. Gamma-Gamma assumes monetary independent of frequency (observed correlation 0.08). Final fit on all data predicts 52-week
discounted revenue (10%/yr, assumption): total GBP 8.57m, median GBP 570, top decile 57.6% of the total.

## 8. Forecasting (PREDICTED)
Weekly units for 13 product families and 60 active SKUs; 104 complete Monday weeks. Rolling origin with expanding window from week 60: 44 origins, horizons 1 to 8.
Models: seasonal-naive (lag 52, baseline), mean of last 4 weeks, damped-trend ETS, seasonal ratio, ensemble. Result: seasonal-naive is the weakest; the 4-week mean has MAE skill
35.1% at horizon 1 (WAPE 29.3% vs 45.2%), 17.5% at horizon 8; it beats seasonal-naive on 57 of 60 SKUs and 12 of 13 families. The ensemble has the best horizon-8 skill (26.2%).
Intervals are the 10th and 90th percentiles of backtest errors; out-of-sample one-step coverage is 71.7% against a nominal 80% (under-covers; published).

## 9. Newsvendor (SIMULATED)
Critical fractile (p - c) / (p - s) with assumed cost 0.60 of price and salvage 0.20 of cost gives 0.4545. Normal and empirical demand variants; 18 items; 49 parity vectors
(`newsvendor_vectors.json`, relative tolerance 1e-6). A replay on real weekly demand over the last 26 origins finds the newsvendor order within 0.01% of ordering the forecast mean
(the fractile is near 0.5, so the policies nearly coincide); it is a what-if on assumed costs, not evidence of savings.

## 10. Price elasticity (declined)
Stage 1 passes (1,311 of 2,753 SKUs with 26+ selling weeks qualify), but Stage 2 fails: 53.8% of log-price variance is inside a single SKU-week and the median within-week Spearman
correlation of quantity and price is -0.61 (quantity-discount tiers). No elasticity is estimated; the evidence table and the missing data are published. Stage 2 was written after seeing that
Stage 1 passed on counts (disclosed in `DATA_CONTRACTS.md`).

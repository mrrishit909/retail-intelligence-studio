# Architecture (data layer)

```
UCI zip (gitignored) -> pipelines/ingestion/fetch.py   (sha256 manifest)
  -> extract.py  (xlsx -> data/interim/raw_lines.parquet, sheet names and row counts asserted)
  -> dbt seed + run  (data/processed/retail.duckdb: stg_raw, stg_lines, dims, fact_lines)
  -> pipelines/cleaning/refunds.py  (LIFO matching -> main.refund_matches)
  -> dbt run fact_refund_match + dbt test
  -> pipelines/cleaning/ledger.py  (data/manifests/cleaning_ledger.json)
  -> analytics/*  (rfm, cohorts, baskets, clv, forecasting, newsvendor, elasticity)
  -> pipelines/publish.py + validation.py  -> site/public/data/*.json  (17 artifacts)
  -> pipelines/validate_artifacts.py  (JSON Schema, 400 KB gzip budget)
```
- `pipelines/contracts.py` is the single source of the schemas in `data/contracts/`; `tests/test_contracts.py` fails if they drift.
- `data/raw`, `data/interim`, `data/processed` are gitignored; manifests, contracts and artifacts are committed.
- No backend. The site reads JSON only. Browser compute (newsvendor) must match `analytics/newsvendor.py` using `newsvendor_vectors.json`.
- Layout: `pipelines/` (ingestion, cleaning, publish), `analytics/` (pure modules), `dbt/` (star schema), `tests/` (pytest), `docs/`.

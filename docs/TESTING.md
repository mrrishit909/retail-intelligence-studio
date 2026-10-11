# Testing

`uv run pytest -q` (45 tests, about 3 s after the pipeline has run; `-m "not slow"` skips tests that need built data).
| File | Covers |
|---|---|
| `tests/test_contracts.py` | schemas valid and equal to the generator, artifacts validate, 400 KB gzip budget, no U+2014/U+2015, no source customer IDs or customer_id fields |
| `tests/test_quality.py` | primary keys, referential integrity, line-class rules, ranges, no remaining duplicates, overlap copies identical, family coverage |
| `tests/test_reconciliation.py` | sheet counts, raw = kept + excluded (rows and GBP) recomputed from the raw parquet without dbt, published revenue = sum of line items, refund quantity closure and no over-refund, guest exclusion |
| `tests/test_models.py` | BG/NBD parameter recovery and prediction by simulation, formula monotonicity, Gamma-Gamma recovery, CLV calibration artifact, RFM and cohort invariants, forecast leakage test (future values do not change forecasts), seasonal-naive lag, backtest artifact, newsvendor optimality and vector parity, elasticity decision consistency |
`dbt test`: 20 generic and 2 singular tests, run by `run_all`. `validation.json` holds 47 runtime checks, all passing in the committed build.

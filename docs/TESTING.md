# Testing

`uv run pytest -q` (45 tests, about 3 s after the pipeline has run; `-m "not slow"` skips tests that need built data).
| File | Covers |
|---|---|
| `tests/test_contracts.py` | schemas valid and equal to the generator, artifacts validate, 400 KB gzip budget, no U+2014/U+2015, no source customer IDs or customer_id fields |
| `tests/test_quality.py` | primary keys, referential integrity, line-class rules, ranges, no remaining duplicates, overlap copies identical, family coverage |
| `tests/test_reconciliation.py` | sheet counts, raw = kept + excluded (rows and GBP) recomputed from the raw parquet without dbt, published revenue = sum of line items, refund quantity closure and no over-refund, guest exclusion |
| `tests/test_models.py` | BG/NBD parameter recovery and prediction by simulation, formula monotonicity, Gamma-Gamma recovery, CLV calibration artifact, RFM and cohort invariants, forecast leakage test (future values do not change forecasts), seasonal-naive lag, backtest artifact, newsvendor optimality and vector parity, elasticity decision consistency |
`dbt test`: 20 generic and 2 singular tests, run by `run_all`. `validation.json` holds 47 runtime checks, all passing in the committed build.


## Site (P09 frontend)
`cd site`: `npm run typecheck`, `npm run lint`, `npm test`, `npm run build`, `node tests/serve.mjs` (port 4391), `npx playwright test --workers 1`.

| Suite | What it proves |
|---|---|
| `src/model/model.test.ts` | lens area limits; the solved distance reproduces the target overlap to 1e-9 relative; the design fixture (4,013 / 2,245 / 1,428, k = 243.75, r 558 and 417.4, d 411.2); disjoint, contained and identical states; hero chance and lift follow `na * nb / baskets`; normal CDF and inverse to 1e-9; all 71 newsvendor vectors to 1e-6; the item whose normal fit puts more than 5% below zero is flagged |
| `e2e/qa.spec.ts` | the hero pair drawn is the exact pair of the published counts; areas drawn equal the numbers shown in every scene state (1e-5); S03a, S03b, S04, S05, S06 figures equal the artifacts; THE COUNTER (an unpublished pair is drawn apart, inspector, reset); zero external requests and console errors; route-blocked artifact RETRY; whole-document collision walk and text floor at 6 sizes; no sideways scroll; pixel contrast; axe in motion and reduced motion; reduced-motion flow |

# Retail Intelligence Studio

**The Hidden Patterns Behind Every Purchase.** Data engine for project 09 of The Data Frontier: 1,067,371 real invoice lines
(UCI Online Retail II, CC BY 4.0) turned into a dbt-duckdb star schema, RFM segments, cohort retention, association rules,
BG/NBD + Gamma-Gamma CLV, weekly forecasts with rolling-origin backtests, newsvendor scenarios, and an explicit decision not to estimate price elasticity.

Run: `uv sync && uv run python -m pipelines.run_all && uv run pytest -q`.
Output: 17 versioned JSON artifacts in `site/public/data/`, each validated against `data/contracts/*.schema.json`.

Headline results (all in `facts.json`): raw = kept + excluded to the penny (GBP 19.29m raw, 18.86m kept); refunds are 3.65% of sale value, 96% of refunded units matched;
CLV holdout error -1.4% in total (corr 0.85); best forecast beats seasonal-naive by 35% (MAE, one week ahead); elasticity not estimable.
Honesty tags: OBSERVED / DERIVED / PREDICTED / SIMULATED. No synthetic data, no demographics.

Docs: `docs/PROBLEM.md`, `DATA_SOURCES.md`, `DATA_CONTRACTS.md`, `METHODOLOGY.md`, `ARCHITECTURE.md`, `TESTING.md`, `LIMITATIONS.md`, `DEPLOYMENT.md`.
Data: Online Retail II, Daqing Chen (2012), UCI Machine Learning Repository, https://doi.org/10.24432/C5CG6D, CC BY 4.0. Derived aggregates, modified.

**Live site:** https://mrrishit909.github.io/retail-intelligence-studio/ (see `docs/DEPLOYMENT.md`).

## The site

One form carries every analysis: two discs of light whose areas are set sizes and whose overlap area is exactly what the sets share (an area-proportional Euler pair, solved by bisection on the circle-circle lens area). Bought together, cohort retention, RFM, the newsvendor order, the forecast and its backtest, and the CLV against its holdout are all the same picture. The only bright thing on a frame is what two sets have in common; where chance would put the partner is a 6% ghost, and the distance between ghost and real is lift.

```
cd site && npm ci && npm run typecheck && npm run lint && npm test   # 78 tests: Euler pair to 1e-9, 71 newsvendor vectors
npm run build && node tests/serve.mjs                               # production preview on :4391
npx playwright test --workers 1
```

Honest limits: one UK gift-ware wholesaler over 24 months, mostly trade buyers; no demographics; price elasticity is not estimable from this ledger (the site says so and shows why); the newsvendor costs are assumptions (SIMULATED).

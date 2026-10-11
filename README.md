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

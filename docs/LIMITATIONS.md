# Limitations

- One UK gift-ware wholesaler, 24 months, two Christmas seasons. Results do not generalise to retail at large. Many customers are trade buyers, not households.
- No demographics, costs, margins, stock levels or promotions. CLV is revenue, not profit. Newsvendor costs are assumptions (SIMULATED).
- The ledger records what shipped, not demand: stock-outs depress observed units and the forecasts inherit that.
- Duplicate removal drops 11,812 exact repeat rows (GBP 54,228); some may be genuine repeated scans. The 22,523 overlap rows are certain duplicates.
- Product families are keyword-derived (95.8% of sale revenue matched, 'Other' is the rest). Descriptions are not a taxonomy.
- Refund matching is LIFO within customer and SKU; 1,711 refund lines have residual quantity with no earlier sale (the ledger starts in 2009-12), so matching is incomplete by design.
- Cohorts: the first month mixes existing and new customers; later offsets are right-censored.
- Baskets: top-lift rules are mostly colour variants of one product; association is not causation.
- CLV: BG/NBD assumes constant purchase rates and ignores seasonality; one holdout window (26 weeks). Calibration is good in aggregate (-1.4%) but weaker in the lowest deciles (decile 1 predicted 0.23 vs actual 0.19; decile 4 0.60 vs 0.47).
- Forecast: only 104 weeks and 44 origins; seasonal-naive has a single prior year. Intervals under-cover (71.7% vs 80%). Horizon-8 skill for the best single model on families is 10%.
- Newsvendor replay: realised sales understate demand when stock was short; with the default costs the fractile is near 0.5, so the policy gain is ~0.
- Elasticity is not estimated (see METHODOLOGY section 10); the Stage-2 identification test was added after Stage 1 was computed.
- Timestamps are naive local time; GBP currency is inferred from the company's UK registration.

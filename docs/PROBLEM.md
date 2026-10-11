# Problem: Retail Intelligence Studio

**Tagline:** The Hidden Patterns Behind Every Purchase.

## The question
A small online gift-ware wholesaler records every invoice line it ships. What does that ledger say about
who buys, whether they come back, what is bought together, what will sell next, and what to stock?
The studio answers six questions from one real transaction ledger, each with its evidence and its limits.

| # | Question | Method | Honesty tag |
|---|---|---|---|
| 1 | Where does revenue come from, net of refunds and fees? | Star schema, explicit refund treatment, revenue reconciled to line items | OBSERVED |
| 2 | Who are the customers by recency, frequency and spend? | RFM with documented quintile bins and named segments | DERIVED |
| 3 | Do customers come back? | Cohort retention by first-purchase month | DERIVED |
| 4 | What is bought together? | Association rules (support, confidence, lift) with a stated minimum support | DERIVED |
| 5 | How many future purchases and how much value per customer? | BG/NBD + Gamma-Gamma, calibrated on a holdout period | PREDICTED |
| 6 | What will sell, and how much should be stocked? | Weekly forecasts with rolling-origin backtests against seasonal-naive; newsvendor scenarios | PREDICTED / SIMULATED |

A seventh question, price elasticity, is answered only if the data can support it. The decision rule is fixed in
`DATA_CONTRACTS.md` before the evidence is computed; the evidence table is published either way.

## Audience and use
A portfolio visitor (hiring manager, analyst, retail operator) should leave understanding the hidden structure of a
real transaction ledger, and should be able to see how every number was produced and how wrong it can be.

## Non-goals
- No demographics. The ledger has none; none are inferred or invented.
- No live inference. Every output is precomputed by `pipelines/run_all.py` and published as versioned JSON.
- No causal claims about promotions, price or marketing.
- No claim that this UK gift-ware wholesaler (2009 to 2011) represents retail in general.

## Success criteria (data layer)
1. `raw = kept + excluded` for rows and for GBP amount, with every exclusion reason counted.
2. Revenue in every artifact reconciles to fact line items (tests).
3. Every PREDICTED output ships its calibration or backtest, including when the model does not beat the baseline.
4. Every SIMULATED output ships its assumption table and Python reference vectors for the browser.
5. Every artifact validates against `data/contracts/*.schema.json` and is under about 400 KB gzip.

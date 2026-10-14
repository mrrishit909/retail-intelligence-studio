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


## Site (frontend)
`site/` is a Vite, React and TypeScript static site (Canvas 2D, Lenis, no worker). Everything is precomputed; the browser computes only the Euler-pair geometry, the newsvendor closed forms and RFM threshold sums, all in under a millisecond.

- `src/model/euler.ts`: lens area, bisection for the centre distance (1e-12), `pairFor` (disjoint, overlap, contained, identical states), chance and lift.
- `src/model/newsvendor.ts`: normal and empirical policies, accurate normal CDF (series and continued fraction) and its inverse; parity-tested against `newsvendor_vectors.json`.
- `src/graphics/commonGround.ts`: the renderer. Overlap luminance is a distance-to-boundary field made from two radial gradients composited with `darken` (never a point-centred glow); a PREDICTED partner has a blurred soft edge sized by its interval; unknown sizes are hatched, never lit.
- `src/app/pairView.ts`: the one store `{spec, camera, alpha, echoStart, inspected}`; `PairLayer.tsx` draws it with eased sizes (log space), re-solving the distance every frame so every drawn frame is an exact pair. `timeline.ts` is S00's pull and S08's echo as pure functions.
- `src/scenes`: S02 deck (with an in-card mini pair), S03a rules, S03b cohorts, S04 RFM, S05 newsvendor, S06 forecast and CLV, S07 argument stack, THE COUNTER with a pair inspector, S08.

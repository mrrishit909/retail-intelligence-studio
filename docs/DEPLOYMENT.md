# Deployment (data layer)

The data layer ships as static JSON committed in `site/public/data/` and copied into the Vite build. There is no server.
Refresh: `uv sync && uv run python -m pipelines.run_all` (downloads 43.5 MB on first run, rebuilds everything, validates against the schemas, fails if any artifact exceeds 400 KB gzip or any validation check fails).
Then `uv run pytest -q`. Site build, Pages workflow and the deploy script belong to the site phase and are documented there.
Attribution text for the footer is in `meta.json.source.attribution`.

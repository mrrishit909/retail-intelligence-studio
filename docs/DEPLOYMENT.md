# Deployment

Target: GitHub Pages, https://mrrishit909.github.io/retail-intelligence-studio/ (repo `mrrishit909/retail-intelligence-studio`, source `gh-pages` root). Base path `/retail-intelligence-studio/` is set in `site/vite.config.ts`.

1. Gate: `uv run pytest -q`; in `site/`: `npm run typecheck && npm run lint && npm test`, `npm run build`, `node tests/serve.mjs`, `npx playwright test --workers 1`, Lighthouse x3.
2. Publish: `scripts/deploy_site_pages.sh retail-intelligence-studio` builds, writes `site/dist` to `gh-pages` with `.nojekyll`, sets the Pages source.
3. Verify: `curl -I` the site and `data/facts.json`; the stylesheet content type is `text/css` before measuring; live smoke at 1440 and 390; Lighthouse x3 on the live URL.
4. Portfolio case study in `projects-site`, merged to main, every link checked.

CI (`.github/workflows/ci.yml`) runs the Python tests and the site typecheck, lint, unit tests and build and never deploys. Rollback: re-run the script from an earlier commit.

Results: see `docs/BUILD_STATUS.md`.

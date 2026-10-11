"""End to end: fetch -> extract -> dbt (staging, dims, facts) -> refund matching -> dbt (post, tests) -> ledger -> analytics -> artifacts -> schema validation.

Usage: uv run python -m pipelines.run_all [--skip-fetch]
"""
from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
import time

from pipelines import contracts, validate_artifacts, validation
from pipelines.cleaning import ledger, refunds
from pipelines.common import PUBLIC, ROOT, write_json
from pipelines.ingestion import extract, fetch


def dbt(*args):
    env = {**os.environ, "DBT_SEND_ANONYMOUS_USAGE_STATS": "False"}
    r = subprocess.run([sys.executable, "-m", "dbt.cli.main", *args, "--project-dir", "dbt", "--profiles-dir", "dbt"], cwd=ROOT, env=env, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-3000:], r.stderr[-2000:])
        raise SystemExit(f"dbt {' '.join(args)} failed")
    return r.stdout


def main():
    t0 = time.time()
    fetch.run()
    if not (ROOT / "data/interim/raw_lines.parquet").exists():
        extract.run()
    (ROOT / "data/processed").mkdir(parents=True, exist_ok=True)
    dbt("seed")
    dbt("run", "--exclude", "fact_refund_match")
    refunds.run()
    dbt("run", "--select", "fact_refund_match")
    dbt("test")
    ledger.run()
    contracts.run()
    from pipelines import publish
    out = publish.run()
    out["validation"] = validation.run(out)
    sizes = publish.write_all(out)
    for _ in range(2):  # meta carries the sizes of all artifacts (its own size is measured on the second pass)
        out["meta"]["artifact_bytes"] = {k: v for k, v in sizes.items()}
        sizes = publish.write_all(out)
    errs = validate_artifacts.run()
    big = {k: v for k, v in sizes.items() if v > 400_000}
    print(json.dumps(sizes, indent=1))
    print("schema errors:", errs or "none", "| over 400KB gz:", big or "none", "| validation failed:", out["validation"]["failed"], f"| {time.time() - t0:.0f}s")
    if errs or big or out["validation"]["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

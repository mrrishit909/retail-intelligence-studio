"""Shared paths, constants and the JSON writer for the Retail Intelligence Studio pipeline."""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"
MANIFESTS = ROOT / "data" / "manifests"
CONTRACTS = ROOT / "data" / "contracts"
PUBLIC = ROOT / "site" / "public" / "data"
LEDGER = MANIFESTS / "cleaning_ledger.json"
SCHEMA_VERSION = "v1"
PIPELINE_VERSION = "1.0.0"
SEED = 20261011

URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
ZIP_NAME = "online_retail_ii.zip"
XLSX_NAME = "online_retail_II.xlsx"
EXPECTED_SHEETS = ["Year 2009-2010", "Year 2010-2011"]
EXPECTED_TOTAL_ROWS = 1067371  # UCI metadata num_instances; verified against the file at extract time
DOI = "10.24432/C5CG6D"
ATTRIBUTION = ("Online Retail II, Daqing Chen (2012), UCI Machine Learning Repository, https://doi.org/10.24432/C5CG6D, "
               "licensed CC BY 4.0. Derived aggregates, modified; not the original file.")


def write_json(path: Path, obj, compact: bool = True) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    s = (json.dumps(obj, separators=(",", ":"), sort_keys=True, allow_nan=False) if compact
         else json.dumps(obj, indent=2, sort_keys=True, allow_nan=False))
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(s + "\n")
    os.replace(tmp, path)
    return len(s) + 1

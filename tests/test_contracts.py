"""Schemas are valid JSON Schema; artifacts validate; no em or en dashes anywhere tracked."""
import json
import subprocess

import pytest
from jsonschema import Draft202012Validator

from pipelines.common import CONTRACTS, PUBLIC, ROOT
from pipelines.validate_artifacts import run as validate_all


def test_schemas_valid_and_complete():
    files = sorted(CONTRACTS.glob("*.schema.json"))
    assert len(files) == 17
    for f in files:
        Draft202012Validator.check_schema(json.loads(f.read_text()))


def test_schemas_match_generator():
    from pipelines.contracts import SCHEMAS
    for name, sch in SCHEMAS.items():
        assert json.loads((CONTRACTS / f"{name}.schema.json").read_text()) == json.loads(json.dumps(sch, sort_keys=True))


@pytest.mark.slow
def test_artifacts_validate():
    assert validate_all() == []


@pytest.mark.slow
def test_artifact_size_budget():
    import gzip
    for f in PUBLIC.glob("*.json"):
        assert len(gzip.compress(f.read_bytes())) < 400_000, f.name


def _strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for k, v in o.items():
            yield from _strings(k)
            yield from _strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _strings(v)


@pytest.mark.slow
def test_no_dash_in_decoded_json_strings():
    for f in list(PUBLIC.glob("*.json")) + list((ROOT / "data").rglob("*.json")):
        if "raw" in f.parts or "interim" in f.parts or "processed" in f.parts:
            continue
        for s in _strings(json.loads(f.read_text())):
            assert chr(0x2014) not in s and chr(0x2015) not in s, f.name


def test_no_em_or_en_dash_in_tracked_files():
    files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    bad = []
    for f in files:
        p = ROOT / f
        if p.suffix in {".md", ".py", ".json", ".toml", ".ini", ".txt", ".yml", ".sql", ".csv"} and p.is_file():
            t = p.read_text(errors="ignore")
            if chr(0x2014) in t or chr(0x2015) in t:
                bad.append(f)
    assert bad == []


@pytest.mark.slow
def test_no_source_customer_ids_in_artifacts(db):
    """Published keys are a dense first-purchase order, not the source Customer ID; no artifact has a customer id field."""
    same = db.sql("select count(*) from dim_customer where customer_key = _src_id").fetchone()[0]
    assert same < 5
    for f in PUBLIC.glob("*.json"):
        assert '"customer_id"' not in f.read_text() and '"Customer ID"' not in f.read_text(), f.name

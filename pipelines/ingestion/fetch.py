"""Download the UCI Online Retail II zip into data/raw (gitignored), unpack, hash, write data/manifests/raw_manifest.json."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import zipfile

import requests

from pipelines.common import MANIFESTS, RAW, URL, XLSX_NAME, ZIP_NAME, write_json


def sha256(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def run() -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    zp, xp = RAW / ZIP_NAME, RAW / XLSX_NAME
    mf_path = MANIFESTS / "raw_manifest.json"
    if zp.exists() and mf_path.exists():
        return json.loads(mf_path.read_text())
    r = requests.get(URL, timeout=600, stream=True)
    r.raise_for_status()
    with open(zp, "wb") as f:
        for chunk in r.iter_content(1 << 20):
            f.write(chunk)
    with zipfile.ZipFile(zp) as z:
        z.extract(XLSX_NAME, RAW)
    mf = {"schema_version": "v1", "tags": {"files": "OBSERVED"}, "source": "UCI Online Retail II (id 502)", "url": URL,
          "licence": "CC BY 4.0", "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
          "http_status": r.status_code, "files": [
              {"name": ZIP_NAME, "bytes": zp.stat().st_size, "sha256": sha256(zp)},
              {"name": XLSX_NAME, "bytes": xp.stat().st_size, "sha256": sha256(xp)}]}
    write_json(mf_path, mf, compact=False)
    return mf


if __name__ == "__main__":
    print(run())

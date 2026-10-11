"""Read both xlsx sheets once, verify names and row counts, write data/interim/raw_lines.parquet (one row per source row)."""
from __future__ import annotations

import fastexcel
import polars as pl

from pipelines.common import EXPECTED_SHEETS, EXPECTED_TOTAL_ROWS, INTERIM, MANIFESTS, RAW, XLSX_NAME, write_json

COLS = {"Invoice": "invoice", "StockCode": "stock_code", "Description": "description", "Quantity": "quantity",
        "InvoiceDate": "invoice_ts", "Price": "price", "Customer ID": "customer_id", "Country": "country"}


def run() -> dict:
    INTERIM.mkdir(parents=True, exist_ok=True)
    rd = fastexcel.read_excel(str(RAW / XLSX_NAME))
    assert rd.sheet_names == EXPECTED_SHEETS, rd.sheet_names
    frames, sheets = [], []
    for s in rd.sheet_names:
        df = rd.load_sheet_by_name(s).to_polars()
        assert df.columns == list(COLS), df.columns
        df = df.rename(COLS).with_columns(
            pl.col("invoice").cast(pl.String), pl.col("stock_code").cast(pl.String),
            pl.col("quantity").cast(pl.Int64), pl.col("customer_id").cast(pl.Int64),
            pl.lit(s).alias("sheet"), pl.int_range(2, pl.len() + 2).alias("sheet_row"))  # sheet_row = Excel row number (header is row 1)
        sheets.append({"sheet": s, "rows": df.height, "first_ts": str(df["invoice_ts"].min()), "last_ts": str(df["invoice_ts"].max())})
        frames.append(df)
    all_ = pl.concat(frames).with_row_index("raw_id")
    assert all_.height == EXPECTED_TOTAL_ROWS, all_.height
    all_.write_parquet(INTERIM / "raw_lines.parquet", compression="zstd")
    out = {"schema_version": "v1", "tags": {"sheets": "OBSERVED"}, "sheet_names": rd.sheet_names, "sheets": sheets, "total_rows": all_.height}
    write_json(MANIFESTS / "extract_manifest.json", out, compact=False)
    return out


if __name__ == "__main__":
    print(run())

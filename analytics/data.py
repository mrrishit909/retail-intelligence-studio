"""Load star-schema tables as Polars frames (read-only DuckDB)."""
from __future__ import annotations

import duckdb
import polars as pl

from pipelines.common import PROCESSED


def con():
    return duckdb.connect(str(PROCESSED / "retail.duckdb"), read_only=True)


def sql(q: str) -> pl.DataFrame:
    c = con()
    try:
        return c.sql(q).pl()
    finally:
        c.close()


def sales(customers_only: bool = False) -> pl.DataFrame:
    w = "and f.customer_key is not null" if customers_only else ""
    return sql(f"""select f.raw_id, f.invoice_no, f.sku, f.customer_key, f.invoice_ts, cast(f.invoice_ts as date) as day, f.week_start, f.month,
                   f.quantity, f.unit_price, f.amount, p.family, p.description, d.in_complete_week
                   from fact_lines f join dim_product p using (product_key) join dim_date d using (date_key)
                   where f.line_class='sale' {w}""")


def refunds() -> pl.DataFrame:
    return sql("""select f.raw_id, f.invoice_no, f.sku, f.customer_key, f.invoice_ts, f.quantity, f.amount from fact_lines f where f.line_class='refund'""")

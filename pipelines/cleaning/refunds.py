"""LIFO refund matching: each credit-note line is allocated to the most recent earlier sale lines of the same customer and SKU
that still have unrefunded quantity. Writes main.refund_matches in the DuckDB file (status: matched, unmatched_no_customer,
unmatched_no_prior_sale = customer never bought the SKU before, unmatched_over_refund = earlier sales exist but were already fully refunded). Residual quantity of a partly matched line is its own row with status unmatched_no_prior_sale."""
from __future__ import annotations

from collections import defaultdict

import duckdb
import polars as pl

from pipelines.common import PROCESSED


def run() -> dict:
    con = duckdb.connect(str(PROCESSED / "retail.duckdb"))
    sales = con.sql("select raw_id, customer_key, sku, invoice_ts, quantity from fact_lines where line_class='sale' and customer_key is not null "
                    "order by customer_key, sku, invoice_ts, raw_id").pl()
    refunds = con.sql("select raw_id, customer_key, sku, invoice_ts, quantity from fact_lines where line_class='refund' "
                      "order by invoice_ts, raw_id").pl()
    book: dict[tuple, list] = defaultdict(list)  # (customer, sku) -> [[ts, raw_id, remaining]] in time order
    for r in sales.iter_rows():
        book[(r[1], r[2])].append([r[3], r[0], r[4]])
    out = []
    for rid, ck, sku, ts, q in refunds.iter_rows():
        need = abs(q)
        if ck is None:
            out.append((rid, None, 0, need, "unmatched_no_customer"))
            continue
        lots = book.get((ck, sku), [])
        eligible = any(lot[0] <= ts for lot in lots)  # an earlier sale of this SKU to this customer exists
        for lot in reversed(lots):
            if need == 0:
                break
            if lot[0] <= ts and lot[2] > 0:
                take = min(need, lot[2])
                lot[2] -= take
                need -= take
                out.append((rid, lot[1], take, abs(q), "matched"))
        if need > 0:
            out.append((rid, None, 0, need, "unmatched_over_refund" if eligible else "unmatched_no_prior_sale"))
    df = pl.DataFrame(out, schema=["refund_raw_id", "sale_raw_id", "matched_qty", "refund_qty", "status"], orient="row")
    df = df.with_columns(pl.col("sale_raw_id").cast(pl.Int64), pl.col("matched_qty").cast(pl.Int64), pl.col("refund_qty").cast(pl.Int64))
    con.execute("drop table if exists refund_matches")
    con.register("df", df.to_arrow())
    con.execute("create table refund_matches as select * from df")
    s = con.sql("select status, count(*) n, sum(matched_qty) mq, sum(refund_qty) rq from refund_matches group by 1").fetchall()
    con.close()
    return {r[0]: {"rows": r[1], "matched_qty": r[2], "qty_field": r[3]} for r in s}


if __name__ == "__main__":
    print(run())

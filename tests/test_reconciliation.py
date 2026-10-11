"""Revenue and rows reconcile: raw = kept + excluded, and every published total equals the sum of line items recomputed independently from the raw parquet."""
import duckdb
import pytest

from pipelines.common import INTERIM

pytestmark = pytest.mark.slow


def raw_con():
    c = duckdb.connect()
    c.execute(f"create view r as select * from read_parquet('{INTERIM}/raw_lines.parquet')")
    return c


def test_sheet_counts(ledger):
    assert [s["sheet"] for s in ledger["sheets"]] == ["Year 2009-2010", "Year 2010-2011"]
    assert [s["rows"] for s in ledger["sheets"]] == [525461, 541910]
    assert sum(s["rows"] for s in ledger["sheets"]) == 1067371


def test_row_and_amount_closure(ledger):
    rl, al = ledger["row_ledger"], ledger["amount_ledger"]
    assert rl["raw_rows"] == rl["kept"] + rl["excluded"] == 1067371
    assert sum(rl["excluded_by_reason"].values()) == rl["excluded"]
    assert abs(al["raw_amount_gbp"] - al["kept_amount_gbp"] - al["excluded_amount_gbp"]) < 0.02
    assert all(i["pass"] for i in ledger["identities"])


def test_raw_amount_independent_of_dbt(ledger):
    c = raw_con()
    n, a = c.sql("select count(*), sum(round(quantity*price,4)) from r").fetchone()
    assert n == ledger["row_ledger"]["raw_rows"]
    assert abs(a - ledger["amount_ledger"]["raw_amount_gbp"]) < 0.02


def test_exclusions_independent_of_dbt(ledger):
    c = raw_con()
    k = "invoice,stock_code,description,quantity,invoice_ts,price,customer_id,country"
    ov = c.sql("select count(*) from r where sheet='Year 2009-2010' and invoice_ts >= timestamp '2010-12-01'").fetchone()[0]
    assert ov == ledger["row_ledger"]["excluded_by_reason"]["overlap_duplicate"]
    dup = c.sql(f"""select count(*) from (select row_number() over (partition by {k} order by raw_id) rn from r
                    where not (sheet='Year 2009-2010' and invoice_ts >= timestamp '2010-12-01')) where rn > 1""").fetchone()[0]
    assert dup == ledger["row_ledger"]["excluded_by_reason"]["exact_duplicate"]


def test_published_revenue_equals_line_items(art, db):
    f = art("facts")["facts"]
    tot = db.sql("select sum(quantity*unit_price) from fact_lines").fetchone()[0]
    assert abs(f["revenue_total_net_gbp"]["value"] - tot) < 0.5
    sales = db.sql("select sum(quantity*unit_price) from fact_lines where line_class='sale'").fetchone()[0]
    assert abs(f["revenue_sales_gbp"]["value"] - sales) < 0.5
    parts = f["revenue_product_net_gbp"]["value"] + f["revenue_nonproduct_net_gbp"]["value"]
    assert abs(parts - f["revenue_total_net_gbp"]["value"]) < 0.5
    ov = art("overview")["series"]
    assert abs(sum(ov["product_net_gbp"]) + sum(ov["nonproduct_net_gbp"]) - tot) < 1.0


def test_family_and_product_totals(art, db):
    sales = art("facts")["facts"]["revenue_sales_gbp"]["value"]
    assert abs(sum(x["revenue_gbp"] for x in art("products")["families"]) - sales) < 1.0


def test_refund_quantities_close(art, db):
    r = art("reconciliation")["refunds"]
    q = -db.sql("select sum(quantity) from fact_lines where line_class='refund'").fetchone()[0]
    assert r["matched_qty"] + r["unmatched_qty"] == q
    # no sale line is refunded more than it was sold
    over = db.sql("""select count(*) from (select s.raw_id, max(s.quantity) q, sum(m.matched_qty) mq from refund_matches m join fact_lines s on s.raw_id = m.sale_raw_id
                     group by 1) where mq > q""").fetchone()[0]
    assert over == 0


def test_guest_excluded_from_customer_analytics(art, db):
    n = db.sql("select count(distinct customer_key) from fact_lines where line_class='sale' and customer_key is not null").fetchone()[0]
    assert art("rfm")["included"]["customers"] == n
    assert sum(x["customers"] for x in art("rfm")["segments"]) == n

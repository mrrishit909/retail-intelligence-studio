"""Data-quality checks on the star schema (schema, nulls, uniqueness, referential integrity, ranges)."""
import pytest

pytestmark = pytest.mark.slow


def one(db, q):
    return db.sql(q).fetchone()[0]


def test_primary_keys_unique(db):
    for t, k in (("fact_lines", "raw_id"), ("dim_product", "sku"), ("dim_customer", "customer_key"), ("dim_date", "date_key"), ("dim_country", "country")):
        assert one(db, f"select count(*) - count(distinct {k}) from {t}") == 0, t
        assert one(db, f"select count(*) from {t} where {k} is null") == 0, t


def test_referential_integrity(db):
    assert one(db, "select count(*) from fact_lines f left join dim_product p using (product_key) where p.product_key is null") == 0
    assert one(db, "select count(*) from fact_lines f left join dim_date d using (date_key) where d.date_key is null") == 0
    assert one(db, "select count(*) from fact_lines f left join dim_country c using (country_key) where c.country_key is null") == 0
    assert one(db, "select count(*) from fact_lines f left join dim_customer c using (customer_key) where f.customer_key is not null and c.customer_key is null") == 0
    assert one(db, "select count(*) from fact_lines where (customer_key is null) <> is_guest") == 0


def test_line_class_rules(db):
    assert one(db, "select count(*) from fact_lines where line_class='sale' and (quantity<=0 or unit_price<=0 or invoice_no like 'C%')") == 0
    assert one(db, "select count(*) from fact_lines where line_class='refund' and invoice_no not like 'C%'") == 0
    assert one(db, "select count(*) from fact_lines where line_class='stock_adjustment' and amount<>0") == 0
    assert one(db, "select count(*) from fact_lines where line_class='nonproduct' and nonproduct_class is null") == 0
    assert one(db, "select count(*) from fact_lines where line_class<>'nonproduct' and nonproduct_class is not null") == 0
    assert one(db, "select count(*) from fact_lines where quantity < 0 and line_class='sale'") == 0


def test_ranges(db):
    lo, hi = db.sql("select min(invoice_ts), max(invoice_ts) from fact_lines").fetchone()
    assert str(lo).startswith("2009-12-01") and str(hi).startswith("2011-12-09")
    assert one(db, "select count(*) from fact_lines where abs(amount - round(quantity*unit_price,4)) > 1e-6") == 0
    assert one(db, "select count(*) from dim_product where not regexp_matches(sku, '^[A-Z0-9 _]+$') and not regexp_matches(sku, '^GIFT_')") == 0


def test_no_duplicate_rows_remain(db):
    n = one(db, """select count(*) from (select 1 from stg_lines where exclusion_reason is null
                   group by invoice_no, sku, description, quantity, invoice_ts, unit_price, source_customer_id, country having count(*) > 1)""")
    assert n == 0


def test_overlap_sheet_pairs_identical(db):
    a = one(db, """select count(*) from (select invoice_no, sku, description, quantity, invoice_ts, unit_price, source_customer_id, country from stg_lines where sheet='Year 2009-2010' and is_overlap
                   except all select invoice_no, sku, description, quantity, invoice_ts, unit_price, source_customer_id, country from stg_lines where sheet='Year 2010-2011' and invoice_ts < timestamp '2010-12-10')""")
    assert a == 0


def test_families_cover_most_revenue(db):
    other = one(db, "select sum(f.amount) filter (where p.family='Other') / sum(f.amount) from fact_lines f join dim_product p using (product_key) where f.line_class='sale'")
    assert other < 0.2

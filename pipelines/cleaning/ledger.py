"""Build data/manifests/cleaning_ledger.json from the DuckDB star schema: raw = kept + excluded for rows and GBP, classes, scopes, refunds."""
from __future__ import annotations

import json

import duckdb

from pipelines.common import LEDGER, MANIFESTS, PROCESSED, write_json

TREAT = {
    "sale": "Revenue and product and customer analytics (customer analytics only if Customer ID present).",
    "refund": "Negative revenue; matched LIFO to earlier sales of the same customer and SKU; not counted as purchases.",
    "stock_adjustment": "Zero-value write-offs and free items; amount is 0; excluded from product and customer analytics.",
    "nonproduct": "In revenue totals; excluded from product and customer analytics.",
}


def run() -> dict:
    con = duckdb.connect(str(PROCESSED / "retail.duckdb"), read_only=True)
    q = lambda s: con.sql(s).fetchall()  # noqa: E731
    ex = json.loads((MANIFESTS / "extract_manifest.json").read_text())
    raw_mf = json.loads((MANIFESTS / "raw_manifest.json").read_text())
    raw_rows, raw_amt = q("select count(*), sum(round(quantity*price,4)) from stg_raw")[0]
    exc = {r[0]: (r[1], r[2]) for r in q("select exclusion_reason, count(*), sum(amount) from stg_lines where exclusion_reason is not null group by 1")}
    kept_rows, kept_amt = q("select count(*), sum(amount) from fact_lines")[0]
    ex_rows = sum(v[0] for v in exc.values())
    ex_amt = sum(v[1] for v in exc.values())
    classes = [dict(**{"class": c, "rows": n, "amount_gbp": round(a, 2), "units": int(u), "treatment": TREAT[c]})
               for c, n, a, u in q("select line_class, count(*), sum(amount), sum(quantity) from fact_lines group by 1 order by 1")]
    sc = [dict(**{"class": c, "codes": codes[:12], "rows": n, "amount_gbp": round(a, 2)}) for c, codes, n, a in q(
        "select nonproduct_class, list(distinct sku order by sku), count(*), sum(amount) from fact_lines where nonproduct_class is not null group by 1 order by 3 desc")]
    g_rows, g_amt = q("select count(*), sum(amount) from fact_lines where is_guest")[0]
    sale = q("select count(*), count(*) filter (where is_guest), count(distinct invoice_no) from fact_lines where line_class='sale'")[0]
    sale_cust = sale[0] - sale[1]
    wk = q("select count(*) from fact_lines f join dim_date d using (date_key) where not d.in_complete_week and line_class='sale'")[0][0]
    cls = {c["class"]: c["rows"] for c in classes}
    scopes = [
        {"analysis": "Revenue and reconciliation", "rule": "all kept lines", "rows_in": kept_rows, "rows_out": kept_rows, "rows_dropped_by_reason": {}},
        {"analysis": "Product analytics (top SKUs, families, landscape)", "rule": "class = sale", "rows_in": kept_rows, "rows_out": cls["sale"],
         "rows_dropped_by_reason": {k: v for k, v in cls.items() if k != "sale"}},
        {"analysis": "Baskets (association rules)", "rule": "class = sale, guest invoices included, one basket per invoice", "rows_in": kept_rows, "rows_out": cls["sale"],
         "rows_dropped_by_reason": {k: v for k, v in cls.items() if k != "sale"}},
        {"analysis": "RFM, cohorts, CLV", "rule": "class = sale and Customer ID present (refunds enter monetary value only)", "rows_in": kept_rows, "rows_out": sale_cust,
         "rows_dropped_by_reason": {**{k: v for k, v in cls.items() if k != "sale"}, "guest_sale_lines": sale[1]}},
        {"analysis": "Weekly forecasting and newsvendor demand", "rule": "class = sale in complete Monday weeks", "rows_in": kept_rows, "rows_out": cls["sale"] - wk,
         "rows_dropped_by_reason": {**{k: v for k, v in cls.items() if k != "sale"}, "incomplete_week_sale_lines": wk}},
        {"analysis": "Price elasticity evidence", "rule": "class = sale, weekly modal unit price per SKU", "rows_in": kept_rows, "rows_out": cls["sale"],
         "rows_dropped_by_reason": {k: v for k, v in cls.items() if k != "sale"}},
    ]
    r = q("""select count(*), count(distinct invoice_no), sum(amount) from fact_lines where line_class='refund'""")[0]
    cls_units = {c['class']: c['units'] for c in classes}
    tot_ref_qty0 = q("select -sum(quantity) from fact_lines where line_class='refund'")[0][0]
    rm = {s: (n, qs) for s, n, qs in q("select status, count(*), coalesce(sum(matched_qty),0) from refund_matches group by 1")}
    # a refund line may be split: matched pieces plus a residual; count distinct lines per status
    lines_matched = q("select count(distinct refund_raw_id) from refund_matches where status='matched'")[0][0]
    nocust = q("select count(distinct refund_raw_id) from refund_matches where status='unmatched_no_customer'")[0][0]
    noprior = q("select count(distinct refund_raw_id) from refund_matches where status='unmatched_no_prior_sale'")[0][0]
    overl = q("select count(distinct refund_raw_id) from refund_matches where status='unmatched_over_refund'")[0][0]
    unq = q("select coalesce(sum(refund_qty),0) from refund_matches where status like 'unmatched%'")[0][0]
    mq = q("select coalesce(sum(matched_qty),0) from refund_matches")[0][0]
    # value of each part = quantity x the credit-note line's own unit value (amount / quantity)
    val = {s: (int(qty), float(v)) for s, qty, v in q("""select m.status, sum(case when m.status='matched' then m.matched_qty else m.refund_qty end),
        sum((case when m.status='matched' then m.matched_qty else m.refund_qty end) * (f.amount / f.quantity)) from refund_matches m join fact_lines f on f.raw_id = m.refund_raw_id group by 1""")}
    g = lambda s: val.get(s, (0, 0.0))  # noqa: E731
    refunds = {"lines": r[0], "invoices": r[1], "value_gbp": round(r[2], 2), "matched_lines": lines_matched, "matched_qty": int(mq), "unmatched_qty": int(unq),
               "unmatched_no_customer_lines": nocust, "unmatched_no_prior_sale_lines": noprior,
               "matching_rule": "LIFO within customer and SKU against earlier sale lines with unrefunded quantity; residual quantity is unmatched.",
               "over_refund_lines": overl, "sale_units": int(cls_units["sale"]), "refunded_qty": int(tot_ref_qty0),
               "matched_value_gbp": round(g("matched")[1], 2), "unmatched_no_prior_sale_qty": g("unmatched_no_prior_sale")[0], "unmatched_no_prior_sale_value_gbp": round(g("unmatched_no_prior_sale")[1], 2),
               "unmatched_no_customer_qty": g("unmatched_no_customer")[0], "unmatched_no_customer_value_gbp": round(g("unmatched_no_customer")[1], 2),
               "over_refund_qty": g("unmatched_over_refund")[0], "over_refund_value_gbp": round(g("unmatched_over_refund")[1], 2),
               "value_basis": "Each part = quantity x the credit-note line's own unit value (amount / quantity); the four parts sum to the refunded value (positive GBP)."}
    monthly = [{"month": m, "amount_gbp": round(a, 2)} for m, a in q("select month, sum(amount) from fact_lines group by 1 order by 1")]
    tot_ref_qty = q("select -sum(quantity) from fact_lines where line_class='refund'")[0][0]
    ids = []

    def idn(i, d, l, rr, tol=0.01):
        ids.append({"id": i, "description": d, "lhs": float(l), "rhs": float(rr), "abs_diff": float(abs(l - rr)), "pass": bool(abs(l - rr) <= tol)})
    idn("rows_closure", "raw rows = kept rows + excluded rows", raw_rows, kept_rows + ex_rows, 0)
    idn("amount_closure", "raw GBP = kept GBP + excluded GBP", raw_amt, kept_amt + ex_amt)
    idn("class_amounts", "sum of class amounts = kept GBP", sum(c["amount_gbp"] for c in classes), kept_amt, 0.05)
    idn("class_rows", "sum of class rows = kept rows", sum(c["rows"] for c in classes), kept_rows, 0)
    idn("monthly_sum", "sum of monthly revenue = kept GBP", sum(m["amount_gbp"] for m in monthly), kept_amt, 0.5)
    idn("customer_plus_guest", "known-customer GBP + guest GBP = kept GBP", q("select sum(amount) from fact_lines where not is_guest")[0][0] + g_amt, kept_amt)
    idn("refund_qty_closure", "matched + unmatched refund quantity = refunded quantity", mq + unq, tot_ref_qty, 0)
    idn("refund_value_closure", "matched + unmatched refund value = refund value", sum(v for _, v in val.values()), -r[2], 0.05)
    idn("sheet_rows", "sheet rows sum to UCI instance count", sum(s["rows"] for s in ex["sheets"]), 1067371, 0)
    idn("overlap_identical_copy", "overlap rows excluded = rows of sheet 2 in the overlap window", exc["overlap_duplicate"][0],
        q("select count(*) from stg_raw where sheet='Year 2010-2011' and invoice_ts < timestamp '2010-12-10'")[0][0], 0)
    led = {
        "schema_version": "v1", "tags": {"ledger": "OBSERVED"}, "retrieved_at": raw_mf["retrieved_at"],
        "raw_files": raw_mf["files"], "sheets": ex["sheets"],
        "row_ledger": {"raw_rows": raw_rows, "kept": kept_rows, "excluded": ex_rows, "excluded_by_reason": {k: v[0] for k, v in exc.items()},
                       "identity": "raw_rows = kept + excluded"},
        "amount_ledger": {"raw_amount_gbp": round(raw_amt, 2), "kept_amount_gbp": round(kept_amt, 2), "excluded_amount_gbp": round(ex_amt, 2),
                          "excluded_by_reason_gbp": {k: round(v[1], 2) for k, v in exc.items()}, "identity": "raw_amount = kept_amount + excluded_amount"},
        "classes": classes, "analytics_scopes": scopes,
        "guest": {"rows": g_rows, "row_share": g_rows / kept_rows, "amount_gbp": round(g_amt, 2), "amount_share": g_amt / kept_amt,
                  "note": "Rows without Customer ID stay in revenue totals and baskets, and are excluded from RFM, cohorts and CLV."},
        "refunds": refunds, "stockcode_classes": sc, "identities": ids, "monthly": monthly,
        "extras": {"sale_lines": sale[0], "sale_lines_guest": sale[1], "sale_invoices": sale[2], "sale_lines_incomplete_week": wk,
                   "zero_price_lines": q("select count(*) from fact_lines where unit_price <= 0")[0][0]},
    }
    write_json(LEDGER, led, compact=False)
    con.close()
    return led


if __name__ == "__main__":
    l = run()
    print(json.dumps({k: l[k] for k in ("row_ledger", "amount_ledger", "guest", "refunds")}, indent=1))
    print([i for i in l["identities"] if not i["pass"]])

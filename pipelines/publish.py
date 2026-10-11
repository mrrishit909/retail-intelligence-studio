"""Build every artifact in site/public/data/ from the DuckDB star schema + analytics (deterministic: fixed seeds, no wall-clock in analytics)."""
from __future__ import annotations

import datetime as dt
import gzip
import importlib.metadata as md
import json
import math
import platform
import re

import duckdb
import numpy as np
import polars as pl
from scipy.stats import norm, spearmanr

from analytics import baskets as bk, clv, cohorts, data, elasticity as el, forecasting as fc, newsvendor as nv, rfm as rf
from pipelines.common import ATTRIBUTION, DOI, LEDGER, MANIFESTS, PIPELINE_VERSION, PUBLIC, SEED, URL, write_json

OBS, DER, PRED, SIM = "OBSERVED", "DERIVED", "PREDICTED", "SIMULATED"
MODEL_LABELS = {"snaive": "Seasonal naive (same week last year)", "mean4": "4-week mean", "ets": "Damped-trend smoothing", "seasonal_ratio": "Seasonal ratio", "ensemble": "Ensemble (smoothing + seasonal ratio)"}
GBP = "GBP"


def py(o, nd=None):
    if isinstance(o, dict):
        return {str(k): py(v, nd) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [py(v, nd) for v in o]
    if isinstance(o, np.ndarray):
        return py(o.tolist(), nd)
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if not math.isfinite(f) else (round(f, nd) if nd is not None else f)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, (dt.date, dt.datetime)):
        return o.isoformat()[:10]
    return o


def tvv(value, unit, tag, note=None):
    d = {"value": py(value), "unit": unit, "tag": tag}
    if note:
        d["note"] = note
    return d


def ds(d) -> str:
    return d.isoformat()[:10]


def run() -> dict:
    ledger = json.loads(LEDGER.read_text())
    raw_mf = json.loads((MANIFESTS / "raw_manifest.json").read_text())
    con = data.con()
    Q = lambda s: con.sql(s).fetchall()  # noqa: E731
    out: dict[str, dict] = {}
    facts: dict[str, dict] = {}

    def F(key, value, unit, tag, note=None):
        facts[key] = tvv(value, unit, tag, note)

    # ------------------------------------------------------------ reconciliation + core facts
    L = ledger
    cls = {c["class"]: c for c in L["classes"]}
    sales_amt = cls["sale"]["amount_gbp"]; ref_amt = cls["refund"]["amount_gbp"]
    nonprod_amt = cls["nonproduct"]["amount_gbp"]
    total_net = L["amount_ledger"]["kept_amount_gbp"]
    rl = L["row_ledger"]; rfd = L["refunds"]; ex = L["extras"]
    weeks = sorted(data.sql("select distinct week_start from dim_date where in_complete_week")["week_start"].to_list())
    first_ts, last_ts = Q("select min(invoice_ts), max(invoice_ts) from fact_lines")[0]
    out["reconciliation"] = {"schema_version": "v1", "tags": {"ledger": OBS, "classes": OBS, "refunds": DER, "identities": DER},
        **{k: L[k] for k in ("raw_files", "retrieved_at", "sheets", "row_ledger", "amount_ledger", "classes", "analytics_scopes", "guest", "refunds", "stockcode_classes", "identities", "monthly")}}
    out["reconciliation"]["refunds"] = {k: v for k, v in L["refunds"].items()}
    n_inv = Q("select count(distinct invoice_no) from fact_lines")[0][0]
    n_cust = Q("select count(*) from dim_customer")[0][0]
    n_sku = Q("select count(*) from dim_product where is_product")[0][0]
    n_ctry = Q("select count(*) from dim_country")[0][0]
    F("rows_raw", rl["raw_rows"], "rows", OBS); F("rows_kept", rl["kept"], "rows", OBS); F("rows_excluded", rl["excluded"], "rows", OBS)
    F("rows_overlap_duplicates", rl["excluded_by_reason"]["overlap_duplicate"], "rows", OBS, "Identical copies of 2010-12-01 to 2010-12-09 rows present in both sheets.")
    F("rows_exact_duplicates", rl["excluded_by_reason"]["exact_duplicate"], "rows", OBS, "Rows identical on all eight columns to an earlier row; some may be genuine repeated scans.")
    F("sheets", 2, "sheets", OBS)
    F("invoices", n_inv, "invoices", OBS); F("customers_known", n_cust, "customers", OBS); F("skus_product", n_sku, "SKUs", OBS); F("countries", n_ctry, "countries", OBS)
    F("revenue_sales_gbp", sales_amt, GBP, OBS); F("revenue_refunds_gbp", ref_amt, GBP, OBS)
    F("revenue_product_net_gbp", sales_amt + ref_amt, GBP, OBS); F("revenue_nonproduct_net_gbp", nonprod_amt, GBP, OBS, "Postage, fees, manual adjustments, vouchers, bad debt.")
    F("revenue_total_net_gbp", total_net, GBP, OBS)
    F("refund_lines", rfd["lines"], "lines", OBS); F("refund_invoices", rfd["invoices"], "invoices", OBS)
    F("refund_value_share_of_sales", -ref_amt / sales_amt, "share", OBS)
    F("refund_matched_line_share", rfd["matched_lines"] / rfd["lines"], "share", DER, "Share of refund lines with at least part matched to an earlier sale.")
    ref_qty = -Q("select sum(quantity) from fact_lines where line_class='refund'")[0][0]
    F("refund_matched_qty_share", rfd["matched_qty"] / ref_qty, "share", DER)
    F("refund_unmatched_no_customer_share", rfd["unmatched_no_customer_lines"] / rfd["lines"], "share", OBS)
    F("stock_adjustment_lines", cls["stock_adjustment"]["rows"], "lines", OBS); F("nonproduct_lines", cls["nonproduct"]["rows"], "lines", OBS)
    F("guest_line_share", L["guest"]["row_share"], "share", OBS); F("guest_revenue_share", L["guest"]["amount_share"], "share", OBS)
    F("zero_price_lines", ex["zero_price_lines"], "lines", OBS); F("weeks_complete", len(weeks), "weeks", OBS)

    # ------------------------------------------------------------ overview
    months = [r[0] for r in Q("select distinct month from fact_lines order by 1")]
    mo = {r[0]: r[1:] for r in Q("""select month, sum(amount) filter (where line_class='sale'), sum(amount) filter (where line_class='refund'),
        sum(amount) filter (where line_class in ('sale','refund')), sum(amount) filter (where line_class='nonproduct'),
        count(distinct invoice_no) filter (where line_class='sale'), count(distinct customer_key) filter (where line_class='sale'),
        sum(amount) filter (where is_guest) / sum(amount) from fact_lines group by 1""")}
    z = lambda v: 0.0 if v is None else v  # noqa: E731
    ser = {"sales_gbp": [round(z(mo[m][0]), 2) for m in months], "refunds_gbp": [round(z(mo[m][1]), 2) for m in months],
           "product_net_gbp": [round(z(mo[m][2]), 2) for m in months], "nonproduct_net_gbp": [round(z(mo[m][3]), 2) for m in months],
           "invoices": [int(mo[m][4]) for m in months], "active_customers": [int(mo[m][5]) for m in months], "guest_revenue_share": [round(z(mo[m][6]), 4) for m in months]}
    ctr = Q("""select c.country, sum(f.amount), count(distinct f.invoice_no), count(distinct f.customer_key) from fact_lines f join dim_country c using (country_key)
               group by 1 order by 2 desc""")
    top = ctr[:14]; rest = ctr[14:]
    countries = [{"country": c, "net_gbp": round(a, 2), "share": a / total_net, "invoices": int(i), "customers": int(k)} for c, a, i, k in top]
    rhythm_rows = Q("""select isodow(invoice_ts), hour(invoice_ts), sum(amount), count(*) from fact_lines where line_class='sale' group by 1,2""")
    hours = list(range(6, 21)); sg = np.zeros((7, len(hours))); ln = np.zeros((7, len(hours)), dtype=int)
    for d_, h_, a, n in rhythm_rows:
        if h_ in hours:
            sg[d_ - 1, hours.index(h_)] += a; ln[d_ - 1, hours.index(h_)] += n
    lv = [0.1, 0.25, 0.5, 0.75, 0.9, 0.99]
    bq = con.sql("""select count(*) n_lines, sum(amount) v from fact_lines where line_class='sale' group by invoice_no""").pl()
    out["overview"] = {"schema_version": "v1", "tags": {"series": OBS, "countries": OBS, "rhythm": OBS, "basket": OBS}, "months": months, "series": ser,
        "countries": countries, "country_other": {"countries": len(rest), "net_gbp": round(sum(r[1] for r in rest), 2), "share": sum(r[1] for r in rest) / total_net},
        "rhythm": {"weekday": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "hour": hours, "sales_gbp": py(np.round(sg, 0)), "lines": ln.tolist()},
        "basket": {"quantile_levels": lv, "lines_per_invoice": py(np.quantile(bq["n_lines"].to_numpy(), lv)), "invoice_value_gbp": py(np.quantile(bq["v"].to_numpy(), lv), 2)}}

    # ------------------------------------------------------------ products + landscape
    rules = {r[1]: r[2] for r in Q("select priority, family, pattern from product_family_rules")}
    fam_kw = {r[0]: [w.strip() for w in r[1].split("|")][:14] for r in Q("select family, pattern from product_family_rules order by priority")}
    fam = Q("""select p.family, count(distinct f.sku), sum(f.amount), sum(f.quantity), count(distinct f.customer_key) from fact_lines f join dim_product p using (product_key)
               where f.line_class='sale' group by 1 order by 3 desc""")
    prod_sales = sum(r[2] for r in fam)
    fam_list = [{"family": f, "keywords": fam_kw.get(f, []), "skus": int(s), "revenue_gbp": round(a, 2), "units": int(u), "share": a / prod_sales, "customers": int(c)} for f, s, a, u, c in fam]
    other = next(x for x in fam_list if x["family"] == "Other")
    sku_total = sum(x["skus"] for x in fam_list)
    top_sku = Q("""select f.sku, any_value(p.description), any_value(p.family), sum(f.amount) rev, sum(f.quantity), count(distinct f.customer_key), count(distinct f.invoice_no),
                   median(f.unit_price), min(f.week_start), max(f.week_start) from fact_lines f join dim_product p using (product_key) where f.line_class='sale'
                   group by 1 order by rev desc""")
    refu = {r[0]: int(r[1]) for r in Q("select sku, -sum(quantity) from fact_lines where line_class='refund' group by 1")}
    revs = np.array([r[3] for r in top_sku]); cs = np.cumsum(revs) / revs.sum()
    out["products"] = {"schema_version": "v1", "tags": {"families": DER, "top_skus": OBS, "concentration": OBS}, "family_rule": "First matching regular expression of seeds/product_family_rules.csv on the upper-cased SKU description (priority order). Unmatched products are 'Other'. DERIVED: the source has no category column.",
        "family_coverage_revenue_share": 1 - other["share"], "family_coverage_sku_share": 1 - other["skus"] / sku_total, "families": fam_list,
        "top_skus": [{"sku": r[0], "description": (r[1] or "").title(), "family": r[2], "revenue_gbp": round(r[3], 2), "units": int(r[4]), "customers": int(r[5]), "invoices": int(r[6]),
                      "median_price_gbp": round(r[7], 2), "first_week": ds(r[8]), "last_week": ds(r[9]), "refund_units": refu.get(r[0], 0)} for r in top_sku[:300]],
        "concentration": {"top_10_share": float(revs[:10].sum() / revs.sum()), "top_100_share": float(revs[:100].sum() / revs.sum()),
                          "skus_for_80pct_revenue": int(np.searchsorted(cs, 0.8) + 1), "skus_total": len(revs)}}
    fams = [x["family"] for x in fam_list]
    lm = {(r[0], r[1]): r[2] for r in Q("""select p.family, f.week_start, sum(f.amount) from fact_lines f join dim_product p using (product_key) join dim_date d using (date_key)
                                           where f.line_class='sale' and d.in_complete_week group by 1,2""")}
    out["landscape"] = {"schema_version": "v1", "tags": {"revenue_gbp": OBS}, "weeks": [ds(w) for w in weeks], "families": fams,
        "revenue_gbp": [[round(lm.get((f, w), 0.0), 0) for w in weeks] for f in fams], "unit": "GBP of sale lines per Monday week",
        "note": "Complete Monday weeks only (the first and last partial weeks are dropped). Weeks with zero are real shop closures around Christmas."}

    # ------------------------------------------------------------ rfm
    R = rf.compute(); df = R["df"]
    seg = df["segment"].to_numpy(); mon = df["monetary"].to_numpy(); rec = df["recency_days"].to_numpy(); fr = df["frequency"].to_numpy()
    countries_all = sorted(df["country"].unique().to_list()); cidx = {c: i for i, c in enumerate(countries_all)}
    segs = []
    for i, (nm, rule, _, note) in enumerate(rf.SEGMENTS):
        m = seg == i
        segs.append({"segment": nm, "rule": rule, "customers": int(m.sum()), "customer_share": float(m.mean()), "revenue_gbp": round(float(mon[m].sum()), 2),
                     "revenue_share": float(mon[m].sum() / mon.sum()), "avg_recency_days": float(rec[m].mean()) if m.any() else 0.0,
                     "avg_frequency": float(fr[m].mean()) if m.any() else 0.0, "avg_monetary_gbp": float(mon[m].mean()) if m.any() else 0.0, "action_note": note})
    def grid2(a_, b_):
        gc = np.zeros((5, 5), dtype=int); gm = np.zeros((5, 5))
        for i_, j_, m_ in zip(df[a_], df[b_], df["monetary"]):
            gc[i_ - 1, j_ - 1] += 1; gm[i_ - 1, j_ - 1] += m_
        return gc, np.round(gm, 0)
    rg, rgm = grid2("r", "f"); rm_c, rm_g = grid2("r", "m"); fm_c, fm_g = grid2("f", "m")
    sl = Q("select count(*) filter (where is_guest), count(*), sum(amount) filter (where is_guest), sum(amount) from fact_lines where line_class='sale'")[0]
    srt = np.sort(mon)[::-1]
    out["rfm"] = {"schema_version": "v1", "tags": {"definition": DER, "segments": DER, "grid": DER, "customers": DER}, "snapshot_date": ds(rf.SNAPSHOT),
        "definition": {"recency": "Days from the customer's last sale invoice to the snapshot date (2011-12-10). Score 5 = most recent quintile.",
                       "frequency": "Distinct sale invoices. Fixed bins (ties make quantiles unstable): 1, 2, 3-4, 5-8, 9+ invoices score 1 to 5.",
                       "monetary": "Net GBP: sale lines minus credit-note lines. Score 5 = top quintile.",
                       "scoring": "Recency and monetary use quintile edges of the 5,852 customers; frequency uses fixed bins. Segments are the first matching rule in the listed order.",
                       "ties": "Quintile edges are cut with numpy.quantile at 0.2, 0.4, 0.6, 0.8; a value equal to an edge falls in the higher bin."},
        "bins": {"recency_days_edges": py(R["r_edges"]), "frequency_edges": [2, 3, 5, 9], "monetary_gbp_edges": py(R["m_edges"], 2)},
        "included": {"customers": df.height, "excluded_guest_line_share": sl[0] / sl[1], "excluded_guest_revenue_share": sl[2] / sl[3], "customers_with_only_refunds": n_cust - df.height},
        "segments": segs, "grid": {"r_by_f_customers": rg.tolist(), "r_by_f_revenue_gbp": py(rgm), "r_by_m_customers": rm_c.tolist(), "r_by_m_revenue_gbp": py(rm_g),
                 "f_by_m_customers": fm_c.tolist(), "f_by_m_revenue_gbp": py(fm_g), "axes": "Row index = first axis score 1 to 5, column index = second axis score 1 to 5. Recency score 5 = most recent."},
        "customers": {"key": py(df["customer_key"].to_numpy()), "recency_days": py(rec), "frequency": py(fr), "monetary_gbp": py(np.round(mon, 2)), "r": py(df["r"].to_numpy()),
                      "f": py(df["f"].to_numpy()), "m": py(df["m"].to_numpy()), "segment": py(seg), "country": [cidx[c] for c in df["country"]]},
        "segment_names": rf.NAMES, "country_names": countries_all}
    ch = segs[0]; lost = segs[-1]
    F("rfm_customers", df.height, "customers", DER)
    F("rfm_champions_share_customers", ch["customer_share"], "share", DER); F("rfm_champions_share_revenue", ch["revenue_share"], "share", DER)
    F("rfm_lost_share_customers", lost["customer_share"], "share", DER)
    rfm_m = (df["r"].to_numpy() >= 4) & (df["f"].to_numpy() >= 4)
    F("rfm_rf_share_customers", float(rfm_m.mean()), "share", DER, "R score >= 4 and F score >= 4.")
    F("rfm_rf_share_revenue", float(mon[rfm_m].sum() / mon.sum()), "share", DER, "Net GBP share of customers with R >= 4 and F >= 4.")
    F("rfm_top_decile_revenue_share", float(srt[: len(srt) // 10].sum() / srt.sum()), "share", DER)

    # ------------------------------------------------------------ cohorts
    C = cohorts.compute(); nC = len(C["months"])
    offs = list(range(nC))
    toL = lambda a: [[None if not np.isfinite(v) else round(float(v), 4) for v in row] for row in a]  # noqa: E731
    wsum = np.zeros(nC); wcnt = np.zeros(nC); ncoh = np.zeros(nC, dtype=int)
    for i in range(nC):
        for k in range(nC):
            if np.isfinite(C["retention"][i, k]):
                wsum[k] += C["retention"][i, k] * C["sizes"][i]; wcnt[k] += C["sizes"][i]; ncoh[k] += 1
    mean_curve = [float(wsum[k] / wcnt[k]) if wcnt[k] else None for k in range(nC)]
    cm = C["months"]
    act_rows = {m_: (n_, s_, nt_) for m_, n_, s_, nt_ in Q("""select month, count(distinct customer_key) filter (where line_class='sale'),
        coalesce(sum(amount) filter (where line_class='sale' and customer_key is not null), 0),
        coalesce(sum(amount) filter (where customer_key is not null), 0) from fact_lines group by 1""")}
    out["cohorts"] = {"schema_version": "v1", "tags": {"retention": DER, "revenue_retention": DER, "mean_curve": DER}, "definition": "Cohort = month of the customer's first sale invoice in the ledger. Retention(k) = share of the cohort with at least one sale invoice in month first+k. Revenue retention = cohort net sale GBP in month k over month 0.",
        "min_cohort_size": int(min(C["sizes"])), "cohort_months": C["months"], "sizes": [int(s) for s in C["sizes"]], "offsets": offs,
        "retention": toL(C["retention"]), "revenue_retention": toL(C["revenue_retention"]), "orders_per_active": toL(C["orders_per_active"]),
        "mean_curve": {"offsets": offs, "retention": [None if v is None else round(v, 4) for v in mean_curve], "n_cohorts": [int(v) for v in ncoh]},
        "active_customers": [int(act_rows[m_][0]) for m_ in cm], "active_revenue_gbp": [round(float(act_rows[m_][1]), 2) for m_ in cm],
        "active_net_revenue_gbp": [round(float(act_rows[m_][2]), 2) for m_ in cm],
        "active_definition": "Known customers (Customer ID present) with at least one sale line in the calendar month, the same activity definition as cohort retention (all cohorts together, including customers from later cohorts). active_revenue_gbp = their sale-line GBP (the basis of revenue_retention); active_net_revenue_gbp also nets their credit-note lines. overview.series.active_customers uses the same definition and also includes the partial month 2011-12.",
        "notes": ["The 2009-12 cohort (951 customers) mixes true new customers with existing customers whose first purchase was before the ledger starts (left-censoring); it is not a clean acquisition cohort.",
                  "Months after 2011-11 are not observed (the ledger ends on 2011-12-09); 2011-12 is dropped as partial. Later cohorts therefore have fewer offsets.",
                  "Guest rows (no Customer ID) cannot be tracked and are excluded."],
        "right_censoring": "Cells beyond 2011-11 are null, never zero."}
    r1 = np.array([C["retention"][i, 1] for i in range(nC - 1)]); r12 = np.array([C["retention"][i, 12] for i in range(nC) if np.isfinite(C["retention"][i, 12])])
    r3 = np.array([C["retention"][i, 3] for i in range(nC) if np.isfinite(C["retention"][i, 3])])
    F("cohort_count", nC, "cohorts", DER); F("cohort_m1_retention_median", float(np.median(r1)), "share", DER); F("cohort_m12_retention_median", float(np.median(r12)), "share", DER)
    F("cohort_best_m3_retention", float(r3.max()), "share", DER); F("cohort_worst_m3_retention", float(r3.min()), "share", DER)

    # ------------------------------------------------------------ baskets
    X, skus, dmeta = bk.baskets_matrix()
    nb, minc, f1, c1f, pairs, triples = bk.mine(X)
    allr = bk.rules(nb, f1, c1f, pairs, triples)
    sk_of = lambda i: skus[f1[i]]  # noqa: E731

    def stem(sku):
        w = (dmeta[sku][1] or "").upper().split()
        return (" ".join(w[:2]), " ".join(w[-2:]))

    def is_variant_sku(sk_list):
        st = [stem(s_) for s_ in sk_list]
        return len({s[0] for s in st}) == 1 or len({s[1] for s in st}) == 1

    def is_variant(items):
        return is_variant_sku([sk_of(i) for i in items])

    # DR-1 hero pair: over ALL pairs of product SKUs (not limited by the support threshold), the most baskets in common
    CC = (X.T @ X).tocoo()
    cnt_all = np.asarray(X.sum(0)).ravel()
    msk = CC.row < CC.col
    ra_, rb_, rn_ = CC.row[msk], CC.col[msk], CC.data[msk].astype(np.int64)
    lift_all = rn_ * nb / (cnt_all[ra_] * cnt_all[rb_])
    order_ = np.lexsort((np.array([skus[j] + "|" + skus[k] for j, k in zip(ra_, rb_)]), -lift_all, -rn_))
    heroes = []
    for o_ in order_[:5]:
        ia, ib = int(ra_[o_]), int(rb_[o_])
        if (cnt_all[ia], skus[ib]) < (cnt_all[ib], skus[ia]):
            ia, ib = ib, ia  # anchor = the larger set (ties: SKU order)
        heroes.append((skus[ia], skus[ib], int(cnt_all[ia]), int(cnt_all[ib]), int(rn_[o_]), float(lift_all[o_])))
    ha, hb, hna, hnb, hnab, hlift = heroes[0]
    hero_set = frozenset((ha, hb))

    rows = []
    for ante, cons, c, sup, conf, lift, lev, conv in allr:
        items = ante + cons
        fm = sorted({dmeta[sk_of(i)][0] for i in items})
        rows.append({"antecedent": [sk_of(i) for i in ante], "consequent": [sk_of(i) for i in cons], "antecedent_desc": [(dmeta[sk_of(i)][1] or "").title() for i in ante],
                     "consequent_desc": [(dmeta[sk_of(i)][1] or "").title() for i in cons], "support": sup, "confidence": conf, "lift": lift, "leverage": lev,
                     "conviction": None if conv is None else float(conv), "count": int(c), "same_family": len(fm) == 1, "families": fm, "variant_of_same_product": bool(is_variant(items))})
    rows.sort(key=lambda r: (-r["lift"], r["antecedent"], r["consequent"]))
    # DR-2 showcase: 3 highest-lift then 3 highest-count rules, non-variant, hero pair excluded, one rule per itemset
    iset = lambda r: frozenset(r["antecedent"] + r["consequent"])  # noqa: E731
    cand_ = [r for r in rows if not r["variant_of_same_product"] and iset(r) != hero_set]
    show, used = [], set()
    for r in cand_:  # rows are sorted by lift desc
        if iset(r) not in used and len([s_ for s_ in show if s_[1] == "lift"]) < 3:
            used.add(iset(r)); show.append((r, "lift"))
    for r in sorted(cand_, key=lambda r: (-r["count"], -r["lift"], r["antecedent"], r["consequent"])):
        if iset(r) not in used and len([s_ for s_ in show if s_[1] == "count"]) < 3:
            used.add(iset(r)); show.append((r, "count"))
    assert len(show) == 6
    pick = [s_[0] for s_ in show] + [r for r in rows if not r["variant_of_same_product"]][:40] + [r for r in rows if r["variant_of_same_product"]][:20]
    pick += [r for r in rows if not r["same_family"] and not r["variant_of_same_product"]][:20]
    seen, sel = set(), []
    for r in pick:
        k = (tuple(r["antecedent"]), tuple(r["consequent"]))
        if k not in seen:
            seen.add(k); sel.append(r)
    sel.sort(key=lambda r: (-r["lift"], r["antecedent"], r["consequent"]))
    key_ = lambda r: (tuple(r["antecedent"]), tuple(r["consequent"]))  # noqa: E731
    pos_ = {key_(r): i for i, r in enumerate(sel)}
    showcase = {"rule": "3 highest-lift rules, then 3 highest-count rules, all with variant_of_same_product false, the hero pair excluded, one rule per itemset (a rule and its reverse count once); chosen over all mined rules, then forced into the published list.",
                "indices": [pos_[key_(s_[0])] for s_ in show], "kinds": [s_[1] for s_ in show], "itemsets": [s_[0]["antecedent"] + s_[0]["consequent"] for s_ in show]}
    deg = {}
    pe = []
    for (a, b), c in pairs.items():
        lf = c * nb / (c1f[a] * c1f[b]); pe.append((lf, a, b, c))
    pe.sort(reverse=True)
    pe_sel = [e for e in pe if not is_variant((e[1], e[2]))][:260]
    for _, a, b, _c in pe_sel:
        deg[a] = deg.get(a, 0) + 1; deg[b] = deg.get(b, 0) + 1
    nodes = [{"sku": sk_of(i), "description": (dmeta[sk_of(i)][1] or "").title(), "family": dmeta[sk_of(i)][0], "support": float(c1f[i] / nb), "baskets": int(c1f[i]), "degree": d_}
             for i, d_ in sorted(deg.items(), key=lambda t: -t[1])]
    skix = {s_: i for i, s_ in enumerate(skus)}
    hero_edge = {"a": ha, "b": hb, "support": hnab / nb, "lift": hlift, "count": hnab, "same_family": dmeta[ha][0] == dmeta[hb][0], "hero": True}
    hero_rule = ("Over all pairs of product SKUs (any support), the pair with the most baskets in common; ties: higher lift, then SKU order. Anchor = the larger set. "
                 "chance = na * nb / baskets; lift = nab * baskets / (na * nb).")
    out["baskets"] = {"schema_version": "v1", "tags": {"params": DER, "rules": DER, "nodes": DER, "edges": DER, "showcase": DER, "hero": DER}, "showcase": showcase,
        "hero": {"a": ha, "b": hb, "a_desc": (dmeta[ha][1] or "").title(), "b_desc": (dmeta[hb][1] or "").title(), "na": hna, "nb": hnb, "nab": hnab, "baskets": nb, "chance": hna * hnb / nb, "lift": hlift,
                 "support": hnab / nb, "confidence_a_to_b": hnab / hna, "confidence_b_to_a": hnab / hnb, "same_family": hero_edge["same_family"],
                 "variant_of_same_product": bool(is_variant_sku([ha, hb])), "selection_rule": hero_rule,
                 "runner_up": [{"a": a_, "b": b_, "nab": n_, "lift": l_} for a_, b_, _na, _nb, n_, l_ in heroes[1:]] or [{"a": "", "b": "", "nab": 0, "lift": 0.0}]},
        "params": {"min_support": bk.MIN_SUPPORT, "min_confidence": bk.MIN_CONFIDENCE, "min_lift": bk.MIN_LIFT, "max_len": bk.MAX_LEN, "baskets": nb, "frequent_items": len(f1),
                   "frequent_itemsets": len(f1) + len(pairs) + len(triples), "basket_definition": "One basket per invoice with at least one sale line (guest invoices included).",
                   "item_definition": "SKU (upper-cased); a SKU counts once per basket.", "support_count_min": minc},
        "rules_total": len(rows), "rules": sel,
        "nodes": nodes, "edges": [{"a": sk_of(a), "b": sk_of(b), "support": c / nb, "lift": float(lf), "count": int(c), "same_family": dmeta[sk_of(a)][0] == dmeta[sk_of(b)][0], "hero": False} for lf, a, b, c in pe_sel]
                 + ([hero_edge] if not any({sk_of(a), sk_of(b)} == {ha, hb} for _l, a, b, _c in pe_sel) else []),
        "caveat": "Top-lift rules are dominated by colour and pattern variants of one product (flagged variant_of_same_product); the featured list shows non-variant rules first. Association is co-occurrence in one invoice, not causation, and wholesale buyers order many lines at once."}
    xf = sum(1 for r in rows if not r["same_family"])
    szs = np.asarray(X.sum(1)).ravel()
    for e_ in out["baskets"]["edges"]:
        if {e_["a"], e_["b"]} == {ha, hb}:
            e_["hero"] = True
    F("hero_pair_na", hna, "baskets", DER); F("hero_pair_nb", hnb, "baskets", DER); F("hero_pair_nab", hnab, "baskets", DER)
    F("hero_pair_chance", hna * hnb / nb, "baskets", DER, "Baskets expected to contain both if the two were independent: na * nb / baskets.")
    F("hero_pair_lift", hlift, "lift", DER)
    F("hero_pair_a", ha, "SKU", DER); F("hero_pair_b", hb, "SKU", DER); F("hero_pair_a_desc", (dmeta[ha][1] or "").title(), "text", OBS); F("hero_pair_b_desc", (dmeta[hb][1] or "").title(), "text", OBS)
    F("hero_selection_rule", hero_rule, "text", DER)
    F("basket_count", nb, "baskets", DER); F("basket_min_support", bk.MIN_SUPPORT, "share of baskets", DER, f"Itemset must appear in at least {minc} baskets.")
    F("basket_min_confidence", bk.MIN_CONFIDENCE, "share", DER); F("basket_frequent_items", len(f1), "SKUs", DER); F("basket_rules_total", len(rows), "rules", DER)
    F("basket_rules_cross_family", xf, "rules", DER); F("basket_top_lift", rows[0]["lift"], "lift", DER); F("basket_median_size_lines", float(np.median(szs)), "SKUs per basket", OBS)

    # ------------------------------------------------------------ clv
    tx = clv.transactions()
    cal = clv.rfm_frame(tx, clv.CAL_END)
    x = cal["x"].to_numpy().astype(float); t_x = cal["tx"].to_numpy(); T_ = cal["T"].to_numpy(); keys = cal["customer_key"].to_numpy()
    bg = clv.fit_bgnbd(x, t_x, T_); bg["n_customers"] = len(x)
    H = ((clv.HOLD_END - clv.CAL_END).days) / 7.0
    pred = clv.expected_purchases(bg, H, x, t_x, T_)
    hold = tx.filter((pl.col("day") >= clv.HOLD_START) & (pl.col("day") <= clv.HOLD_END)).group_by("customer_key").len()
    actual = cal.join(hold, on="customer_key", how="left")["len"].fill_null(0).to_numpy().astype(float)
    pop_rate = x.sum() / T_.sum()
    base_pop = pop_rate * H * np.ones_like(x)
    base_ind = np.where(T_ > 0, x / np.maximum(T_, 1e-9) * H, 0.0)
    ov_sum, base_ov_sum = float(np.minimum(pred, actual).sum()), float(np.minimum(base_pop, actual).sum())
    mae, mae_pop, mae_ind = np.abs(pred - actual).mean(), np.abs(base_pop - actual).mean(), np.abs(base_ind - actual).mean()
    order = np.argsort(pred, kind="stable"); dec = np.array_split(order, 10)
    deciles = [{"decile": i + 1, "customers": len(g), "predicted": float(pred[g].mean()), "actual": float(actual[g].mean()),
                "predicted_sum": float(pred[g].sum()), "actual_sum": float(actual[g].sum()), "baseline_predicted": float(base_pop[g].mean()), "baseline_predicted_sum": float(base_pop[g].sum()),
                "overlap_sum": float(np.minimum(pred[g], actual[g]).sum()),
                "error_pct": float(100 * (pred[g].mean() - actual[g].mean()) / actual[g].mean()) if actual[g].mean() > 0 else 0.0} for i, g in enumerate(dec)]
    mape_dec = float(np.mean([abs(d_["error_pct"]) for d_ in deciles]))
    byf = []
    for k in (0, 1, 2, 3, 4, 5):
        m = (x >= 5) if k == 5 else (x == k)
        byf.append({"repeats_in_calibration": k, "customers": int(m.sum()), "predicted": float(pred[m].mean()), "actual": float(actual[m].mean())})
    tot_err = float(100 * (pred.sum() - actual.sum()) / actual.sum())
    corr = float(np.corrcoef(pred, actual)[0, 1]); rho = float(spearmanr(pred, actual)[0])
    # gamma-gamma on calibration repeaters
    rep = cal.filter(pl.col("x") > 0)
    gg_cal = clv.fit_gg(rep["x"].to_numpy().astype(float), rep["m"].to_numpy()); gg_cal["n_customers"] = rep.height
    ind_corr = float(np.corrcoef(rep["x"].to_numpy(), rep["m"].to_numpy())[0, 1])
    # final fit on all data
    fin = clv.rfm_frame(tx, clv.FINAL_END)
    fx = fin["x"].to_numpy().astype(float); ftx = fin["tx"].to_numpy(); fT = fin["T"].to_numpy(); fm = np.nan_to_num(fin["m"].fill_null(0).to_numpy(), nan=0.0); fkeys = fin["customer_key"].to_numpy()
    bgf = clv.fit_bgnbd(fx, ftx, fT); bgf["n_customers"] = len(fx)
    repf = fin.filter(pl.col("x") > 0)
    ggf = clv.fit_gg(repf["x"].to_numpy().astype(float), repf["m"].to_numpy()); ggf["n_customers"] = repf.height
    DISC, HOR = 0.10, 52
    exp_n, exp_52 = clv.discounted_expected(bgf, fx, ftx, fT, HOR, DISC)
    ev = np.where(fx > 0, clv.gg_expected_value(ggf, np.maximum(fx, 1), fm), ggf["p"] * ggf["v"] / (ggf["q"] - 1))
    clv_c = exp_n * ev
    pal = clv.p_alive(bgf, fx, ftx, fT)
    srt_c = np.sort(clv_c)[::-1]
    ql = [0.1, 0.25, 0.5, 0.75, 0.9, 0.99]
    segmap = dict(zip(df["customer_key"].to_numpy().tolist(), seg.tolist()))
    bys = []
    for i, nm in enumerate(rf.NAMES):
        m = np.array([segmap.get(int(k), -1) == i for k in fkeys])
        bys.append({"segment": nm, "customers": int(m.sum()), "clv_mean_gbp": float(clv_c[m].mean()) if m.any() else 0.0, "clv_total_gbp": float(clv_c[m].sum()),
                    "p_alive_mean": float(pal[m].mean()) if m.any() else 0.0, "expected_purchases_mean": float(exp_52[m].mean()) if m.any() else 0.0})
    out["clv"] = {"schema_version": "v1", "tags": {"model": PRED, "calibration": PRED, "holdout": PRED, "deciles": PRED, "final_fit": PRED, "customers": PRED, "gamma_gamma_check": DER},
        "model": {"bgnbd": {k: bg[k] for k in ("r", "alpha", "a", "b", "loglik", "converged", "n_customers")}, "gamma_gamma": {k: gg_cal[k] for k in ("p", "q", "v", "loglik", "converged", "n_customers")},
                  "implementation": "Own numpy/scipy implementation of Fader, Hardie and Lee (2005) BG/NBD and Fader and Hardie (2013) Gamma-Gamma (maximum likelihood, L-BFGS-B on log-parameters); tested by simulation recovery in tests/test_models.py. The lifetimes package is not used.",
                  "transaction_definition": "One transaction = a customer's distinct purchase day (same-day invoices merged), sale lines only.", "time_unit": "weeks"},
        "calibration": {"start": ds(dt.date(2009, 12, 1)), "end": ds(clv.CAL_END), "holdout_start": ds(clv.HOLD_START), "holdout_end": ds(clv.HOLD_END), "holdout_weeks": H,
                        "customers": len(x), "customers_repeat_in_calibration": int((x > 0).sum()), "customers_active_in_holdout": int((actual > 0).sum())},
        "holdout": {"predicted_repeats_total": float(pred.sum()), "actual_repeats_total": int(actual.sum()), "total_error_pct": tot_err, "mae_customer": float(mae),
                    "baseline_mae_customer": float(mae_pop), "baseline_individual_rate_mae_customer": float(mae_ind), "corr_customer": corr, "rank_corr_customer": rho,
                    "baseline": "Population-average repeat rate (repeats per exposure week in calibration) times holdout weeks, identical for every customer. Alternative baseline, own history rate scaled to the holdout, is in baseline_individual_rate_mae_customer.",
                    "mape_decile_pct": mape_dec,
                    "overlap_customer_sum": ov_sum, "baseline_predicted_total": float(base_pop.sum()), "baseline_overlap_customer_sum": base_ov_sum},
        "deciles": deciles, "by_frequency": byf,
        "gamma_gamma_check": {"corr_frequency_monetary": ind_corr, "customers": rep.height, "note": "Gamma-Gamma assumes monetary value is independent of frequency; a correlation near 0 supports that. Fitted on customers with at least one repeat transaction."},
        "final_fit": {"fit_start": "2009-12-01", "fit_end": ds(clv.FINAL_END), "horizon_weeks": HOR, "discount_rate_annual": DISC, "customers": len(fx), "clv_total_gbp": float(clv_c.sum()),
                      "clv_median_gbp": float(np.median(clv_c)), "top_decile_share": float(srt_c[: len(srt_c) // 10].sum() / srt_c.sum()), "clv_quantiles": py(np.quantile(clv_c, ql), 2), "quantile_levels": ql,
                      "bgnbd_final": {k: bgf[k] for k in ("r", "alpha", "a", "b", "loglik", "converged")}, "gamma_gamma_final": {k: ggf[k] for k in ("p", "q", "v", "loglik", "converged")}},
        "by_segment": bys,
        "customers": {"key": py(fkeys), "frequency": py(fx.astype(int)), "recency_weeks": py(np.round(ftx, 2)), "age_weeks": py(np.round(fT, 2)), "monetary_gbp": py(np.round(fm, 2)),
                      "p_alive": py(np.round(pal, 4)), "expected_purchases": py(np.round(exp_52, 3)), "expected_value_gbp": py(np.round(ev, 2)), "clv_gbp": py(np.round(clv_c, 2))},
        "limitations": ["Customers are mostly trade buyers (wholesale), not households; BG/NBD assumes a constant purchase rate per customer, which seasonal buying violates.",
                        "First observed purchase is not always the true first purchase (the ledger starts 2009-12-01), so tenure is understated for existing customers.",
                        "CLV is revenue, not profit: the ledger has no cost or margin. Values are GBP revenue per customer over the next 52 weeks, discounted at 10% a year (assumption).",
                        "The calibration holdout is one 26-week window that includes the 2011 autumn peak; accuracy elsewhere is not shown."]}
    F("clv_calibration_customers", len(x), "customers", PRED); F("clv_holdout_weeks", H, "weeks", PRED)
    F("clv_pred_repeats_total", float(pred.sum()), "purchase days", PRED); F("clv_actual_repeats_total", int(actual.sum()), "purchase days", OBS)
    F("clv_total_error_pct", tot_err, "percent", PRED); F("clv_customer_corr", corr, "correlation", PRED); F("clv_decile_mape_pct", mape_dec, "percent", PRED)
    F("clv_baseline_mae", float(mae_pop), "purchases per customer", PRED); F("clv_model_mae", float(mae), "purchases per customer", PRED)
    F("clv_gg_independence_corr", ind_corr, "correlation", DER); F("clv_horizon_weeks", HOR, "weeks", PRED); F("clv_discount_rate_annual", DISC, "rate", SIM, "Assumption, not estimated.")
    F("clv_top_decile_share", float(srt_c[: len(srt_c) // 10].sum() / srt_c.sum()), "share", PRED); F("clv_total_gbp", float(clv_c.sum()), GBP, PRED); F("clv_median_gbp", float(np.median(clv_c)), GBP, PRED)
    _clv_state = dict(bg=bg, pred=pred, actual=actual)

    # ------------------------------------------------------------ forecast + backtest
    wk, ser_, meta_ = fc.weekly_matrix()
    origins, err = fc.backtest(ser_)
    ids = list(ser_); fam_ids = [i for i in ids if i.startswith("family:")]; sku_ids = [i for i in ids if i.startswith("sku:")]
    pooled_rows = []; sk_cmp = {}
    for scope, sids in (("all", ids), ("family", fam_ids), ("sku", sku_ids)):
        for h in fc.POOL_H:
            pm = fc.pooled(ser_, err, origins, sids, h); base = pm["snaive"]["mae"]
            for m_, v in pm.items():
                pooled_rows.append({"model": m_, "horizon": h, "scope": scope, **{k: float(v[k]) for k in ("mae", "wape_pct", "mase", "bias_pct", "actual_total", "forecast_total", "over_total", "under_total")}, "skill_vs_snaive_pct": float(100 * (1 - v["mae"] / base)), "n": v["n"]})
                sk_cmp[(m_, h, scope)] = v
    # choose best model: lowest mean pooled WAPE over scopes family and sku and horizons
    cand = [m_ for m_ in fc.MODELS if m_ != "snaive"]
    score = {m_: np.mean([sk_cmp[(m_, h, s)]["wape_pct"] for h in fc.POOL_H for s in ("family", "sku")]) for m_ in cand}
    best = min(score, key=score.get)
    # per-series maes (all horizons 1..4 pooled) and win rate
    by_series = []; wins = {m_: {"family": 0, "sku": 0} for m_ in cand}
    for s_ in ids:
        mm = {}
        for m_ in fc.MODELS:
            e = err[m_][s_][:, :4]; mm[m_] = float(np.nanmean(np.abs(e)))
        kind = "family" if s_.startswith("family:") else "sku"
        for m_ in cand:
            if mm[m_] < mm["snaive"]:
                wins[m_][kind] += 1
        by_series.append({"id": s_, "kind": kind, "models": {k: round(v, 3) for k, v in mm.items()}})
    win_rows = []
    for m_ in cand:
        for kind, tot in (("family", len(fam_ids)), ("sku", len(sku_ids))):
            win_rows.append({"model": m_, "scope": kind, "series_beating_snaive": wins[m_][kind], "series": tot, "share": wins[m_][kind] / tot})
    N = len(wk)
    by_origin = []
    for oi, o in enumerate(origins):
        if o + 1 >= N:
            continue
        d_ = {}
        for m_ in fc.MODELS:
            vals = [abs(err[m_][s_][oi, 0]) for s_ in ids if np.isfinite(err[m_][s_][oi, 0])]
            d_[m_] = round(float(np.mean(vals)), 2)
        by_origin.append({"origin": ds(wk[o]), "mae": d_})
    # interval quantiles per series/horizon from best model errors; coverage test: first half -> quantiles, second half -> coverage
    half = len(origins) // 2
    cover = []; qlo = {}; qhi = {}
    for s_ in ids:
        e = err[best][s_]  # forecast - actual
        for h in range(1, fc.HMAX + 1):
            col = e[:, h - 1]; ok = ~np.isnan(col)
            # actual = forecast - e  => interval for actual: f - q90(e) .. f - q10(e)
            qlo[(s_, h)] = float(np.nanquantile(col[ok], 0.10)); qhi[(s_, h)] = float(np.nanquantile(col[ok], 0.90))
        e1 = err[best][s_][:, 0]
        a, b = np.nanquantile(e1[:half], 0.10), np.nanquantile(e1[:half], 0.90)
        te = e1[half:]; te = te[~np.isnan(te)]
        cover.extend(((te >= a) & (te <= b)).tolist())
    fut_weeks = [wk[-1] + dt.timedelta(days=7 * k) for k in range(1, fc.HMAX + 1)]
    fseries = []
    ens = fc.forecasts
    for s_ in ids:
        y = ser_[s_]
        f = fc.forecasts(y, fc.HMAX)[best]
        lo = [max(0.0, float(f[h - 1] - qhi[(s_, h)])) for h in range(1, fc.HMAX + 1)]
        hi = [max(0.0, float(f[h - 1] - qlo[(s_, h)])) for h in range(1, fc.HMAX + 1)]
        pmae = {m_: float(np.nanmean(np.abs(err[m_][s_][:, :4]))) for m_ in ("snaive", best)}
        act_h = np.concatenate([[y[o + h] for o in origins if o + h < N] for h in (1, 2, 3, 4)])
        wape = lambda m_: float(100 * pmae[m_] * 1.0 / max(np.mean(act_h), 1e-9))  # noqa: E731
        kind, label, family = meta_[s_]
        fseries.append({"id": s_, "kind": kind, "label": label, "family": family, "history_units": [int(v) for v in y], "forecast": [round(float(v), 1) for v in f],
                        "lo": [round(v, 1) for v in lo], "hi": [round(max(h_, l_), 1) for h_, l_ in zip(hi, lo)], "total_units": int(y.sum()),
                        "skill_vs_snaive_pct": float(100 * (1 - pmae[best] / pmae["snaive"])) if pmae["snaive"] > 0 else None, "wape_pct": wape(best), "snaive_wape_pct": wape("snaive")})
    pr = {(r["model"], r["horizon"], r["scope"]): r for r in pooled_rows}
    verdict = (f"Best model by pooled WAPE: {best}. At horizon 1 its MAE skill versus seasonal-naive is {pr[(best, 1, 'family')]['skill_vs_snaive_pct']:.1f}% on families and "
               f"{pr[(best, 1, 'sku')]['skill_vs_snaive_pct']:.1f}% on SKUs; at horizon 8 it is {pr[(best, 8, 'family')]['skill_vs_snaive_pct']:.1f}% and {pr[(best, 8, 'sku')]['skill_vs_snaive_pct']:.1f}%. "
               "Seasonal-naive has only one prior year to copy and is the weakest model here; flat and smoothed levels beat it. The reason was not tested (a demand level shift between the two years is one candidate).")
    out["backtest"] = {"schema_version": "v1", "tags": {"design": DER, "pooled": PRED, "win_rate": PRED, "interval_coverage": PRED},
        "design": {"scheme": "Rolling origin, expanding window, every weekly origin from week 60; one forecast vector per origin up to 8 weeks ahead.", "first_origin_week": ds(wk[origins[0]]), "last_origin_week": ds(wk[origins[-1]]),
                   "origins": len(origins), "horizons": fc.POOL_H, "min_train_weeks": fc.MIN_TRAIN, "series": len(ids), "baseline": "seasonal-naive, lag 52 weeks",
                   "metrics": ["MAE (units)", "WAPE = sum|e| / sum actual", "MASE = |e| / in-sample naive-1 MAE at the origin", "bias = sum e / sum actual", "skill = 1 - MAE_model / MAE_snaive"],
                   "error_sign": "e = forecast - actual. Positive bias = over-forecast. over_total = sum max(f - a, 0), under_total = sum max(a - f, 0); over + under = sum |e| = MAE * n; actual - under = sum min(a, f); WAPE = (over + under) / actual.",
                   "total_identities": "Pooled rows exist for horizons 1, 2, 4, 8 and scopes all, family, sku; totals are sums over series and origins."},
        "models": [{"id": k, "label": MODEL_LABELS[k], "description": v} for k, v in fc.MODELS.items()], "pooled": pooled_rows, "win_rate": win_rows, "by_series": by_series, "by_origin": by_origin,
        "interval_coverage": {"nominal": 0.8, "empirical": float(np.mean(cover)), "n": len(cover)}, "verdict": verdict, "best_model": best}
    out["forecast"] = {"schema_version": "v1", "tags": {"history": OBS, "forecast": PRED, "interval": PRED}, "unit": "units per Monday week (sale lines only)", "week_start": ds(wk[0]), "weeks": [ds(w) for w in wk],
        "horizon_weeks": fc.HMAX, "forecast_weeks": [ds(w) for w in fut_weeks], "model": best,
        "interval": {"level": 0.8, "method": "Empirical 10th and 90th percentiles of the best model's backtest errors per series and horizon (all origins; coverage checked out of sample in backtest.json)."},
        "series": fseries}
    skf = lambda sc: pr[(best, 1, sc)]["skill_vs_snaive_pct"]  # noqa: E731
    F("forecast_series", len(ids), "series", PRED); F("forecast_origins", len(origins), "origins", DER); F("forecast_horizon_max", fc.HMAX, "weeks", PRED)
    F("forecast_best_model_skill_pct", pr[(best, 1, "all")]["skill_vs_snaive_pct"], "percent", PRED, "MAE skill versus seasonal-naive, horizon 1, all series pooled.")
    F("forecast_family_skill_pct", skf("family"), "percent", PRED); F("forecast_sku_skill_pct", skf("sku"), "percent", PRED)
    allwin = sum(wins[best].values()) / len(ids)
    F("forecast_win_rate", allwin, "share", PRED, "Share of series where the best model has lower MAE than seasonal-naive (horizons 1 to 4)."); F("forecast_snaive_wape_pct", pr[("snaive", 1, "all")]["wape_pct"], "percent", PRED)
    F("forecast_best_wape_pct", pr[(best, 1, "all")]["wape_pct"], "percent", PRED); F("forecast_best_model", best, "model id", PRED); F("backtest_best_model_label", MODEL_LABELS[best], "text", PRED)

    # ------------------------------------------------------------ newsvendor
    CR, SR = 0.60, 0.20
    items = []
    famprice = {r[0]: r[1] / r[2] for r in Q("select p.family, sum(f.amount), sum(f.quantity) from fact_lines f join dim_product p using (product_key) where f.line_class='sale' group by 1")}
    skuprice = {r[0]: r[1] for r in Q("select sku, median(unit_price) from fact_lines where line_class='sale' group by 1")}
    nv_ids = [i for i in fam_ids if i != "family:Other"][:6] + sku_ids[:12]
    item_stats = {}
    for s_ in nv_ids:
        y = ser_[s_]; kind, label, family = meta_[s_]
        price = famprice[family] if kind == "family" else skuprice[s_.split(":")[1]]
        f1_ = fc.forecasts(y, 1)[best][0]
        samp = y[-52:]
        sg_ = float(np.std([err[best][s_][i, 0] for i in range(len(origins)) if np.isfinite(err[best][s_][i, 0])], ddof=1))
        price = round(float(price), 4)
        item_stats[s_] = dict(price=float(price), mu=float(f1_), sigma=sg_, samples=samp)
        items.append({"id": s_, "label": label, "kind": kind, "price_gbp": float(price), "mean_weekly_units": float(samp.mean()), "sd_weekly_units": float(samp.std(ddof=1)),
                      "forecast_next_week": float(f1_), "weekly_units_sample": [int(v) for v in samp], "weeks": 52, "forecast_sd": sg_})
    cf0 = nv.fractile(1.0, CR, CR * SR)
    assum = [
        {"id": "cost_ratio", "label": "Unit cost as a share of selling price", "value": CR, "unit": "share", "basis": "Assumption. The ledger has no cost data; 0.60 is a placeholder typical of wholesale gift-ware.", "range": [0.3, 0.9]},
        {"id": "salvage_ratio", "label": "Salvage value as a share of unit cost", "value": SR, "unit": "share", "basis": "Assumption. Value recovered per unsold unit (clearance).", "range": [0.0, 0.6]},
        {"id": "review_period", "label": "Review period", "value": 1, "unit": "week", "basis": "Assumption. One stocking decision per Monday week, no carry-over of stock.", "range": [1, 1]},
        {"id": "lead_time", "label": "Replenishment lead time", "value": 0, "unit": "weeks", "basis": "Assumption. Stock arrives before the week starts; no lead-time demand uncertainty.", "range": [0, 0]},
        {"id": "price", "label": "Selling price", "value": 1.0, "unit": "share of observed price", "basis": "OBSERVED: family average selling price (revenue / units) or SKU median unit price from the ledger.", "range": [1.0, 1.0]}]
    out["newsvendor_params"] = {"schema_version": "v1", "tags": {"assumptions": SIM, "items": "OBSERVED/PREDICTED"}, "labelled": SIM, "assumptions": assum,
        "formula": {"critical_fractile": "cf = (p - c) / (p - s)", "normal": "Q* = max(0, mu + sigma * Phi^-1(cf)); demand = max(D, 0); L(z) = phi(z) - z (1 - Phi(z)); E[sales] = sigma (L(-mu / sigma) - L(zq)), zq = (Q - mu) / sigma; shortage = sigma L(zq)",
                    "empirical": "Q* = smallest sample d with F(d) >= cf; E[sales] = mean(min(d, Q))", "profit": "profit = p E[sales] - c Q + s (Q - E[sales])"},
        "items": items, "disclaimer": f"SIMULATED. Costs and salvage are assumptions, not data. Demand is OBSERVED (last 52 weeks) and PREDICTED (next-week forecast from {best} with its backtest error as sigma). The output is a what-if, not advice."}
    # vectors (DR-7): every item at the default assumptions for both models, plus non-default cases for the first 8 items
    vec = []

    def addvec(s_, cr_, sr_, model_):
        st = item_stats[s_]
        p_ = st["price"]; c_ = round(p_ * cr_, 6); s2 = round(c_ * sr_, 6)
        if model_ == "normal":
            r_ = nv.normal_policy(p_, c_, s2, st["mu"], st["sigma"])
            inp = {"price": p_, "cost": c_, "salvage": s2, "mu": st["mu"], "sigma": st["sigma"], "samples": None}
        else:
            r_ = nv.empirical_policy(p_, c_, s2, st["samples"])
            inp = {"price": p_, "cost": c_, "salvage": s2, "mu": None, "sigma": None, "samples": py(st["samples"])}
        vec.append({"case": f"{model_}_{s_}_c{cr_}_s{sr_}" + ("_default" if (cr_, sr_) == (CR, SR) else ""), "item": s_, "model": model_, "inputs": inp, "expected": py(r_)})
    for s_ in nv_ids:
        for m_ in ("normal", "empirical"):
            addvec(s_, CR, SR, m_)
    for s_ in nv_ids[:8]:
        for cr_, sr_ in ((0.4, 0.0), (0.8, 0.4)):
            for m_ in ("normal", "empirical"):
                addvec(s_, cr_, sr_, m_)
    # edge cases
    vec.append({"case": "normal_cf_half", "item": "edge", "model": "normal", "inputs": {"price": 10.0, "cost": 5.0, "salvage": 0.0, "mu": 100.0, "sigma": 20.0, "samples": None}, "expected": py(nv.normal_policy(10.0, 5.0, 0.0, 100.0, 20.0))})
    vec.append({"case": "normal_q_clipped_at_zero", "item": "edge", "model": "normal", "inputs": {"price": 10.0, "cost": 9.5, "salvage": 0.0, "mu": 3.0, "sigma": 5.0, "samples": None}, "expected": py(nv.normal_policy(10.0, 9.5, 0.0, 3.0, 5.0))})
    vec.append({"case": "empirical_small_sample", "item": "edge", "model": "empirical", "inputs": {"price": 10.0, "cost": 4.0, "salvage": 1.0, "mu": None, "sigma": None, "samples": [5, 8, 8, 10, 12, 15, 20, 20, 25, 40]}, "expected": py(nv.empirical_policy(10.0, 4.0, 1.0, [5, 8, 8, 10, 12, 15, 20, 20, 25, 40]))})
    out["newsvendor_vectors"] = {"schema_version": "v1", "tags": {"vectors": SIM}, "tolerance_rel": 1e-6,
        "note": "Parity vectors for the browser implementation of analytics/newsvendor.py. Compare every expected field with relative tolerance 1e-6 (absolute 1e-9 near zero). The browser needs an inverse normal CDF accurate to about 1e-9 (for example Acklam's rational approximation plus one Halley refinement step using erfc). Empirical Q* is the smallest sample with F(d) >= cf, ties by sorted order.",
        "vectors": vec}
    # scenarios
    grid_c, grid_s = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9], [0.0, 0.2, 0.4]
    scen = []
    for s_ in nv_ids:
        st = item_stats[s_]
        for cr_ in grid_c:
            for sr_ in grid_s:
                p_ = st["price"]; c_ = round(p_ * cr_, 6); s2 = round(c_ * sr_, 6)
                rn = nv.normal_policy(p_, c_, s2, st["mu"], st["sigma"]); re_ = nv.empirical_policy(p_, c_, s2, st["samples"])
                mo_ = nv.normal_policy(p_, c_, s2, st["mu"], st["sigma"], q=max(st["mu"], 0.0))
                scen.append({"item": s_, "cost_ratio": cr_, "salvage_ratio": sr_, "critical_fractile": rn["critical_fractile"], "q_normal": rn["q_star"], "q_empirical": re_["q_star"],
                             "profit_normal": rn["expected_profit"], "profit_empirical": re_["expected_profit"], "service_level": rn["service_level"], "mean_order_profit": mo_["expected_profit"],
                             "expected_sales_normal": rn["expected_sales"], "expected_leftover_normal": rn["expected_leftover"], "expected_shortage_normal": rn["expected_shortage"],
                             "expected_sales_empirical": re_["expected_sales"], "expected_leftover_empirical": re_["expected_leftover"], "expected_shortage_empirical": re_["expected_shortage"]})
    # policy check (realised profit over the last 26 origins, best-model forecast +/- backtest sigma)
    per = []; tot_nv = tot_mo = 0.0; wk_eval = 0
    z0 = norm.ppf(nv.fractile(1.0, CR, CR * SR))
    for s_ in nv_ids:
        y = ser_[s_]; st = item_stats[s_]; p_ = st["price"]; c_ = p_ * CR; s2 = c_ * SR
        pn = pm_ = ps = 0.0; ne = 0
        for oi in range(len(origins) - 26, len(origins)):
            o = origins[oi]
            if o + 1 >= N:
                continue
            e1 = err[best][s_][:oi, 0]; e1 = e1[np.isfinite(e1)]
            if len(e1) < 10:
                continue
            fcast = y[o + 1] + err[best][s_][oi, 0]; sg_ = float(np.std(e1, ddof=1))
            q_nv = max(0.0, fcast + sg_ * z0); q_mo = max(0.0, fcast); q_sn = y[o + 1 - 52]
            a_ = y[o + 1]
            pn += nv.realised_profit(p_, c_, s2, q_nv, a_); pm_ += nv.realised_profit(p_, c_, s2, q_mo, a_); ps += nv.realised_profit(p_, c_, s2, q_sn, a_); ne += 1
        per.append({"item": s_, "profit_newsvendor": pn, "profit_mean_order": pm_, "profit_snaive_order": ps}); tot_nv += pn; tot_mo += pm_; wk_eval = max(wk_eval, ne)
    upl = 100 * (tot_nv - tot_mo) / abs(tot_mo)
    out["newsvendor_scenarios"] = {"schema_version": "v1", "tags": {"grid": SIM, "scenarios": SIM, "policy_check": SIM}, "grid": {"cost_ratio": grid_c, "salvage_ratio": grid_s}, "scenarios": scen,
        "policy_check": {"description": f"Rolling replay on real weekly demand: each of the last {wk_eval} weeks, order Q = forecast + sigma * z(cf) (newsvendor) versus Q = forecast (mean order) and Q = last year's week (seasonal-naive order); realised profit uses actual units sold. Forecast = {best} backtest forecast; sigma = std of its earlier one-step errors. Costs are the SIMULATED defaults (cost 0.60, salvage 0.20 of cost).",
                         "items": len(nv_ids), "weeks_evaluated": wk_eval, "profit_newsvendor": tot_nv, "profit_mean_order": tot_mo, "uplift_pct": upl, "per_item": per,
                         "caveat": "Demand is realised sales (units shipped), which understates true demand when stock ran out; costs are assumed; there is no carry-over inventory or lead time. Uplift is measured in assumed-GBP and can be negative."}}
    F("nv_cost_ratio", CR, "share of price", SIM); F("nv_salvage_ratio", SR, "share of cost", SIM); F("nv_critical_fractile", nv.fractile(1.0, CR, CR * SR), "probability", SIM)
    F("nv_items", len(nv_ids), "items", SIM); F("nv_vectors", len(vec), "cases", SIM); F("nv_policy_profit_uplift_pct", upl, "percent", SIM, "Replay on real demand with assumed costs.")

    # ------------------------------------------------------------ elasticity
    ev_ = el.evidence(); considered, qual = ev_["considered"], ev_["qualifying"]
    ident = el.identification(qual["sku"].to_list())
    s1 = qual.height >= el.MIN_SKUS
    c_a = ident["within_week_variance_share"] <= el.STAGE2_MAX_WITHIN_WEEK_SHARE
    c_b = abs(ident["median_qty_price_spearman"]) <= el.STAGE2_MAX_ABS_CORR
    estimable = bool(s1 and c_a and c_b)
    tbl = qual.sort("units", descending=True).head(60)
    lv2 = [0.1, 0.25, 0.5, 0.75, 0.9]
    out["elasticity"] = {"schema_version": "v1", "tags": {"decision": DER, "evidence": OBS}, "decision": {
        "estimable": estimable,
        "text": ("Price elasticity is NOT estimated. Unit prices vary a lot, but mostly between buyers and by order size inside the same week, not over time. "
                 "A regression of units on price would measure the quantity-discount schedule, not how demand responds to price.") if not estimable else "Estimable.",
        "rule": "Stage 1: at least 30 SKUs with >= 26 selling weeks, <= 90% of weeks at the modal weekly price and >= 3 price regimes. Stage 2 (added after Stage 1 was computed, disclosed): within-SKU-week share of log-price variance <= 25% and |median Spearman(quantity, price) within multi-price SKU-weeks| <= 0.2. Both stages must pass.",
        "criteria": [
            {"id": "stage1_skus", "text": "SKUs qualifying on price variation (Stage 1)", "threshold": el.MIN_SKUS, "observed": qual.height, "pass": bool(s1)},
            {"id": "stage2_within_week_share", "text": "Share of within-SKU log-price variance that is within a single SKU-week (must be at most this)", "threshold": el.STAGE2_MAX_WITHIN_WEEK_SHARE, "observed": ident["within_week_variance_share"], "pass": bool(c_a)},
            {"id": "stage2_qty_price_corr", "text": "Median |Spearman(quantity, price)| inside multi-price SKU-weeks (must be at most this)", "threshold": el.STAGE2_MAX_ABS_CORR, "observed": abs(ident["median_qty_price_spearman"]), "pass": bool(c_b)}]},
        "evidence": {"skus_considered": considered.height, "skus_qualifying": qual.height, "price_rows": int(ev_["weekly"].height),
            "table": [{"sku": r["sku"], "description": (r["description"] or "").title(), "weeks_sold": r["weeks_sold"], "distinct_prices": r["distinct_prices"], "modal_price_gbp": r["modal_price_gbp"],
                       "modal_price_share": r["modal_price_share"], "price_cv": r["price_cv"], "weeks_off_modal": r["weeks_off_modal"], "price_regimes": r["price_regimes"], "units": r["units"]} for r in tbl.iter_rows(named=True)],
            "distribution": {"distinct_prices_quantiles": py(np.quantile(considered["distinct_prices"].to_numpy(), lv2)), "price_cv_quantiles": py(np.quantile(considered["price_cv"].to_numpy(), lv2)), "quantile_levels": lv2},
            "price_tiers_note": f"{100 * ident['sku_weeks_multi_price_share']:.0f}% of SKU-weeks (qualifying SKUs) show more than one unit price; {100 * ident['within_week_variance_share']:.0f}% of log-price variance sits inside a single SKU-week; "
                                f"in the {ident['sku_weeks_tested']:,} multi-price SKU-weeks with at least 5 lines the median Spearman correlation between line quantity and unit price is {ident['median_qty_price_spearman']:.2f}, "
                                f"and {100 * ident['share_corr_below_minus_0_2']:.0f}% of them are below -0.2. That is the signature of quantity-discount tiers.",
            "stage2": ident},
        "estimates": None,
        "what_would_be_needed": ["Dated list-price changes per SKU (a price history), separate from customer-specific or quantity-tier prices.",
                                 "Price changes that are not driven by order size, for example staggered price tests or promotions with known dates across comparable SKUs.",
                                 "Stock-out and availability data, so that unsold weeks are not read as low demand.",
                                 "Customer-level price tier labels, to compare like with like."]}
    F("elasticity_skus_considered", considered.height, "SKUs", OBS); F("elasticity_skus_qualifying", qual.height, "SKUs", DER); F("elasticity_estimable", 1 if estimable else 0, "boolean", DER)
    F("elasticity_decision", "not estimable: price varies by buyer and order size, not over time" if not estimable else "estimable", "text", DER)

    # ------------------------------------------------------------ meta, strings, facts
    F("title", "Retail Intelligence Studio", "text", OBS); F("attribution", ATTRIBUTION, "text", OBS); F("licence", "CC BY 4.0", "text", OBS)
    F("window_label", "1 Dec 2009 to 9 Dec 2011", "text", OBS); F("currency", "GBP", "text", OBS)
    F("not_advice", "Forecasts, CLV and newsvendor outputs are analytical examples from a 2009-2011 UK gift-ware ledger, not business advice.", "text", DER)
    F("synthetic_note", "No synthetic data is used. No demographics exist in the source and none are inferred.", "text", OBS)
    out["facts"] = {"schema_version": "v1", "tags": {"facts": "OBSERVED/DERIVED/PREDICTED/SIMULATED"}, "facts": facts}
    try:
        dbtv = md.version("dbt-duckdb")
    except Exception:
        dbtv = "unknown"
    out["meta"] = {"schema_version": "v1", "tags": {"source": OBS, "engine": OBS}, "pipeline_version": PIPELINE_VERSION, "retrieved_at": raw_mf["retrieved_at"],
        "source": {"id": "uci_online_retail_ii", "publisher": "UCI Machine Learning Repository", "dataset": "Online Retail II (Daqing Chen, 2012)", "url": URL, "doi": DOI, "licence": "CC BY 4.0",
                   "licence_url": "https://creativecommons.org/licenses/by/4.0/", "attribution": ATTRIBUTION, "role": "Sole data source: every invoice line of a UK online gift-ware wholesaler, 2009-12-01 to 2011-12-09."},
        "window": {"first_ts": str(first_ts)[:19], "last_ts": str(last_ts)[:19], "first_week": ds(weeks[0]), "last_complete_week": ds(weeks[-1]), "weeks_complete": len(weeks)},
        "engine": {"star_schema": "dbt-duckdb (models in dbt/): stg_raw, stg_lines, dim_product, dim_customer, dim_date, dim_country, fact_lines, fact_refund_match", "dbt_version": dbtv,
                   "duckdb_version": duckdb.__version__, "python": platform.python_version(), "seed": SEED},
        "currency": "GBP",
        "assumptions": ["Unit price is GBP (the source describes a UK-registered retailer; there is no currency column).", "Credit notes (invoice prefix C) are refunds; matched LIFO to earlier sales of the same customer and SKU.",
                        "Exact duplicate rows are removed (count published); some may be genuine repeated scans.", "Product families are DERIVED from description keywords; the source has no category.",
                        "Newsvendor cost, salvage and review period are assumptions (SIMULATED).", "CLV is revenue, discounted at an assumed 10% a year, not profit."],
        "disclaimers": [ATTRIBUTION, "Customers are anonymised integer keys; the source Customer IDs are never published.", "Not representative of retail in general: one UK gift-ware wholesaler, 24 months, two Christmas seasons.",
                        "Analytical examples only, not business advice."],
        "no_demographics": "The source contains no demographic fields. None are inferred, imputed or invented.", "artifact_tags": {}, "artifact_bytes": {}}
    out["meta"]["artifact_tags"] = {k: v["tags"] for k, v in out.items() if k != "meta"}
    # validation checks are appended by pipelines.validation (needs written artifacts)
    con.close()
    out["_state"] = {"clv": _clv_state, "best": best}
    return out


def write_all(out: dict) -> dict[str, int]:
    PUBLIC.mkdir(parents=True, exist_ok=True)
    sizes = {}
    for name, obj in out.items():
        if name.startswith("_"):
            continue
        n = write_json(PUBLIC / f"{name}.json", py(obj))
        sizes[name] = len(gzip.compress((PUBLIC / f"{name}.json").read_bytes(), 9))
    return sizes

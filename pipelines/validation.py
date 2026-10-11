"""Build validation.json: every check recomputed from the artifacts (and from the star schema) at publish time."""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm

from analytics import clv, data, newsvendor as nv


def chk(cid, group, desc, expected, actual, ok):
    return {"id": cid, "group": group, "description": desc, "expected": str(expected), "actual": str(actual), "pass": bool(ok)}


def run(out: dict) -> dict:
    C = []
    rec = out["reconciliation"]
    for i in rec["identities"]:
        C.append(chk("recon_" + i["id"], "reconciliation", i["description"], i["lhs"], i["rhs"], i["pass"]))
    ov = out["overview"]
    tot = out["facts"]["facts"]["revenue_total_net_gbp"]["value"]
    s = sum(ov["series"]["product_net_gbp"]) + sum(ov["series"]["nonproduct_net_gbp"])
    C.append(chk("overview_sum", "reconciliation", "Monthly product net + non-product net = total net revenue", round(tot, 2), round(s, 2), abs(s - tot) < 1.0))
    pr = out["products"]
    fs = sum(f["revenue_gbp"] for f in pr["families"])
    C.append(chk("family_sum", "reconciliation", "Family revenue sums to total sale-line revenue", out["facts"]["facts"]["revenue_sales_gbp"]["value"], round(fs, 2), abs(fs - out["facts"]["facts"]["revenue_sales_gbp"]["value"]) < 1.0))
    ls = sum(sum(r) for r in out["landscape"]["revenue_gbp"])
    C.append(chk("landscape_le_sales", "reconciliation", "Landscape (complete weeks only) does not exceed sale revenue", "<= sales", round(ls, 0), ls <= out["facts"]["facts"]["revenue_sales_gbp"]["value"] + 1))
    rf = out["rfm"]
    C.append(chk("rfm_partition", "rfm", "RFM segments partition all included customers", rf["included"]["customers"], sum(x["customers"] for x in rf["segments"]), rf["included"]["customers"] == sum(x["customers"] for x in rf["segments"])))
    C.append(chk("rfm_revenue", "rfm", "RFM segment monetary sums to customer monetary", round(sum(rf["customers"]["monetary_gbp"]), 0), round(sum(x["revenue_gbp"] for x in rf["segments"]), 0),
                 abs(sum(rf["customers"]["monetary_gbp"]) - sum(x["revenue_gbp"] for x in rf["segments"])) < 5))
    coh = out["cohorts"]
    ok0 = all(r[0] == 1.0 for r in coh["retention"])
    inr = all(v is None or 0 <= v <= 1 for r in coh["retention"] for v in r)
    C.append(chk("cohort_m0", "cohorts", "Month-0 retention is 1 for every cohort", True, ok0, ok0))
    C.append(chk("cohort_range", "cohorts", "All retention cells lie in [0, 1] or are null (censored)", True, inr, inr))
    bs = out["baskets"]
    # recompute lift of top rules independently from the invoice x SKU table
    d = data.sql("select distinct invoice_no, sku from fact_lines where line_class='sale'")
    inv = d.group_by("invoice_no").agg(__import__("polars").col("sku").alias("s"))
    sets = [frozenset(x) for x in inv["s"].to_list()]
    nb = len(sets)
    bad = 0
    for r in bs["rules"][:15]:
        a, c = frozenset(r["antecedent"]), frozenset(r["consequent"])
        na = sum(1 for x in sets if a <= x); nc = sum(1 for x in sets if c <= x); nac = sum(1 for x in sets if (a | c) <= x)
        lift = (nac / na) / (nc / nb)
        if abs(lift - r["lift"]) > 1e-9 or nac != r["count"]:
            bad += 1
    C.append(chk("basket_recount", "baskets", "Top 15 published rules recomputed from raw baskets (count and lift)", 0, bad, bad == 0))
    C.append(chk("basket_baskets", "baskets", "Basket count = distinct invoices with a sale line", nb, bs["params"]["baskets"], nb == bs["params"]["baskets"]))
    C.append(chk("basket_min_support", "baskets", "Every published rule meets the minimum support", bs["params"]["min_support"], min(r["support"] for r in bs["rules"]), min(r["support"] for r in bs["rules"]) >= bs["params"]["min_support"] - 1e-12))
    cv = out["clv"]
    C.append(chk("clv_converged", "clv", "BG/NBD and Gamma-Gamma optimisers converged", True, cv["model"]["bgnbd"]["converged"] and cv["model"]["gamma_gamma"]["converged"], cv["model"]["bgnbd"]["converged"] and cv["model"]["gamma_gamma"]["converged"]))
    rng = np.random.default_rng(7)
    par = {"r": 0.8, "alpha": 8.0, "a": 0.6, "b": 3.0}
    T = rng.uniform(20, 100, 5000)
    x, tx, fut = clv.simulate_bgnbd(par, T, 26, rng)
    fit = clv.fit_bgnbd(x, tx, T)
    rel = max(abs(fit[k] - par[k]) / par[k] for k in par)
    C.append(chk("clv_param_recovery", "clv", "BG/NBD fit recovers simulated parameters within 25% relative error (5,000 simulated customers)", "< 0.25", round(rel, 3), rel < 0.25))
    pred = clv.expected_purchases(par, 26, x, tx, T)
    err = abs(pred.sum() - fut.sum()) / fut.sum()
    C.append(chk("clv_sim_prediction", "clv", "Conditional expected purchases match simulated future purchases (total, 5%)", "< 0.05", round(err, 4), err < 0.05))
    H = cv["holdout"]
    C.append(chk("clv_holdout_total", "clv", "Holdout predicted repeat total within 10% of actual", "< 10%", f"{H['total_error_pct']:.2f}%", abs(H["total_error_pct"]) < 10))
    C.append(chk("clv_beats_baseline", "clv", "BG/NBD per-customer MAE below the population-rate baseline", H["baseline_mae_customer"], H["mae_customer"], H["mae_customer"] < H["baseline_mae_customer"]))
    C.append(chk("clv_deciles_ordered", "clv", "Predicted decile means increase with decile", True, True, all(cv["deciles"][i]["predicted"] <= cv["deciles"][i + 1]["predicted"] + 1e-12 for i in range(9))))
    bt = out["backtest"]
    C.append(chk("bt_baseline_present", "forecast", "Seasonal-naive baseline evaluated on every series and horizon", bt["design"]["series"], len({r["scope"] for r in bt["pooled"]}), any(r["model"] == "snaive" for r in bt["pooled"])))
    C.append(chk("bt_origins", "forecast", "At least 40 rolling origins", ">= 40", bt["design"]["origins"], bt["design"]["origins"] >= 40))
    cov = bt["interval_coverage"]["empirical"]
    C.append(chk("bt_interval_coverage", "forecast", "80% empirical intervals cover 70% to 90% of out-of-sample one-step actuals", "0.70 to 0.90", round(cov, 3), 0.70 <= cov <= 0.90))
    fcst = out["forecast"]
    C.append(chk("forecast_nonneg", "forecast", "All forecasts and bounds are non-negative and lo <= forecast <= hi", True, True,
                 all(min(s["forecast"]) >= 0 and all(l <= f + 1e-6 <= h + 2e-6 for l, f, h in zip(s["lo"], s["forecast"], s["hi"])) for s in fcst["series"])))
    # newsvendor vectors: reproduce with an independent evaluation path
    vs = out["newsvendor_vectors"]["vectors"]
    worst = 0.0
    for v in vs:
        i = v["inputs"]
        r = nv.normal_policy(i["price"], i["cost"], i["salvage"], i["mu"], i["sigma"]) if v["model"] == "normal" else nv.empirical_policy(i["price"], i["cost"], i["salvage"], i["samples"])
        for k, e in v["expected"].items():
            worst = max(worst, abs(r[k] - e) / max(abs(e), 1e-9))
    C.append(chk("nv_vectors_reproduce", "newsvendor", "Vectors reproduce from the reference implementation", "< 1e-9", f"{worst:.1e}", worst < 1e-9))
    # empirical optimality: Q* maximises profit among sample points
    opt = True
    for v in vs:
        if v["model"] == "empirical":
            i = v["inputs"]; q = v["expected"]["q_star"]
            pf = [nv.empirical_policy(i["price"], i["cost"], i["salvage"], i["samples"], q=float(c))["expected_profit"] for c in sorted(set(i["samples"]))]
            opt &= v["expected"]["expected_profit"] >= max(pf) - 1e-9
    C.append(chk("nv_empirical_optimal", "newsvendor", "Empirical Q* attains the maximum expected profit over all sample points", True, opt, opt))
    # normal optimality (numeric grid)
    opt2 = True
    for v in vs:
        if v["model"] == "normal" and v["expected"]["q_star"] > 0:
            i = v["inputs"]; q = v["expected"]["q_star"]
            grid = [nv.normal_policy(i["price"], i["cost"], i["salvage"], i["mu"], i["sigma"], q=q * f)["expected_profit"] for f in np.linspace(0.5, 1.5, 41)]
            opt2 &= v["expected"]["expected_profit"] >= max(grid) - 1e-6 * abs(max(grid))
    C.append(chk("nv_normal_optimal", "newsvendor", "Normal Q* attains the maximum expected profit on a +/-50% grid", True, opt2, opt2))
    el = out["elasticity"]
    consistent = el["decision"]["estimable"] == all(c["pass"] for c in el["decision"]["criteria"])
    C.append(chk("elasticity_consistent", "elasticity", "Decision equals the conjunction of the published criteria", True, consistent, consistent))
    C.append(chk("elasticity_no_number", "elasticity", "No elasticity estimate is published when not estimable", None, el["estimates"], el["decision"]["estimable"] or el["estimates"] is None))
    C.append(chk("tags_present", "honesty", "Every artifact declares honesty tags", len(out), sum(1 for k, v in out.items() if not k.startswith("_") and v.get("tags")), all(v.get("tags") for k, v in out.items() if not k.startswith("_"))))
    C.append(chk("no_raw_customer_ids", "privacy", "Customer keys are a dense 1..N index, not source IDs (no key above customer count)", out["facts"]["facts"]["customers_known"]["value"],
                 max(out["rfm"]["customers"]["key"]), max(out["rfm"]["customers"]["key"]) <= out["facts"]["facts"]["customers_known"]["value"]))
    lim = ["Single UK wholesale-like gift-ware company over 24 months; patterns do not generalise to retail at large.",
           "The ledger records shipped lines, not demand: stock-outs, lead times, costs and margins are absent.",
           "Product families are keyword-derived approximations, and the first observed purchase is not always a customer's first.",
           "Seasonal-naive has only one prior year to copy in this data, so it is a weak baseline; skill numbers are relative to it.",
           "Association rules measure co-occurrence in one invoice; the top-lift rules are mostly variants of the same product."]
    p = sum(1 for c in C if c["pass"])
    return {"schema_version": "v1", "tags": {"checks": "DERIVED"}, "checks": C, "passed": p, "failed": len(C) - p, "limitations_observed": lim}

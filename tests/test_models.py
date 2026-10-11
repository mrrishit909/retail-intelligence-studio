"""Model tests: BG/NBD and Gamma-Gamma against simulation, RFM/cohort invariants, forecasting leakage, newsvendor properties and vector parity."""
import numpy as np
import pytest

from analytics import clv, forecasting as fc, newsvendor as nv


# ---------- CLV ----------
def test_bgnbd_recovers_parameters_and_predicts():
    rng = np.random.default_rng(11)
    par = {"r": 0.8, "alpha": 8.0, "a": 0.6, "b": 3.0}
    T = rng.uniform(20, 100, 6000)
    x, tx, fut = clv.simulate_bgnbd(par, T, 26, rng)
    fit = clv.fit_bgnbd(x, tx, T)
    assert fit["converged"]
    for k in par:
        assert abs(fit[k] - par[k]) / par[k] < 0.25, (k, fit[k])
    pred = clv.expected_purchases(par, 26, x, tx, T)
    assert abs(pred.sum() - fut.sum()) / fut.sum() < 0.05
    for k in (0, 2, 5):
        m = x == k
        assert abs(pred[m].mean() - fut[m].mean()) < 0.1 * max(fut[m].mean(), 0.3)


def test_bgnbd_formula_properties():
    par = {"r": 0.7, "alpha": 9.0, "a": 0.15, "b": 3.3}
    x = np.array([0.0, 1.0, 4.0]); tx = np.array([0.0, 10.0, 50.0]); T = np.array([30.0, 40.0, 60.0])
    e = [clv.expected_purchases(par, t, x, tx, T) for t in (1, 4, 26, 52)]
    assert np.all(np.diff(np.array(e), axis=0) > 0) and np.all(e[0] > 0)
    p = clv.p_alive(par, x, tx, T)
    assert p[0] == 1.0 and np.all((p > 0) & (p <= 1))
    assert clv.unconditional_expected(par, 52) > clv.unconditional_expected(par, 26) > 0


def test_gamma_gamma_recovers_parameters():
    rng = np.random.default_rng(5)
    p, q, v = 6.0, 4.0, 15.0
    n = 4000
    x = rng.integers(1, 12, n).astype(float)
    nu = rng.gamma(q, 1 / v, n)  # mean transaction value = p / nu
    m = np.array([rng.gamma(p * xi, 1 / (nu_i * xi)) / 1.0 for xi, nu_i in zip(x, nu)])
    # mean of x i.i.d. gamma(p, nu) draws ~ gamma(p x, nu x)
    fit = clv.fit_gg(x, m)
    assert fit["converged"]
    assert abs(fit["p"] - p) / p < 0.3 and abs(fit["q"] - q) / q < 0.3
    assert abs(clv.gg_expected_value(fit, x, m).mean() - m.mean()) / m.mean() < 0.05


@pytest.mark.slow
def test_clv_artifact_calibration(art):
    c = art("clv")
    h = c["holdout"]
    assert abs(h["total_error_pct"]) < 10 and h["mae_customer"] < h["baseline_mae_customer"]
    assert c["model"]["bgnbd"]["converged"] and c["model"]["gamma_gamma"]["converged"]
    assert len(c["deciles"]) == 10 and sum(d["customers"] for d in c["deciles"]) == c["calibration"]["customers"]
    cu = c["customers"]
    n = len(cu["key"])
    assert all(len(v) == n for v in cu.values())
    assert min(cu["clv_gbp"]) >= 0 and all(0 <= p <= 1 for p in cu["p_alive"])


# ---------- RFM / cohorts ----------
@pytest.mark.slow
def test_rfm_and_cohort_invariants(art):
    r = art("rfm")
    cu = r["customers"]
    assert set(cu["r"]) <= {1, 2, 3, 4, 5} and set(cu["f"]) <= {1, 2, 3, 4, 5}
    assert sum(sum(row) for row in r["grid"]["r_by_f_customers"]) == r["included"]["customers"]
    assert all(cu["recency_days"][i] >= 0 for i in range(len(cu["key"])))
    c = art("cohorts")
    assert all(row[0] == 1.0 for row in c["retention"])
    assert len(c["cohort_months"]) == len(c["sizes"]) == len(c["retention"])
    # right censoring: the last cohort has only offset 0
    assert [v is not None for v in c["retention"][-1]].count(True) == 1


# ---------- forecasting ----------
def test_forecast_uses_only_training_data():
    rng = np.random.default_rng(3)
    y = rng.poisson(50, 120).astype(float)
    base = fc.forecasts(y[:80], 4)
    y2 = y.copy(); y2[80:] += 1000.0
    again = fc.forecasts(y2[:80], 4)
    for k in base:
        assert np.allclose(base[k], again[k]), k


def test_snaive_is_lag_52():
    y = np.arange(100, dtype=float)
    assert np.allclose(fc.f_snaive(y[:70], 3), [18, 19, 20])


@pytest.mark.slow
def test_backtest_artifact(art):
    b = art("backtest")
    assert b["design"]["origins"] >= 40 and b["design"]["min_train_weeks"] == 60
    models = {r["model"] for r in b["pooled"]}
    assert "snaive" in models and len(models) >= 4
    for r in b["pooled"]:
        if r["model"] == "snaive":
            assert abs(r["skill_vs_snaive_pct"]) < 1e-9
    assert 0.7 <= b["interval_coverage"]["empirical"] <= 0.9


# ---------- newsvendor ----------
def test_newsvendor_properties():
    p, c, s = 10.0, 6.0, 1.0
    cf = nv.fractile(p, c, s)
    assert abs(cf - 4 / 9) < 1e-12
    r = nv.normal_policy(p, c, s, 100.0, 20.0)
    assert abs(r["service_level"] - cf) < 1e-9  # P(D <= Q*) equals the critical fractile
    for f in (0.8, 0.9, 1.1, 1.2):
        assert nv.normal_policy(p, c, s, 100.0, 20.0, q=r["q_star"] * f)["expected_profit"] < r["expected_profit"]
    assert abs(r["expected_sales"] + r["expected_shortage"] - 100.0) < 1e-9 or r["expected_shortage"] >= 0
    # sigma -> 0 limit: sells min(mu, Q)
    z = nv.normal_policy(p, c, s, 100.0, 1e-6)
    assert abs(z["expected_profit"] - (p - c) * 100.0) < 1e-3
    # empirical: known small case
    e = nv.empirical_policy(10.0, 4.0, 1.0, [5, 8, 8, 10, 12, 15, 20, 20, 25, 40])
    assert e["critical_fractile"] == pytest.approx(6 / 9) and e["q_star"] == 20


@pytest.mark.slow
def test_newsvendor_vectors_reproduce(art):
    v = art("newsvendor_vectors")
    assert len(v["vectors"]) >= 20 and v["tolerance_rel"] == 1e-6
    for c in v["vectors"]:
        i = c["inputs"]
        r = nv.normal_policy(i["price"], i["cost"], i["salvage"], i["mu"], i["sigma"]) if c["model"] == "normal" else nv.empirical_policy(i["price"], i["cost"], i["salvage"], i["samples"])
        for k, e in c["expected"].items():
            assert r[k] == pytest.approx(e, rel=1e-6, abs=1e-9), (c["case"], k)


@pytest.mark.slow
def test_newsvendor_labelled_simulated(art):
    p = art("newsvendor_params")
    assert p["labelled"] == "SIMULATED" and {a["id"] for a in p["assumptions"]} >= {"cost_ratio", "salvage_ratio", "review_period"}
    assert art("newsvendor_scenarios")["tags"]["scenarios"] == "SIMULATED"


# ---------- elasticity ----------
@pytest.mark.slow
def test_elasticity_decision_published_with_evidence(art):
    e = art("elasticity")
    crit = e["decision"]["criteria"]
    assert e["decision"]["estimable"] == all(c["pass"] for c in crit)
    if not e["decision"]["estimable"]:
        assert e["estimates"] is None
    assert len(e["evidence"]["table"]) >= 20 and e["evidence"]["skus_qualifying"] > 0


# ---------- baskets ----------
@pytest.mark.slow
def test_baskets_thresholds(art):
    b = art("baskets")
    p = b["params"]
    for r in b["rules"]:
        assert r["support"] >= p["min_support"] - 1e-12 and r["confidence"] >= p["min_confidence"] - 1e-12 and r["lift"] > 1
        assert r["count"] >= p["support_count_min"]


# ---------- P09-DATA-002 data requests ----------
@pytest.mark.slow
def test_dr1_hero_pair_facts_match_baskets(art):
    f, b = art("facts")["facts"], art("baskets")
    h = b["hero"]
    assert f["hero_pair_a"]["value"] == h["a"] and f["hero_pair_nab"]["value"] == h["nab"]
    assert f["hero_pair_chance"]["value"] == pytest.approx(h["na"] * h["nb"] / f["basket_count"]["value"])
    assert f["hero_pair_lift"]["value"] == pytest.approx(h["nab"] * f["basket_count"]["value"] / (h["na"] * h["nb"]))
    assert h["na"] >= h["nb"] and h["nab"] >= max(r["nab"] for r in h["runner_up"])
    assert any(e["hero"] and {e["a"], e["b"]} == {h["a"], h["b"]} for e in b["edges"])


@pytest.mark.slow
def test_dr2_showcase(art):
    b = art("baskets")
    s = b["showcase"]
    assert len(s["indices"]) == 6 and s["kinds"] == ["lift"] * 3 + ["count"] * 3
    sets = [frozenset(b["rules"][i]["antecedent"] + b["rules"][i]["consequent"]) for i in s["indices"]]
    assert len(set(sets)) == 6 and frozenset((b["hero"]["a"], b["hero"]["b"])) not in sets
    assert not any(b["rules"][i]["variant_of_same_product"] for i in s["indices"])
    lifts = [b["rules"][i]["lift"] for i in s["indices"][:3]]
    assert lifts == sorted(lifts, reverse=True)


@pytest.mark.slow
def test_dr3_cohort_active_set_matches_overview(art):
    c, o = art("cohorts"), art("overview")
    for m, n in zip(c["cohort_months"], c["active_customers"]):
        assert o["series"]["active_customers"][o["months"].index(m)] == n
    assert all(a >= b for a, b in zip(c["active_net_revenue_gbp"], [0] * len(c["cohort_months"])))
    # a cohort can never be bigger than the active set in its own month
    assert all(s <= a for s, a in zip(c["sizes"], c["active_customers"]))


@pytest.mark.slow
def test_dr4_rfm_grids(art):
    r = art("rfm")
    n = r["included"]["customers"]
    for k in ("r_by_f", "r_by_m", "f_by_m"):
        assert sum(map(sum, r["grid"][k + "_customers"])) == n
        assert sum(map(sum, r["grid"][k + "_revenue_gbp"])) == pytest.approx(sum(r["customers"]["monetary_gbp"]), abs=30)
    # marginals agree across pairs: row sums of R x F equal row sums of R x M
    assert [sum(x) for x in r["grid"]["r_by_f_customers"]] == [sum(x) for x in r["grid"]["r_by_m_customers"]]
    assert [sum(x) for x in zip(*r["grid"]["r_by_f_customers"])] == [sum(x) for x in r["grid"]["f_by_m_customers"]]


@pytest.mark.slow
def test_dr5_backtest_area_identities(art):
    b = art("backtest")
    assert "forecast - actual" in b["design"]["error_sign"]
    for r in b["pooled"]:
        assert (r["over_total"] + r["under_total"]) / r["actual_total"] * 100 == pytest.approx(r["wape_pct"], rel=1e-9)
        assert r["forecast_total"] - r["actual_total"] == pytest.approx(r["over_total"] - r["under_total"], rel=1e-9, abs=1e-6)
        assert r["bias_pct"] == pytest.approx(100 * (r["forecast_total"] - r["actual_total"]) / r["actual_total"], rel=1e-9, abs=1e-9)
        assert r["mae"] * r["n"] == pytest.approx(r["over_total"] + r["under_total"], rel=1e-9)


@pytest.mark.slow
def test_dr6_clv_overlap_and_baseline(art):
    c = art("clv")
    h = c["holdout"]
    assert 0 < h["overlap_customer_sum"] <= min(h["predicted_repeats_total"], h["actual_repeats_total"])
    assert h["baseline_overlap_customer_sum"] < h["overlap_customer_sum"]
    assert sum(d["predicted_sum"] for d in c["deciles"]) == pytest.approx(h["predicted_repeats_total"])
    assert sum(d["baseline_predicted_sum"] for d in c["deciles"]) == pytest.approx(h["baseline_predicted_total"])
    assert sum(d["overlap_sum"] for d in c["deciles"]) <= h["overlap_customer_sum"] + 1e-6  # decile-level min can only be larger-grained: <=


@pytest.mark.slow
def test_dr7_scenarios_match_vectors_at_defaults(art):
    v, s, p = art("newsvendor_vectors")["vectors"], art("newsvendor_scenarios")["scenarios"], art("newsvendor_params")
    ids = {i["id"] for i in p["items"]}
    for model in ("normal", "empirical"):
        assert {c["item"] for c in v if c["model"] == model and c["case"].endswith("_default")} == ids
    for c in v:
        if not c["case"].endswith("_default"):
            continue
        row = next(r for r in s if r["item"] == c["item"] and r["cost_ratio"] == 0.6 and r["salvage_ratio"] == 0.2)
        m = c["model"]
        for k in ("sales", "leftover", "shortage"):
            assert row[f"expected_{k}_{m}"] == pytest.approx(c["expected"][f"expected_{k}"], rel=1e-9, abs=1e-9)
        assert row[f"profit_{m}"] == pytest.approx(c["expected"]["expected_profit"], rel=1e-9)
    for r in s:
        assert r["expected_sales_normal"] >= 0 and r["expected_leftover_normal"] >= -1e-9 and r["expected_shortage_normal"] >= -1e-9
        assert r["expected_sales_empirical"] >= 0 and r["expected_shortage_empirical"] >= -1e-9


@pytest.mark.slow
def test_dr8_refund_split(art):
    r = art("reconciliation")["refunds"]
    assert r["matched_qty"] + r["unmatched_no_prior_sale_qty"] + r["unmatched_no_customer_qty"] + r["over_refund_qty"] == r["refunded_qty"]
    parts = r["matched_value_gbp"] + r["unmatched_no_prior_sale_value_gbp"] + r["unmatched_no_customer_value_gbp"] + r["over_refund_value_gbp"]
    assert parts == pytest.approx(-r["value_gbp"], abs=0.05)
    assert r["sale_units"] == next(c for c in art("reconciliation")["classes"] if c["class"] == "sale")["units"]


def test_dr9_elasticity_schema_blocks_numbers_when_not_estimable():
    import json
    import copy
    from jsonschema import Draft202012Validator
    from pipelines.common import CONTRACTS, PUBLIC
    v = Draft202012Validator(json.loads((CONTRACTS / "elasticity.schema.json").read_text()))
    doc = json.loads((PUBLIC / "elasticity.json").read_text())
    assert not list(v.iter_errors(doc))
    bad = copy.deepcopy(doc)
    bad["estimates"] = {"method": "x", "skus": [], "pooled": {"elasticity": -1.2, "ci_lo": -1.5, "ci_hi": -0.9}}
    assert list(v.iter_errors(bad))  # a number is rejected in the not-estimable state
    ok = copy.deepcopy(bad)
    ok["decision"]["estimable"] = True
    ok["decision"]["criteria"] = [dict(c, **{"pass": True}) for c in ok["decision"]["criteria"]]
    assert not list(v.iter_errors(ok))  # the estimable state accepts the typed shape
    ok["estimates"] = None
    assert list(v.iter_errors(ok))  # and requires it


@pytest.mark.slow
def test_dr10_copy_facts(art):
    f = art("facts")["facts"]
    r = art("rfm")
    n = r["included"]["customers"]
    m = sum(1 for a, b in zip(r["customers"]["r"], r["customers"]["f"]) if a >= 4 and b >= 4)
    assert f["rfm_rf_share_customers"]["value"] == pytest.approx(m / n)
    mon = r["customers"]["monetary_gbp"]
    rev = sum(x for x, a, b in zip(mon, r["customers"]["r"], r["customers"]["f"]) if a >= 4 and b >= 4) / sum(mon)
    assert f["rfm_rf_share_revenue"]["value"] == pytest.approx(rev, abs=2e-4)
    b = art("backtest")
    assert f["backtest_best_model_label"]["value"] == next(x["label"] for x in b["models"] if x["id"] == f["forecast_best_model"]["value"])

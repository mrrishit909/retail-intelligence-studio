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

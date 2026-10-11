"""BG/NBD (Fader, Hardie and Lee 2005) and Gamma-Gamma (Fader and Hardie 2013), own implementation in numpy/scipy.

Units: weeks. Transaction = distinct purchase day of a customer (same-day invoices merged); value = GBP of sale lines that day.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl
from scipy import optimize
from scipy.special import gammaln, hyp2f1

from analytics import data

CAL_END = dt.date(2011, 6, 9)
HOLD_START = dt.date(2011, 6, 10)
HOLD_END = dt.date(2011, 12, 9)
FINAL_END = dt.date(2011, 12, 9)


# ---------------- BG/NBD ----------------
def bgnbd_ll(params, x, tx, T):
    r, alpha, a, b = np.exp(params)
    a1 = gammaln(r + x) - gammaln(r) + r * np.log(alpha)
    a2 = gammaln(a + b) + gammaln(b + x) - gammaln(b) - gammaln(a + b + x)
    a3 = -(r + x) * np.log(alpha + T)
    a4 = np.log(a) - np.log(np.maximum(b + x - 1, 1e-12)) - (r + x) * np.log(alpha + tx)
    m = np.maximum(a3, np.where(x > 0, a4, -np.inf))
    ll = a1 + a2 + m + np.log(np.exp(a3 - m) + np.where(x > 0, np.exp(a4 - m), 0.0))
    return ll


def fit_bgnbd(x, tx, T, penalizer=0.0):
    f = lambda p: -bgnbd_ll(p, x, tx, T).sum() + penalizer * (np.exp(p) ** 2).sum()  # noqa: E731
    best = None
    for p0 in ([0.0, 0.0, 0.0, 0.0], [-1.0, 1.0, 0.5, 1.0], [0.3, 2.0, -0.5, 0.0]):
        res = optimize.minimize(f, np.array(p0), method="L-BFGS-B", bounds=[(-8, 8)] * 4)
        if best is None or res.fun < best.fun:
            best = res
    r, alpha, a, b = np.exp(best.x)
    return {"r": float(r), "alpha": float(alpha), "a": float(a), "b": float(b), "loglik": float(-best.fun), "converged": bool(best.success)}


def p_alive(par, x, tx, T):
    r, alpha, a, b = par["r"], par["alpha"], par["a"], par["b"]
    ratio = np.where(x > 0, a / np.maximum(b + x - 1, 1e-12) * ((alpha + T) / (alpha + tx)) ** (r + x), 0.0)
    return 1.0 / (1.0 + ratio)


def expected_purchases(par, t, x, tx, T):
    """E[Y(t) | x, t_x, T]: expected purchases in the next t weeks (requires a > 1)."""
    r, alpha, a, b = par["r"], par["alpha"], par["a"], par["b"]
    t = np.asarray(t, dtype=float)
    hyp = hyp2f1(r + x, b + x, a + b + x - 1, t / (alpha + T + t))
    num = (a + b + x - 1) / (a - 1) * (1 - ((alpha + T) / (alpha + T + t)) ** (r + x) * hyp)
    den = 1 + np.where(x > 0, a / np.maximum(b + x - 1, 1e-12) * ((alpha + T) / (alpha + tx)) ** (r + x), 0.0)
    return num / den


def unconditional_expected(par, t):
    r, alpha, a, b = par["r"], par["alpha"], par["a"], par["b"]
    return (a + b - 1) / (a - 1) * (1 - (alpha / (alpha + t)) ** r * hyp2f1(r, b, a + b - 1, t / (alpha + t)))


def simulate_bgnbd(par, T, H, rng):
    """Draw len(T) customers from the BG/NBD process. Returns x, tx (observed in [0, T]) and future purchase counts in (T, T+H]."""
    T = np.asarray(T, dtype=float)
    n = len(T)
    lam = rng.gamma(par["r"], 1 / par["alpha"], n)
    p = rng.beta(par["a"], par["b"], n)
    xs, txs, fut = np.zeros(n), np.zeros(n), np.zeros(n)
    for i in range(n):
        t, x, tx, alive = 0.0, 0, 0.0, True
        while alive:
            t += rng.exponential(1 / lam[i])
            if t > T[i] + H:
                break
            if t <= T[i]:
                x += 1; tx = t
            else:
                fut[i] += 1
            if rng.random() < p[i]:
                alive = False
        xs[i], txs[i] = x, tx
    return xs, txs, fut


# ---------------- Gamma-Gamma ----------------
def gg_ll(params, x, m):
    p, q, v = np.exp(params)
    px = p * x
    return gammaln(px + q) - gammaln(px) - gammaln(q) + q * np.log(v) + (px - 1) * np.log(m) + px * np.log(x) - (px + q) * np.log(v + m * x)


def fit_gg(x, m):
    f = lambda p: -gg_ll(p, x, m).sum()  # noqa: E731
    best = None
    for p0 in ([0.0, 1.0, 3.0], [1.0, 1.5, 4.0]):
        res = optimize.minimize(f, np.array(p0), method="L-BFGS-B", bounds=[(-6, 8)] * 3)
        if best is None or res.fun < best.fun:
            best = res
    p, q, v = np.exp(best.x)
    return {"p": float(p), "q": float(q), "v": float(v), "loglik": float(-best.fun), "converged": bool(best.success)}


def gg_expected_value(par, x, m):
    p, q, v = par["p"], par["q"], par["v"]
    return p * (v + x * m) / (p * x + q - 1)


# ---------------- data ----------------
def transactions() -> pl.DataFrame:
    s = data.sales(customers_only=True)
    t = s.group_by("customer_key", "day").agg(pl.col("amount").sum().alias("value"))
    return t.filter(pl.col("value") > 0).sort("customer_key", "day")


def rfm_frame(tx: pl.DataFrame, end: dt.date) -> pl.DataFrame:
    t = tx.filter(pl.col("day") <= end)
    g = t.group_by("customer_key").agg(pl.col("day").min().alias("first"), pl.col("day").max().alias("last"), pl.len().alias("n"),
                                       pl.col("value").sum().alias("total"))
    # value of repeat transactions only = total minus value of the first transaction day
    firstv = t.join(g.select("customer_key", pl.col("first").alias("day")), on=["customer_key", "day"]).select("customer_key", pl.col("value").alias("first_value"))
    g = g.join(firstv, on="customer_key").with_columns(
        (pl.col("n") - 1).alias("x"),
        ((pl.col("last") - pl.col("first")).dt.total_days() / 7.0).alias("tx"),
        ((pl.lit(end) - pl.col("first")).dt.total_days() / 7.0).alias("T"),
        ((pl.col("total") - pl.col("first_value")) / (pl.col("n") - 1)).alias("m"))
    return g.sort("customer_key")


def discounted_expected(par, x, tx, T, weeks=52, annual_rate=0.10):
    """sum over weeks of (E[Y(w)] - E[Y(w-1)]) / (1+d)^(w/52)."""
    prev = np.zeros(len(x)); tot = np.zeros(len(x))
    for w in range(1, weeks + 1):
        cur = expected_purchases(par, w, x, tx, T)
        tot += (cur - prev) / (1 + annual_rate) ** (w / 52.0)
        prev = cur
    return tot, prev

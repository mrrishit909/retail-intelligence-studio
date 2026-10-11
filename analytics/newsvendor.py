"""Newsvendor reference implementation (SIMULATED costs). The browser module must reproduce these functions (see newsvendor_vectors.json).

Single period, price p, unit cost c, salvage s (s < c < p). Critical fractile cf = (p - c) / (p - s). Underage cu = p - c, overage co = c - s.
Normal demand N(mu, sigma): z = Phi^-1(cf); Q* = max(0, mu + sigma z); zq = (Q - mu) / sigma;
  E[sales] = mu - sigma * (phi(zq) - zq * (1 - Phi(zq)))   (demand truncation at 0 ignored; documented)
  leftover = Q - E[sales]; shortage = mu - E[sales]; profit = p E[sales] - c Q + s leftover; service level = Phi(zq).
Empirical demand (samples d_i): Q* = smallest sample with F(Q) >= cf; E[sales] = mean(min(d, Q)); service level = F(Q).
"""
from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm


def fractile(p: float, c: float, s: float) -> float:
    assert s < c < p, (p, c, s)
    return (p - c) / (p - s)


def normal_policy(p, c, s, mu, sigma, q=None):
    cf = fractile(p, c, s)
    Q = max(0.0, mu + sigma * norm.ppf(cf)) if q is None else q
    zq = (Q - mu) / sigma
    es = mu - sigma * (norm.pdf(zq) - zq * (1 - norm.cdf(zq)))
    left = Q - es
    return {"critical_fractile": cf, "q_star": Q, "expected_profit": p * es - c * Q + s * left, "expected_sales": es, "expected_leftover": left,
            "expected_shortage": mu - es, "service_level": float(norm.cdf(zq))}


def empirical_policy(p, c, s, samples, q=None):
    d = np.sort(np.asarray(samples, dtype=float))
    cf = fractile(p, c, s)
    n = len(d)
    if q is None:
        k = int(math.ceil(cf * n - 1e-12))
        Q = float(d[max(k, 1) - 1])
    else:
        Q = q
    sales = np.minimum(d, Q)
    es = float(sales.mean())
    left = Q - es
    return {"critical_fractile": cf, "q_star": Q, "expected_profit": p * es - c * Q + s * left, "expected_sales": es, "expected_leftover": left,
            "expected_shortage": float(d.mean()) - es, "service_level": float((d <= Q).mean())}


def realised_profit(p, c, s, q, demand):
    return p * min(demand, q) - c * q + s * max(q - demand, 0.0)

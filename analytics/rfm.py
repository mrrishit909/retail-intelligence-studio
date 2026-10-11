"""RFM segmentation with documented bins. Snapshot = day after the last observed day."""
from __future__ import annotations

import datetime as dt

import numpy as np
import polars as pl

from analytics import data

SNAPSHOT = dt.date(2011, 12, 10)
F_EDGES = [1, 2, 4, 9]  # F score 1: 1 order; 2: 2; 3: 3-4; 4: 5-8; 5: 9+  (score = 1 + count of edges <= freq... see fscore)
SEGMENTS = [  # ordered, first match wins: (name, rule text, predicate on r,f,m, action note)
    ("Champions", "R >= 4, F >= 4, M >= 4", lambda r, f, m: (r >= 4) & (f >= 4) & (m >= 4), "Recent, frequent, high spend."),
    ("Loyal", "F >= 4, R >= 3", lambda r, f, m: (f >= 4) & (r >= 3), "Frequent and not lapsed; spend below champions or slightly less recent."),
    ("At risk", "F >= 4, R <= 2", lambda r, f, m: (f >= 4) & (r <= 2), "Used to buy often, quiet for a long time."),
    ("New customers", "R >= 4, F = 1", lambda r, f, m: (r >= 4) & (f == 1), "One recent order so far."),
    ("Potential loyalists", "R >= 4, F in {2,3}", lambda r, f, m: (r >= 4) & (f >= 2) & (f <= 3), "Recent, repeating, not yet frequent."),
    ("Promising", "R = 3, F <= 3", lambda r, f, m: (r == 3) & (f <= 3), "Mid recency, light frequency."),
    ("Need attention", "R = 2, F = 3", lambda r, f, m: (r == 2) & (f == 3), "Slipping, moderate history."),
    ("About to sleep", "R = 2, F <= 2", lambda r, f, m: (r == 2) & (f <= 2), "Below-average recency, light history."),
    ("Lost", "R = 1, F <= 3", lambda r, f, m: (r == 1) & (f <= 3), "Longest silent, light history."),
]
NAMES = [s[0] for s in SEGMENTS]


def fscore(freq: np.ndarray) -> np.ndarray:
    return 1 + (freq >= 2).astype(int) + (freq >= 3).astype(int) + (freq >= 5).astype(int) + (freq >= 9).astype(int)


def quint_by_edges(x: np.ndarray, edges: np.ndarray, higher_better=True) -> np.ndarray:
    k = np.searchsorted(edges, x, side="right")  # 0..4 -> bin index
    return (k + 1) if higher_better else (5 - k)


def compute() -> dict:
    s = data.sales(customers_only=True)
    rf = data.refunds().filter(pl.col("customer_key").is_not_null())
    g = s.group_by("customer_key").agg(
        pl.col("day").max().alias("last_day"), pl.col("invoice_no").n_unique().alias("frequency"), pl.col("amount").sum().alias("sales"),
        pl.col("raw_id").count().alias("lines"))
    r = rf.group_by("customer_key").agg(pl.col("amount").sum().alias("refunds"))
    c = g.join(r, on="customer_key", how="left").with_columns(pl.col("refunds").fill_null(0.0)).sort("customer_key")
    c = c.with_columns(((pl.lit(SNAPSHOT) - pl.col("last_day")).dt.total_days()).alias("recency_days"), (pl.col("sales") + pl.col("refunds")).alias("monetary"))
    rec, fr, mon = c["recency_days"].to_numpy(), c["frequency"].to_numpy(), c["monetary"].to_numpy()
    q = [0.2, 0.4, 0.6, 0.8]
    r_edges, m_edges = np.quantile(rec, q), np.quantile(mon, q)
    rs = quint_by_edges(rec, r_edges, higher_better=False)  # fewer days = better
    ms = quint_by_edges(mon, m_edges)
    fs = fscore(fr)
    seg = np.full(len(c), -1)
    for i, (_, _, pred, _) in enumerate(SEGMENTS):
        m = pred(rs, fs, ms) & (seg == -1)
        seg[m] = i
    assert (seg >= 0).all()
    c = c.with_columns(pl.Series("r", rs), pl.Series("f", fs), pl.Series("m", ms), pl.Series("segment", seg))
    ctry = data.sql("select customer_key, country from dim_customer")
    c = c.join(ctry, on="customer_key").sort("customer_key")
    return {"df": c, "r_edges": r_edges, "m_edges": m_edges}

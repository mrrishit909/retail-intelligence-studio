"""Cohort retention by first-purchase month (first sale invoice observed in the ledger)."""
from __future__ import annotations

import numpy as np
import polars as pl

from analytics import data

LAST_FULL_MONTH = "2011-11"  # 2011-12 ends on the 9th: partial, treated as not observed


def month_idx(m: str) -> int:
    y, mo = m.split("-")
    return int(y) * 12 + int(mo) - 1


def compute() -> dict:
    s = data.sales(customers_only=True).filter(pl.col("month") <= LAST_FULL_MONTH)
    first = s.group_by("customer_key").agg(pl.col("month").min().alias("cohort"))
    inv = s.group_by("customer_key", "invoice_no", "month").agg(pl.col("amount").sum().alias("amt"))
    inv = inv.join(first, on="customer_key")
    months = sorted(first["cohort"].unique().to_list())
    last = month_idx(LAST_FULL_MONTH)
    n = len(months)
    ret = np.full((n, n), np.nan); rev = np.full((n, n), np.nan); opa = np.full((n, n), np.nan)
    sizes = []
    for i, c in enumerate(months):
        ci = month_idx(c)
        sub = inv.filter(pl.col("cohort") == c)
        size = sub["customer_key"].n_unique()
        sizes.append(size)
        base = sub.filter(pl.col("month") == c)["amt"].sum()
        for k in range(0, last - ci + 1):
            mm = [m for m in [f"{(ci + k) // 12}-{(ci + k) % 12 + 1:02d}"]][0]
            t = sub.filter(pl.col("month") == mm)
            act = t["customer_key"].n_unique()
            ret[i, k] = act / size
            rev[i, k] = t["amt"].sum() / base if base > 0 else np.nan
            opa[i, k] = t.height / act if act else np.nan
    return {"months": months, "sizes": sizes, "retention": ret, "revenue_retention": rev, "orders_per_active": opa}

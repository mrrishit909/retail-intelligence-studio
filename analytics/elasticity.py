"""Price-variation evidence and the pre-registered estimability decision (docs/DATA_CONTRACTS.md).

Weekly SKU price = most frequent unit price among sale lines that week (ties: higher). A SKU qualifies when it has >= 26 weeks with sales,
<= 90% of those weeks at its modal weekly price, and >= 3 price regimes (distinct weekly prices each seen in >= 4 weeks).
Estimable only if >= 30 SKUs qualify."""
from __future__ import annotations

import numpy as np
import polars as pl

from analytics import data

MIN_WEEKS, MAX_MODAL_SHARE, MIN_REGIMES, MIN_REGIME_WEEKS, MIN_SKUS = 26, 0.90, 3, 4, 30


def weekly_prices() -> pl.DataFrame:
    s = data.sales().filter(pl.col("in_complete_week"))
    c = s.group_by("sku", "week_start", "unit_price").agg(pl.len().alias("n"), pl.col("quantity").sum().alias("units"))
    wk = c.sort(["sku", "week_start", "n", "unit_price"], descending=[False, False, True, True]).group_by(["sku", "week_start"], maintain_order=True).first()
    u = c.group_by("sku", "week_start").agg(pl.col("units").sum().alias("units_total"), pl.col("unit_price").n_unique().alias("lines_prices"))
    return wk.join(u, on=["sku", "week_start"]).select("sku", "week_start", pl.col("unit_price").alias("price"), "units_total", "lines_prices")


def evidence() -> dict:
    w = weekly_prices()
    desc = data.sql("select sku, description from dim_product")
    rows = []
    for sku, g in w.group_by("sku"):
        sku = sku[0]
        p = g["price"].round(2).to_numpy()
        vals, cnt = np.unique(p, return_counts=True)
        modal = vals[np.lexsort((vals, cnt))[-1]]  # max count, ties higher price
        regimes = int((cnt >= MIN_REGIME_WEEKS).sum())
        rows.append({"sku": sku, "weeks_sold": len(p), "distinct_prices": len(vals), "modal_price_gbp": float(modal), "modal_price_share": float(cnt.max() / len(p)),
                     "price_cv": float(p.std() / p.mean()) if p.mean() > 0 else 0.0, "weeks_off_modal": int((p != modal).sum()), "price_regimes": regimes,
                     "units": int(g["units_total"].sum())})
    df = pl.DataFrame(rows).join(desc, on="sku", how="left")
    cons = df.filter(pl.col("weeks_sold") >= MIN_WEEKS)
    qual = cons.filter((pl.col("modal_price_share") <= MAX_MODAL_SHARE) & (pl.col("price_regimes") >= MIN_REGIMES))
    return {"all": df, "considered": cons, "qualifying": qual, "weekly": w}


STAGE2_MAX_WITHIN_WEEK_SHARE, STAGE2_MAX_ABS_CORR, STAGE2_MIN_LINES = 0.25, 0.2, 5


def identification(qualifying_skus: list[str]) -> dict:
    """Stage 2: is price variation time-based (list price) or buyer/quantity-based (tiers)?"""
    from scipy.stats import spearmanr
    s = data.sales().filter(pl.col("in_complete_week") & pl.col("sku").is_in(qualifying_skus)).with_columns(pl.col("unit_price").log().alias("lp"))
    s = s.with_columns(pl.col("lp").mean().over("sku").alias("m_sku"), pl.col("lp").mean().over("sku", "week_start").alias("m_sw"))
    tot = float(((s["lp"] - s["m_sku"]) ** 2).sum()); within = float(((s["lp"] - s["m_sw"]) ** 2).sum())
    g = s.group_by("sku", "week_start").agg(pl.col("unit_price").n_unique().alias("k"), pl.len().alias("n"))
    cs = []
    for _, d in s.group_by("sku", "week_start"):
        if d.height >= STAGE2_MIN_LINES and d["unit_price"].n_unique() > 1 and d["quantity"].n_unique() > 1:
            cs.append(spearmanr(d["quantity"].to_numpy(), d["unit_price"].to_numpy())[0])
    cs = np.array(cs)
    return {"within_week_variance_share": within / tot, "sku_weeks": g.height, "sku_weeks_multi_price_share": float((g["k"] > 1).mean()),
            "median_qty_price_spearman": float(np.nanmedian(cs)), "share_corr_below_minus_0_2": float(np.nanmean(cs < -0.2)), "sku_weeks_tested": int(len(cs))}

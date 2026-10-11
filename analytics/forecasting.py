"""Weekly unit forecasting with rolling-origin (expanding window) backtests against seasonal-naive (lag 52)."""
from __future__ import annotations

import datetime as dt
import warnings

import numpy as np
import polars as pl
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from analytics import data

MIN_TRAIN = 60
HMAX = 8
POOL_H = [1, 2, 4, 8]
LAG = 52
MODELS = {
    "snaive": "Seasonal naive: units of the same week last year (lag 52). The baseline every other model must beat.",
    "mean4": "Mean of the last 4 weeks, flat. No seasonality.",
    "ets": "Damped additive-trend exponential smoothing (statsmodels Holt), no seasonality.",
    "seasonal_ratio": "Recent 4-week level times last year's seasonal ratio (3-week centred window of lag-52 units over last year's matching 4-week level).",
    "ensemble": "Mean of ets and seasonal_ratio.",
}


def weekly_matrix(n_sku=60):
    s = data.sales().filter(pl.col("in_complete_week"))
    wk = sorted(data.sql("select distinct week_start from dim_date where in_complete_week")["week_start"].to_list())
    idx = {w: i for i, w in enumerate(wk)}
    ser, meta = {}, {}
    fam = s.group_by("family", "week_start").agg(pl.col("quantity").sum().alias("u"))
    for f in sorted(fam["family"].unique().to_list()):
        y = np.zeros(len(wk))
        for w, u in fam.filter(pl.col("family") == f).select("week_start", "u").iter_rows():
            y[idx[w]] = u
        ser[f"family:{f}"] = y; meta[f"family:{f}"] = ("family", f, f)
    sk = s.group_by("sku", "week_start").agg(pl.col("quantity").sum().alias("u"))
    info = s.group_by("sku").agg(pl.col("description").first(), pl.col("family").first(), pl.col("quantity").sum().alias("tot"), pl.col("week_start").n_unique().alias("nw"))
    last13 = set(wk[-13:])
    act = sk.filter(pl.col("week_start").is_in(list(last13))).group_by("sku").agg(pl.col("week_start").n_unique().alias("nl"))
    cand = info.join(act, on="sku").filter((pl.col("nw") >= 70) & (pl.col("nl") >= 8)).sort("tot", descending=True).head(n_sku)
    for sku, d, f, tot, nw, nl in cand.iter_rows():
        y = np.zeros(len(wk))
        for w, u in sk.filter(pl.col("sku") == sku).select("week_start", "u").iter_rows():
            y[idx[w]] = u
        ser[f"sku:{sku}"] = y; meta[f"sku:{sku}"] = ("sku", f"{sku} {d.title()}", f)
    return wk, ser, meta


def f_snaive(y, h):  # y = training series; forecast steps 1..h
    n = len(y)
    return np.array([y[n + k - LAG] for k in range(h)])  # step k+1 -> index n+k, minus 52


def f_mean4(y, h):
    return np.full(h, y[-4:].mean())


def f_ets(y, h):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            m = ExponentialSmoothing(y, trend="add", damped_trend=True, initialization_method="estimated").fit()
            f = m.forecast(h)
            if not np.all(np.isfinite(f)):
                raise ValueError
        except Exception:
            f = np.full(h, y[-4:].mean())
    return np.maximum(f, 0.0)


def f_ratio(y, h):
    n = len(y)
    lvl = y[-4:].mean()
    ly = y[n - 4 - LAG:n - LAG].mean()
    out = []
    for k in range(h):
        j = n + k - LAG
        win = y[max(j - 1, 0):j + 2].mean()
        if ly <= 0 or lvl <= 0:
            out.append(y[j])
        else:
            out.append(lvl * float(np.clip(win / ly, 0.25, 4.0)))
    return np.array(out)


def forecasts(y, h):
    e, r = f_ets(y, h), f_ratio(y, h)
    return {"snaive": f_snaive(y, h), "mean4": f_mean4(y, h), "ets": e, "seasonal_ratio": r, "ensemble": (e + r) / 2}


def backtest(ser: dict):
    """Returns errors[model][series_id] -> array (n_origins_total, HMAX) of (forecast - actual), NaN where origin+h beyond data; plus origins."""
    names = list(ser)
    N = len(next(iter(ser.values())))
    origins = list(range(MIN_TRAIN - 1, N - 1))
    err = {m: {s: np.full((len(origins), HMAX), np.nan) for s in names} for m in MODELS}
    for s in names:
        y = ser[s]
        for oi, o in enumerate(origins):
            h = min(HMAX, N - 1 - o)
            f = forecasts(y[:o + 1], h)
            for m, v in f.items():
                err[m][s][oi, :h] = v - y[o + 1:o + 1 + h]
    return origins, err


def pooled(ser, err, origins, ids, h):
    """Pooled metrics over `ids` at horizon h for every model. Returns dict model -> metrics."""
    N = len(next(iter(ser.values())))
    out = {}
    for m in MODELS:
        ae, act, mase_terms, bias = [], [], [], []
        for s in ids:
            e = err[m][s][:, h - 1]
            ok = ~np.isnan(e)
            y = ser[s]
            # actual at origin+h
            a = np.array([y[o + h] for o, k in zip(origins, ok) if k])
            ee = e[ok]
            ae.append(np.abs(ee)); act.append(a); bias.append(ee)
            for o, x in zip([o for o, k in zip(origins, ok) if k], ee):
                sc = np.abs(np.diff(y[:o + 1])).mean()
                mase_terms.append(abs(x) / sc if sc > 0 else np.nan)
        ae, act, bias = np.concatenate(ae), np.concatenate(act), np.concatenate(bias)
        fcst = act + bias  # e = forecast - actual
        out[m] = {"actual_total": float(act.sum()), "forecast_total": float(fcst.sum()), "over_total": float(np.maximum(bias, 0).sum()),
                  "under_total": float(np.maximum(-bias, 0).sum()), "mae": float(ae.mean()), "wape_pct": float(100 * ae.sum() / act.sum()), "mase": float(np.nanmean(mase_terms)),
                  "bias_pct": float(100 * bias.sum() / act.sum()), "n": int(len(ae))}
    return out

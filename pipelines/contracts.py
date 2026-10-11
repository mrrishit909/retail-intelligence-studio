"""Generate JSON Schemas (draft 2020-12) for every published artifact into data/contracts/*.schema.json.

Contract-first: the site is designed against these files. Every artifact carries schema_version "v1" and a `tags` map
(field group -> honesty tag; OBSERVED, DERIVED, PREDICTED, SIMULATED, SYNTHETIC, optionally combined with "/").
No SYNTHETIC data is used. Money is GBP as recorded in the source; weeks start Monday; timestamps are naive UK local time as in the source.
"""
from __future__ import annotations

import json

from pipelines.common import CONTRACTS

N, I, S, B = {"type": "number"}, {"type": "integer"}, {"type": "string"}, {"type": "boolean"}
NN, IN, SN = {"type": ["number", "null"]}, {"type": ["integer", "null"]}, {"type": ["string", "null"]}
TAG_RE = "^(OBSERVED|DERIVED|PREDICTED|SIMULATED|SYNTHETIC)(/(OBSERVED|DERIVED|PREDICTED|SIMULATED|SYNTHETIC))*$"
TAG = {"type": "string", "pattern": TAG_RE}
TAGS = {"type": "object", "minProperties": 1, "additionalProperties": TAG}
DATE = {"type": "string", "pattern": r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"}
MONTH = {"type": "string", "pattern": r"^[0-9]{4}-[0-9]{2}$"}
OBJ = {"type": "object"}


def arr(item, n=None, lo=None):
    d = {"type": "array", "items": item}
    if n is not None:
        d["minItems"] = d["maxItems"] = n
    elif lo is not None:
        d["minItems"] = lo
    return d


def obj(props: dict, req: list | None = None, extra: bool = True) -> dict:
    return {"type": "object", "properties": props, "required": req if req is not None else list(props), "additionalProperties": extra}


def top(name: str, props: dict, req: list | None = None) -> dict:
    p = {"schema_version": {"const": "v1"}, "tags": TAGS, **props}
    r = ["schema_version", "tags"] + (req if req is not None else list(props))
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": name, **obj(p, r)}


def tv(v):
    """A tagged scalar fact: {value, unit, tag, note?}."""
    return obj({"value": v, "unit": S, "tag": TAG, "note": S}, ["value", "unit", "tag"])


# every number quoted in site copy lives in facts.json under one of these keys (numbers: tv(N); strings: tv(S))
FACT_NUM = [
    # source and reconciliation
    "rows_raw", "rows_kept", "rows_excluded", "rows_overlap_duplicates", "rows_exact_duplicates", "sheets", "invoices", "customers_known", "skus_product", "countries",
    "revenue_sales_gbp", "revenue_refunds_gbp", "revenue_product_net_gbp", "revenue_nonproduct_net_gbp", "revenue_total_net_gbp",
    "refund_lines", "refund_invoices", "refund_value_share_of_sales", "refund_matched_line_share", "refund_matched_qty_share", "refund_unmatched_no_customer_share",
    "stock_adjustment_lines", "nonproduct_lines", "guest_line_share", "guest_revenue_share", "zero_price_lines", "weeks_complete",
    # rfm and cohorts
    "rfm_customers", "rfm_champions_share_customers", "rfm_champions_share_revenue", "rfm_lost_share_customers", "rfm_top_decile_revenue_share",
    "cohort_count", "cohort_m1_retention_median", "cohort_m12_retention_median", "cohort_best_m3_retention", "cohort_worst_m3_retention",
    # baskets
    "basket_count", "basket_min_support", "basket_min_confidence", "basket_frequent_items", "basket_rules_total", "basket_rules_cross_family", "basket_top_lift", "basket_median_size_lines",
    # clv
    "clv_calibration_customers", "clv_holdout_weeks", "clv_pred_repeats_total", "clv_actual_repeats_total", "clv_total_error_pct", "clv_customer_corr", "clv_decile_mape_pct",
    "clv_baseline_mae", "clv_model_mae", "clv_gg_independence_corr", "clv_horizon_weeks", "clv_discount_rate_annual", "clv_top_decile_share", "clv_total_gbp", "clv_median_gbp",
    # forecasting
    "forecast_series", "forecast_origins", "forecast_horizon_max", "forecast_best_model_skill_pct", "forecast_family_skill_pct", "forecast_sku_skill_pct", "forecast_win_rate", "forecast_snaive_wape_pct", "forecast_best_wape_pct",
    # newsvendor
    "nv_cost_ratio", "nv_salvage_ratio", "nv_critical_fractile", "nv_items", "nv_vectors", "nv_policy_profit_uplift_pct",
    # elasticity
    "elasticity_skus_considered", "elasticity_skus_qualifying", "elasticity_estimable",
]
FACT_STR = ["title", "attribution", "licence", "window_label", "elasticity_decision", "not_advice", "synthetic_note", "forecast_best_model", "currency"]

TEXT_SOURCE = obj({"id": S, "publisher": S, "dataset": S, "url": S, "doi": S, "licence": S, "licence_url": S, "attribution": S, "role": S})

SCHEMAS = {
    "meta": top("meta", {
        "pipeline_version": S, "retrieved_at": S, "source": TEXT_SOURCE,
        "window": obj({"first_ts": S, "last_ts": S, "first_week": DATE, "last_complete_week": DATE, "weeks_complete": I}),
        "engine": obj({"star_schema": S, "dbt_version": S, "duckdb_version": S, "python": S, "seed": I}),
        "currency": S, "assumptions": arr(S, lo=1), "disclaimers": arr(S, lo=1), "no_demographics": S,
        "artifact_tags": OBJ, "artifact_bytes": OBJ}),
    "facts": top("facts", {
        "facts": obj({**{k: tv(N) for k in FACT_NUM}, **{k: tv(S) for k in FACT_STR}}, FACT_NUM + FACT_STR)}),
    "reconciliation": top("reconciliation", {
        "raw_files": arr(obj({"name": S, "bytes": I, "sha256": S}), lo=2), "retrieved_at": S,
        "sheets": arr(obj({"sheet": S, "rows": I, "first_ts": S, "last_ts": S}), 2),
        "row_ledger": obj({"raw_rows": I, "kept": I, "excluded": I, "excluded_by_reason": OBJ, "identity": S}),
        "amount_ledger": obj({"raw_amount_gbp": N, "kept_amount_gbp": N, "excluded_amount_gbp": N, "excluded_by_reason_gbp": OBJ, "identity": S}),
        "classes": arr(obj({"class": S, "rows": I, "amount_gbp": N, "units": I, "treatment": S}), lo=4),
        "analytics_scopes": arr(obj({"analysis": S, "rule": S, "rows_in": I, "rows_out": I, "rows_dropped_by_reason": OBJ}), lo=5),
        "guest": obj({"rows": I, "row_share": N, "amount_gbp": N, "amount_share": N, "note": S}),
        "refunds": obj({"lines": I, "invoices": I, "value_gbp": N, "matched_lines": I, "matched_qty": I, "unmatched_qty": I, "unmatched_no_customer_lines": I,
                        "unmatched_no_prior_sale_lines": I, "matching_rule": S, "over_refund_lines": I}),
        "stockcode_classes": arr(obj({"class": S, "codes": arr(S), "rows": I, "amount_gbp": N}), lo=3),
        "identities": arr(obj({"id": S, "description": S, "lhs": N, "rhs": N, "abs_diff": N, "pass": B}), lo=6),
        "monthly": arr(obj({"month": MONTH, "amount_gbp": N}), lo=24)}),
    "overview": top("overview", {
        "months": arr(MONTH, lo=24),
        "series": obj({"sales_gbp": arr(N), "refunds_gbp": arr(N), "product_net_gbp": arr(N), "nonproduct_net_gbp": arr(N), "invoices": arr(I), "active_customers": arr(I), "guest_revenue_share": arr(N)}),
        "countries": arr(obj({"country": S, "net_gbp": N, "share": N, "invoices": I, "customers": I}), lo=5),
        "country_other": obj({"countries": I, "net_gbp": N, "share": N}),
        "rhythm": obj({"weekday": arr(S, 7), "hour": arr(I), "sales_gbp": arr(arr(N)), "lines": arr(arr(I))}),
        "basket": obj({"quantile_levels": arr(N), "lines_per_invoice": arr(N), "invoice_value_gbp": arr(N)})}),
    "products": top("products", {
        "family_rule": S, "family_coverage_revenue_share": N, "family_coverage_sku_share": N,
        "families": arr(obj({"family": S, "keywords": arr(S), "skus": I, "revenue_gbp": N, "units": I, "share": N, "customers": I}), lo=10),
        "top_skus": arr(obj({"sku": S, "description": S, "family": S, "revenue_gbp": N, "units": I, "customers": I, "invoices": I, "median_price_gbp": N,
                             "first_week": DATE, "last_week": DATE, "refund_units": I}), lo=100),
        "concentration": obj({"top_10_share": N, "top_100_share": N, "skus_for_80pct_revenue": I, "skus_total": I})}),
    "landscape": top("landscape", {
        "weeks": arr(DATE, lo=90), "families": arr(S, lo=10), "revenue_gbp": arr(arr(N)), "unit": S, "note": S}),
    "rfm": top("rfm", {
        "snapshot_date": DATE, "definition": obj({"recency": S, "frequency": S, "monetary": S, "scoring": S, "ties": S}),
        "bins": obj({"recency_days_edges": arr(N, 4), "frequency_edges": arr(N, 4), "monetary_gbp_edges": arr(N, 4)}),
        "included": obj({"customers": I, "excluded_guest_line_share": N, "excluded_guest_revenue_share": N, "customers_with_only_refunds": I}),
        "segments": arr(obj({"segment": S, "rule": S, "customers": I, "customer_share": N, "revenue_gbp": N, "revenue_share": N, "avg_recency_days": N,
                             "avg_frequency": N, "avg_monetary_gbp": N, "action_note": S}), lo=6),
        "grid": obj({"r_by_f_customers": arr(arr(I), 5), "r_by_f_revenue_gbp": arr(arr(N), 5)}),
        "customers": obj({"key": arr(I), "recency_days": arr(I), "frequency": arr(I), "monetary_gbp": arr(N), "r": arr(I), "f": arr(I), "m": arr(I), "segment": arr(I), "country": arr(I)}),
        "segment_names": arr(S), "country_names": arr(S)}),
    "cohorts": top("cohorts", {
        "definition": S, "min_cohort_size": I, "cohort_months": arr(MONTH, lo=20), "sizes": arr(I),
        "offsets": arr(I, lo=12),
        "retention": arr(arr(NN)), "revenue_retention": arr(arr(NN)), "orders_per_active": arr(arr(NN)),
        "mean_curve": obj({"offsets": arr(I), "retention": arr(NN), "n_cohorts": arr(I)}),
        "notes": arr(S, lo=1), "right_censoring": S}),
    "baskets": top("baskets", {
        "params": obj({"min_support": N, "min_confidence": N, "min_lift": N, "max_len": I, "baskets": I, "frequent_items": I, "frequent_itemsets": I,
                       "basket_definition": S, "item_definition": S, "support_count_min": I}),
        "rules_total": I,
        "rules": arr(obj({"antecedent": arr(S, lo=1), "consequent": arr(S, lo=1), "antecedent_desc": arr(S), "consequent_desc": arr(S), "support": N, "confidence": N, "lift": N,
                          "leverage": N, "conviction": NN, "count": I, "same_family": B, "families": arr(S)}), lo=20),
        "nodes": arr(obj({"sku": S, "description": S, "family": S, "support": N, "baskets": I, "degree": I}), lo=20),
        "edges": arr(obj({"a": S, "b": S, "support": N, "lift": N, "count": I, "same_family": B}), lo=20),
        "caveat": S}),
    "clv": top("clv", {
        "model": obj({"bgnbd": obj({"r": N, "alpha": N, "a": N, "b": N, "loglik": N, "converged": B, "n_customers": I}),
                      "gamma_gamma": obj({"p": N, "q": N, "v": N, "loglik": N, "converged": B, "n_customers": I}),
                      "implementation": S, "transaction_definition": S, "time_unit": S}),
        "calibration": obj({"start": DATE, "end": DATE, "holdout_start": DATE, "holdout_end": DATE, "holdout_weeks": N, "customers": I,
                            "customers_repeat_in_calibration": I, "customers_active_in_holdout": I}),
        "holdout": obj({"predicted_repeats_total": N, "actual_repeats_total": I, "total_error_pct": N, "mae_customer": N, "baseline_mae_customer": N,
                        "corr_customer": N, "rank_corr_customer": N, "baseline": S, "mape_decile_pct": N}),
        "deciles": arr(obj({"decile": I, "customers": I, "predicted": N, "actual": N, "error_pct": N}), 10),
        "by_frequency": arr(obj({"repeats_in_calibration": I, "customers": I, "predicted": N, "actual": N}), lo=4),
        "gamma_gamma_check": obj({"corr_frequency_monetary": N, "customers": I, "note": S}),
        "final_fit": obj({"fit_start": DATE, "fit_end": DATE, "horizon_weeks": I, "discount_rate_annual": N, "customers": I, "clv_total_gbp": N, "clv_median_gbp": N,
                          "top_decile_share": N, "clv_quantiles": arr(N), "quantile_levels": arr(N)}),
        "by_segment": arr(obj({"segment": S, "customers": I, "clv_mean_gbp": N, "clv_total_gbp": N, "p_alive_mean": N, "expected_purchases_mean": N}), lo=6),
        "customers": obj({"key": arr(I), "frequency": arr(I), "recency_weeks": arr(N), "age_weeks": arr(N), "monetary_gbp": arr(N), "p_alive": arr(N),
                          "expected_purchases": arr(N), "expected_value_gbp": arr(N), "clv_gbp": arr(N)}),
        "limitations": arr(S, lo=3)}),
    "forecast": top("forecast", {
        "unit": S, "week_start": DATE, "weeks": arr(DATE, lo=90), "horizon_weeks": I, "forecast_weeks": arr(DATE, lo=1),
        "model": S, "interval": obj({"level": N, "method": S}),
        "series": arr(obj({"id": S, "kind": {"enum": ["family", "sku"]}, "label": S, "family": S, "history_units": arr(N), "forecast": arr(N), "lo": arr(N), "hi": arr(N),
                           "total_units": I, "skill_vs_snaive_pct": NN, "wape_pct": NN, "snaive_wape_pct": NN}), lo=20)}),
    "backtest": top("backtest", {
        "design": obj({"scheme": S, "first_origin_week": DATE, "last_origin_week": DATE, "origins": I, "horizons": arr(I, lo=1), "min_train_weeks": I, "series": I,
                       "baseline": S, "metrics": arr(S)}),
        "models": arr(obj({"id": S, "description": S}), lo=3),
        "pooled": arr(obj({"model": S, "horizon": I, "scope": {"enum": ["all", "family", "sku"]}, "mae": N, "wape_pct": N, "mase": NN, "bias_pct": N, "skill_vs_snaive_pct": NN, "n": I}), lo=10),
        "win_rate": arr(obj({"model": S, "scope": S, "series_beating_snaive": I, "series": I, "share": N}), lo=2),
        "by_series": arr(obj({"id": S, "kind": S, "models": OBJ}), lo=20),
        "by_origin": arr(obj({"origin": DATE, "mae": OBJ}), lo=10),
        "interval_coverage": obj({"nominal": N, "empirical": N, "n": I}),
        "verdict": S}),
    "newsvendor_params": top("newsvendor_params", {
        "labelled": {"const": "SIMULATED"},
        "assumptions": arr(obj({"id": S, "label": S, "value": N, "unit": S, "basis": S, "range": arr(N, 2)}), lo=4),
        "formula": obj({"critical_fractile": S, "normal": S, "empirical": S, "profit": S}),
        "items": arr(obj({"id": S, "label": S, "kind": S, "price_gbp": N, "mean_weekly_units": N, "sd_weekly_units": N, "forecast_next_week": N,
                          "weekly_units_sample": arr(N), "weeks": I}), lo=10),
        "disclaimer": S}),
    "newsvendor_vectors": top("newsvendor_vectors", {
        "tolerance_rel": N, "note": S,
        "vectors": arr(obj({"case": S, "model": {"enum": ["normal", "empirical"]},
                            "inputs": obj({"price": N, "cost": N, "salvage": N, "mu": NN, "sigma": NN, "samples": {"type": ["array", "null"], "items": N}}, ["price", "cost", "salvage"]),
                            "expected": obj({"critical_fractile": N, "q_star": N, "expected_profit": N, "expected_sales": N, "expected_leftover": N, "expected_shortage": N, "service_level": N})}), lo=20)}),
    "newsvendor_scenarios": top("newsvendor_scenarios", {
        "grid": obj({"cost_ratio": arr(N, lo=3), "salvage_ratio": arr(N, lo=2)}),
        "scenarios": arr(obj({"item": S, "cost_ratio": N, "salvage_ratio": N, "critical_fractile": N, "q_normal": N, "q_empirical": N, "profit_normal": N, "profit_empirical": N,
                              "service_level": N, "mean_order_profit": N}), lo=50),
        "policy_check": obj({"description": S, "items": I, "weeks_evaluated": I, "profit_newsvendor": N, "profit_mean_order": N, "uplift_pct": N,
                             "per_item": arr(obj({"item": S, "profit_newsvendor": N, "profit_mean_order": N, "profit_snaive_order": N})), "caveat": S})}),
    "elasticity": top("elasticity", {
        "decision": obj({"estimable": B, "text": S, "rule": S, "criteria": arr(obj({"id": S, "text": S, "threshold": N, "observed": N, "pass": B}), lo=3)}),
        "evidence": obj({
            "skus_considered": I, "skus_qualifying": I, "price_rows": I,
            "table": arr(obj({"sku": S, "description": S, "weeks_sold": I, "distinct_prices": I, "modal_price_gbp": N, "modal_price_share": N, "price_cv": N,
                              "weeks_off_modal": I, "price_regimes": I, "units": I}), lo=20),
            "distribution": obj({"distinct_prices_quantiles": arr(N), "price_cv_quantiles": arr(N), "quantile_levels": arr(N)}),
            "price_tiers_note": S}),
        "estimates": {"type": ["object", "null"]}, "what_would_be_needed": arr(S, lo=2)}),
    "validation": top("validation", {
        "checks": arr(obj({"id": S, "group": S, "description": S, "expected": S, "actual": S, "pass": B}), lo=20),
        "passed": I, "failed": I, "limitations_observed": arr(S, lo=3)}),
}


def run() -> None:
    CONTRACTS.mkdir(parents=True, exist_ok=True)
    for name, sch in SCHEMAS.items():
        (CONTRACTS / f"{name}.schema.json").write_text(json.dumps(sch, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(SCHEMAS)} schemas")


if __name__ == "__main__":
    run()

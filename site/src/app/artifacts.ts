import type { ArtifactSpec } from "../data/loader";
const obj = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null;
const spec = <T,>(file: string): ArtifactSpec<T> => ({ file, guard: (v): v is T => obj(v) });

export interface Rule { antecedent: string[]; antecedent_desc: string[]; consequent: string[]; consequent_desc: string[]; count: number; support: number; confidence: number; lift: number; same_family: boolean; variant_of_same_product: boolean; families: string[] }
export interface Node { sku: string; description: string; family: string; baskets: number; degree: number; support: number }
export interface Edge { a: string; b: string; count: number; lift: number; support: number; same_family: boolean; hero: boolean }
export interface Baskets {
  hero: { a: string; a_desc: string; b: string; b_desc: string; na: number; nb: number; nab: number; chance: number; lift: number; baskets: number; confidence_a_to_b: number; confidence_b_to_a: number; variant_of_same_product: boolean };
  rules: Rule[]; rules_total: number; nodes: Node[]; edges: Edge[]; caveat: string;
  params: { baskets: number; min_support: number; min_confidence: number; min_lift: number; max_len: number; support_count_min: number };
  showcase: { indices: number[]; kinds: string[] };
}
export interface Cohorts {
  cohort_months: string[]; offsets: number[]; sizes: number[]; retention: (number | null)[][]; revenue_retention: (number | null)[][];
  active_customers: number[]; active_revenue_gbp: number[]; min_cohort_size: number; right_censoring: string; definition: string; notes: string[];
}
export interface Segment { segment: string; customers: number; revenue_gbp: number; customer_share: number; revenue_share: number; rule: string; action_note: string }
export interface Rfm {
  grid: Record<"r_by_f_customers" | "r_by_f_revenue_gbp" | "r_by_m_customers" | "r_by_m_revenue_gbp" | "f_by_m_customers" | "f_by_m_revenue_gbp", number[][]>;
  segments: Segment[]; definition: { scoring: string; ties: string; recency: string; frequency: string; monetary: string };
  included: { customers: number; excluded_guest_revenue_share: number; excluded_guest_line_share: number }; snapshot_date: string;
}
export interface NvItem { id: string; kind: string; label: string; mean_weekly_units: number; sd_weekly_units: number; price_gbp: number; weekly_units_sample: number[]; weeks: number; forecast_next_week: number; forecast_sd: number }
export interface NvAssumption { id: string; label: string; value: number; range: [number, number]; unit: string; basis: string }
export interface NvParams { assumptions: NvAssumption[]; items: NvItem[]; disclaimer: string }
export interface NvScenarios { policy_check: { caveat: string; description: string; profit_mean_order: number; profit_newsvendor: number; uplift_pct: number; weeks_evaluated: number } }
export interface Backtest {
  best_model: string; verdict: string; design: { horizons: number[]; origins: number; baseline: string };
  models: { id: string; label: string; description: string }[];
  pooled: { model: string; scope: string; horizon: number; actual_total: number; forecast_total: number; over_total: number; under_total: number; wape_pct: number; bias_pct: number; skill_vs_snaive_pct: number; n: number }[];
  win_rate: { model: string; scope: string; series: number; series_beating_snaive: number; share: number }[];
  interval_coverage: { nominal: number; empirical: number; n: number };
}
export interface ForecastSeries { id: string; kind: string; label: string; forecast: number[]; lo: number[]; hi: number[]; history_units: number[]; total_units: number; wape_pct: number; snaive_wape_pct: number; skill_vs_snaive_pct: number }
export interface Forecast { series: ForecastSeries[]; interval: { level: number; method: string }; model: string }
export interface ClvDecile { decile: number; customers: number; actual_sum: number; predicted_sum: number; overlap_sum: number; baseline_predicted_sum: number; error_pct: number }
export interface Clv {
  deciles: ClvDecile[]; limitations: string[]; calibration: { customers: number; start: string; end: string; holdout_weeks: number };
  holdout: { actual_repeats_total: number; predicted_repeats_total: number; overlap_customer_sum: number; baseline_predicted_total: number; baseline_overlap_customer_sum: number; total_error_pct: number; mape_decile_pct: number; mae_customer: number; baseline_mae_customer: number };
  gamma_gamma_check: { corr_frequency_monetary: number };
}
export interface Elasticity { decision: { text: string; estimable: boolean }; evidence: { criteria: { id: string; text: string; observed: number; threshold: number; pass: boolean }[] }; what_would_be_needed: string[] }
export interface Recon {
  row_ledger: { raw_rows: number; kept: number; excluded: number; excluded_by_reason: Record<string, number> };
  classes: Record<string, { rows?: number; gbp?: number; units?: number }>[] | Record<string, unknown>;
  refunds: { matched_qty: number; refunded_qty: number; sale_units: number; matched_value_gbp: number; matching_rule: string; unmatched_no_customer_qty?: number };
  guest: { rows: number; row_share: number; amount_share: number; amount_gbp: number; note: string };
  identities: { id: string; description: string; pass: boolean }[];
}

export const BASKETS = spec<Baskets>("baskets.json");
export const COHORTS = spec<Cohorts>("cohorts.json");
export const RFM = spec<Rfm>("rfm.json");
export const NVPARAMS = spec<NvParams>("newsvendor_params.json");
export const NVSCEN = spec<NvScenarios>("newsvendor_scenarios.json");
export const BACKTEST = spec<Backtest>("backtest.json");
export const FORECAST = spec<Forecast>("forecast.json");
export const CLV = spec<Clv>("clv.json");
export const ELAST = spec<Elasticity>("elasticity.json");
export const RECON = spec<Recon>("reconciliation.json");

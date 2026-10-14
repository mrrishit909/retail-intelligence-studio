import { useState } from "react";
import { Track } from "../scroll/Track";
import { HonestyChip } from "../components/HonestyChip";
import { Radio } from "../components/Radio";
import { WordReveal } from "../components/WordReveal";
import { ArtifactStatus } from "../components/StateUI";
import { useArtifact } from "../data/useArtifact";
import { BACKTEST, CLV, FORECAST, type Backtest, type Clv, type Forecast } from "../app/artifacts";
import { fmt } from "../app/data";
import { setPair, type PairSpec } from "../app/pairView";
import { Column, Lower, SetNames, SourceFoot, useSteps } from "./common";
import type { SceneDef } from "../app/scenes";
import { classOf } from "../app/geometry";

type Scope = "all" | "family" | "sku";
export function forecastSpec(b: Backtest, model: string, horizon: number, scope: Scope): { spec: PairSpec; row: Backtest["pooled"][number] } | null {
  const row = b.pooled.find((r) => r.model === model && r.horizon === horizon && r.scope === scope);
  if (!row || row.n === 0) return null;
  const label = b.models.find((m) => m.id === model)?.label ?? model;
  return {
    row,
    spec: { id: `fc:${model}:${horizon}:${scope}`, unit: "UNITS", sizeA: row.actual_total, sizeB: row.forecast_total, shared: row.actual_total - row.under_total, labelA: `ACTUAL UNITS, HORIZON ${horizon} WEEK${horizon > 1 ? "S" : ""}`, labelB: `FORECAST: ${label.toUpperCase()}`, chance: null, role: "predicted", interval: null, hatch: false, refSize: Math.max(row.actual_total, row.forecast_total), axis: "h" },
  };
}
export function clvSpec(c: Clv, decile: number | null, baseline: boolean): PairSpec {
  const d = decile ? c.deciles.find((x) => x.decile === decile)! : null;
  const a = d ? d.actual_sum : c.holdout.actual_repeats_total;
  const p = d ? (baseline ? d.baseline_predicted_sum : d.predicted_sum) : baseline ? c.holdout.baseline_predicted_total : c.holdout.predicted_repeats_total;
  const sh = d ? Math.min(a, p) : baseline ? c.holdout.baseline_overlap_customer_sum : c.holdout.overlap_customer_sum;
  return { id: `clv:${decile ?? "all"}:${baseline ? "base" : "model"}`, unit: "UNITS", sizeA: a, sizeB: p, shared: Math.min(sh, a, p), labelA: `ACTUAL HOLDOUT REPEAT PURCHASES${d ? `, DECILE ${decile}` : ""}`, labelB: baseline ? "NO-MODEL BASELINE" : "PREDICTED BY BG/NBD", chance: null, role: "predicted", interval: null, hatch: false, refSize: Math.max(a, p) * 1.05, axis: "h" };
}

/** S06 Consequences: the forecast pair beside its baseline and backtest, then the CLV pair beside its holdout. */
export function S06Sells({ def }: { def: SceneDef }) {
  const [bt, retryB] = useArtifact(BACKTEST);
  const [fc] = useArtifact(FORECAST);
  const [cl, retryC] = useArtifact(CLV);
  const [model, setModel] = useState<string | null>(null);
  const [horizon, setHorizon] = useState<number | null>(null);
  const [scope, setScope] = useState<Scope>("all");
  const [decile, setDecile] = useState<number | null>(null);
  const [step, setStep] = useState(0);
  const B = bt.status === "ready" ? bt.data : null, F: Forecast | null = fc.status === "ready" ? fc.data : null, C = cl.status === "ready" ? cl.data : null;
  const best = B?.best_model ?? "mean4";
  const stepModel = step === 2 ? "snaive" : best;
  const stepHorizon = step === 3 ? 8 : 1;
  const m = model ?? stepModel, h = horizon ?? stepHorizon;
  const fcPair = B ? forecastSpec(B, m, h, scope) : null;
  const series = F?.series[0];
  const seriesSpec: PairSpec | null = series ? { id: `series:${series.id}`, unit: "UNITS", sizeA: series.history_units[series.history_units.length - 1]!, sizeB: series.forecast[0]!, shared: Math.min(series.history_units[series.history_units.length - 1]!, series.forecast[0]!), labelA: `${series.label.toUpperCase()}: LAST WEEK'S UNITS`, labelB: "NEXT WEEK, FORECAST", chance: null, role: "predicted", interval: [series.lo[0]!, series.hi[0]!], hatch: false, refSize: Math.max(series.hi[0]!, series.history_units[series.history_units.length - 1]!), axis: "h" } : null;
  useSteps(def.id, [0.06, 0.22, 0.38, 0.54, 0.7, 0.86], (s) => {
    setStep(s);
    if (s >= 1 && s <= 4) { setModel(null); setHorizon(null); }
    if (s <= 3 && B) {
      const r = forecastSpec(B, s === 2 ? "snaive" : best, s === 3 ? 8 : 1, "all");
      if (s === 4 && seriesSpec) setPair({ spec: seriesSpec, alpha: 1 }); else if (r) setPair({ spec: r.spec, alpha: 1 });
    }
    if (s === 4 && seriesSpec) setPair({ spec: seriesSpec, alpha: 1 });
    if (s >= 5 && C) setPair({ spec: clvSpec(C, decile, s >= 6), alpha: 1 });
  });
  const mobile = typeof document !== "undefined" && classOf(document.documentElement.clientWidth) === "M";
  const showFc = step < 5;
  const upd = (mm: string, hh: number, sc: Scope) => { if (B) { const r = forecastSpec(B, mm, hh, sc); if (r) setPair({ spec: r.spec, alpha: 1 }); } };
  const win = B?.win_rate.find((w) => w.model === best && w.scope === "family");
  return (
    <Track id={def.id} height={def.track} landing={def.landing} className="scene scene-sells">
      <Column>
        <p className="scene-kicker">EVERY PREDICTION BESIDE ITS TEST</p>
        <WordReveal text="What will sell, and how wrong we were." as="h2" className="serif scene-title" mode={{ kind: "scrub", track: def.id, from: 0.0, to: 0.06 }} id={`${def.id}-title`} tabIndex={-1} data-scene-heading />
        <div className="ctl-row">
          {showFc && B ? (
            <>
              <Radio<string> label="MODEL" value={m} options={B.models.map((x) => x.id)} render={(id) => B.models.find((x) => x.id === id)!.label.split(" (")[0]!.toUpperCase()} onChange={(x) => { setModel(x); upd(x, h, scope); }} asSelect={mobile} />
              <Radio<string> label="HORIZON" value={String(h)} options={B.design.horizons.map(String)} render={(x) => `${x} WK`} onChange={(x) => { setHorizon(Number(x)); upd(m, Number(x), scope); }} asSelect={mobile} />
              <Radio<Scope> label="SCOPE" value={scope} options={["all", "family", "sku"] as const} render={(x) => x.toUpperCase()} onChange={(x) => { setScope(x); upd(m, h, x); }} asSelect={mobile} />
            </>
          ) : (
            <Radio<string> label="DECILE" value={String(decile ?? 0)} options={["0", ...Array.from({ length: 10 }, (_, i) => String(i + 1))]} render={(x) => (x === "0" ? "ALL" : x)} onChange={(x) => { const d = Number(x) || null; setDecile(d); if (C) setPair({ spec: clvSpec(C, d, step >= 6), alpha: 1 }); }} asSelect={mobile} />
          )}
        </div>
        <Lower>
          {showFc ? (
            <ArtifactStatus file="backtest.json" state={bt} retry={retryB} empty="UNAVAILABLE">{(b) => {
              const isSeries = step === 4 && seriesSpec;
              const spec = isSeries ? seriesSpec! : fcPair?.spec;
              return spec ? (
                <>
                  <SetNames spec={spec} />
                  {isSeries && series && F ? (
                    <p className="ledger-line mono-label">{Math.round(F.interval.level * 100)}% INTERVAL {fmt(series.lo[0]!)} TO {fmt(series.hi[0]!)} · {Math.round(b.interval_coverage.nominal * 100)}% INTERVAL COVERED {(b.interval_coverage.empirical * 100).toFixed(0)}% OF {fmt(b.interval_coverage.n)} BACKTEST CASES</p>
                  ) : fcPair ? (
                    <p className="ledger-line mono-label">WAPE {fcPair.row.wape_pct.toFixed(1)}% · BIAS {fcPair.row.bias_pct > 0 ? "+" : ""}{fcPair.row.bias_pct.toFixed(1)}% · SKILL VS SEASONAL NAIVE {fcPair.row.skill_vs_snaive_pct.toFixed(1)}% · {b.design.origins} ORIGINS</p>
                  ) : null}
                  {step >= 2 ? <p className="ledger-line mono-label">{b.verdict.toUpperCase()}</p> : null}
                  {win ? <p className="note-line mono-label">BEATS SEASONAL NAIVE ON {win.series_beating_snaive} OF {win.series} FAMILY SERIES</p> : null}
                </>
              ) : <p className="state-line">NOT EVALUATED AT THIS SCOPE</p>;
            }}</ArtifactStatus>
          ) : (
            <ArtifactStatus file="clv.json" state={cl} retry={retryC} empty="UNAVAILABLE">{(c) => (
              <>
                <SetNames spec={clvSpec(c, decile, step >= 6)} />
                <p className="ledger-line mono-label">{c.calibration.holdout_weeks.toFixed(0)}-WEEK HOLDOUT · TOTAL ERROR {c.holdout.total_error_pct.toFixed(1)}% · DECILE MAPE {c.holdout.mape_decile_pct.toFixed(1)}% · CUSTOMER MAE {c.holdout.mae_customer.toFixed(2)} VS NO-MODEL {c.holdout.baseline_mae_customer.toFixed(2)}</p>
                <p className="caveat mono-label">{c.limitations[0]!.toUpperCase()}</p>
              </>
            )}</ArtifactStatus>
          )}
          <HonestyChip tag="PREDICTED" detail="TESTED ON DATA IT NEVER SAW" />
          <SourceFoot />
        </Lower>
      </Column>
    </Track>
  );
}

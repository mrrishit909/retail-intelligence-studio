import { useMemo, useState } from "react";
import { Track } from "../scroll/Track";
import { HonestyChip } from "../components/HonestyChip";
import { Radio } from "../components/Radio";
import { WordReveal } from "../components/WordReveal";
import { ArtifactStatus } from "../components/StateUI";
import { useArtifact } from "../data/useArtifact";
import { NVPARAMS, NVSCEN, type NvItem, type NvParams } from "../app/artifacts";
import { fmt, fs, useCore } from "../app/data";
import { setPair, type PairSpec } from "../app/pairView";
import { empiricalPolicy, negativeMass, normalPolicy, type Policy } from "../model/newsvendor";
import { Column, Lower, SetNames, SourceFoot, useSteps } from "./common";
import type { SceneDef } from "../app/scenes";
import { classOf } from "../app/geometry";

export type NvModel = "normal" | "empirical";
export function nvPolicy(item: NvItem, cost: number, salvage: number, model: NvModel, q?: number): Policy {
  const p = item.price_gbp, c = cost * p, s = salvage * c; // salvage ratio is a share of unit cost (the published vectors' convention)
  return model === "normal" ? normalPolicy(p, c, s, item.forecast_next_week, item.forecast_sd, q) : empiricalPolicy(p, c, s, item.weekly_units_sample, q);
}
export function nvSpec(item: NvItem, pol: Policy, model: NvModel): PairSpec {
  const demand = pol.expected_sales + pol.expected_shortage;
  return {
    id: `nv:${item.id}:${model}`, unit: "UNITS", sizeA: demand, sizeB: pol.q_star, shared: pol.expected_sales,
    labelA: `EXPECTED WEEKLY DEMAND, ${item.label}`, labelB: "UNITS ORDERED (SIMULATED)", chance: null, role: "observed", interval: null, hatch: false, refSize: demand * 1.2, axis: "h",
  };
}

/** S05 Experiment: how many to stock. The partner is the order; the crescents are the two costs. */
export function S05Stock({ def }: { def: SceneDef }) {
  const [art, retry] = useArtifact(NVPARAMS);
  const [scen] = useArtifact(NVSCEN);
  const cs = useCore();
  const [itemId, setItemId] = useState<string | null>(null);
  const [cost, setCost] = useState<number | null>(null);
  const [sal, setSal] = useState<number | null>(null);
  const [model, setModel] = useState<NvModel>("normal");
  const [override, setOverride] = useState<number | null>(null);
  const [step, setStep] = useState(0);
  const P: NvParams | null = art.status === "ready" ? art.data : null;
  const dflt = (id: string) => P?.assumptions.find((a) => a.id === id);
  const item = P?.items.find((i) => i.id === itemId) ?? P?.items[0];
  const stepCost = step === 2 ? dflt("cost_ratio")?.range[0] : step === 3 ? dflt("cost_ratio")?.range[1] : undefined;
  const costNow = cost ?? stepCost ?? dflt("cost_ratio")?.value ?? 0.6;
  const salNow = sal ?? dflt("salvage_ratio")?.value ?? 0.2;
  const mdl: NvModel = model === "empirical" && item && item.weeks < 26 ? "normal" : model;
  const pol = useMemo(() => (item ? nvPolicy(item, costNow, salNow, mdl, override ?? undefined) : null), [item, costNow, salNow, mdl, override]);
  const star = useMemo(() => (item ? nvPolicy(item, costNow, salNow, mdl) : null), [item, costNow, salNow, mdl]);
  const spec = item && pol ? nvSpec(item, pol, mdl) : null;
  useSteps(def.id, [0.08, 0.3, 0.52, 0.74, 0.86], (s) => {
    setStep(s);
    if (item && s >= 1 && s <= 4) { setCost(null); setSal(null); setOverride(null); }
    if (item) {
      const c = s === 2 ? dflt("cost_ratio")!.range[0] : s === 3 ? dflt("cost_ratio")!.range[1] : cost ?? dflt("cost_ratio")!.value;
      const pl = nvPolicy(item, c, salNow, mdl, override ?? undefined);
      setPair({ spec: nvSpec(item, pl, mdl), alpha: 1 });
    }
  });
  const push = (c: number, s: number, m: NvModel, q?: number) => { if (item) setPair({ spec: nvSpec(item, nvPolicy(item, c, s, m, q), m), alpha: 1 }); };
  const mobile = typeof document !== "undefined" && classOf(document.documentElement.clientWidth) === "M";
  const neg = item ? negativeMass(item.mean_weekly_units, item.sd_weekly_units) : 0;
  const qMax = item && star ? Math.max(star.q_star * 2, 10) : 100;
  const profitDelta = pol && star && override !== null ? pol.expected_profit - star.expected_profit : null;
  const cp = scen.status === "ready" ? scen.data.policy_check : null;
  return (
    <Track id={def.id} height={def.track} landing={def.landing} className="scene scene-stock">
      <Column>
        <p className="scene-kicker">SIMULATED · COSTS ARE ASSUMPTIONS, DEMAND IS THE LEDGER&apos;S</p>
        <WordReveal text="How many to stock." as="h2" className="serif scene-title" mode={{ kind: "scrub", track: def.id, from: 0.0, to: 0.08 }} id={`${def.id}-title`} tabIndex={-1} data-scene-heading />
        <div className="ctl-row">
          <label className="seg-ctl seg-ctl--select"><span className="seg-ctl__label">ITEM</span>
            <select value={item?.id ?? ""} onChange={(e) => { setItemId(e.target.value); setOverride(null); const it = P!.items.find((i) => i.id === e.target.value)!; setPair({ spec: nvSpec(it, nvPolicy(it, costNow, salNow, model), model) }); }}>
              {P?.items.map((i) => <option key={i.id} value={i.id}>{i.label}</option>)}
            </select></label>
          <Radio<NvModel> label="MODEL" value={mdl} options={["normal", "empirical"] as const} render={(x) => x.toUpperCase()}
            disabled={(x) => (x === "empirical" && item && item.weeks < 26 ? "FEWER THAN 26 SAMPLE WEEKS" : null)} onChange={(m) => { setModel(m); setOverride(null); push(costNow, salNow, m); }} asSelect={mobile} />
        </div>
        <Lower>
          <ArtifactStatus file="newsvendor_params.json" state={art} retry={retry} empty="UNAVAILABLE">{(np) => item && pol && spec && star ? (
            <>
              <label className="slider"><span className="mono-label">COST RATIO {costNow.toFixed(2)}</span>
                <input type="range" aria-label="Cost ratio" min={dflt("cost_ratio")!.range[0]} max={dflt("cost_ratio")!.range[1]} step={0.01} value={costNow} onChange={(e) => { const v = Number(e.target.value); setCost(v); setOverride(null); push(v, salNow, mdl); }} /></label>
              <label className="slider"><span className="mono-label">SALVAGE RATIO {salNow.toFixed(2)}</span>
                <input type="range" aria-label="Salvage ratio" min={dflt("salvage_ratio")!.range[0]} max={dflt("salvage_ratio")!.range[1]} step={0.01} value={salNow} onChange={(e) => { const v = Number(e.target.value); setSal(v); setOverride(null); push(costNow, v, mdl); }} /></label>
              <label className="slider"><span className="mono-label">ORDER OVERRIDE {fmt(override ?? star.q_star)}</span>
                <input type="range" aria-label="Order quantity" min={0} max={Math.round(qMax)} step={1} value={Math.round(override ?? star.q_star)} onChange={(e) => { const v = Number(e.target.value); setOverride(v); push(costNow, salNow, mdl, v); }} /></label>
              <SetNames spec={spec} />
              <p className="ledger-line mono-label">ORDER {fmt(pol.q_star)} · EXPECTED SOLD {fmt(pol.expected_sales)} · LEFT OVER {fmt(pol.expected_leftover)} · SHORT {fmt(pol.expected_shortage)} · CRITICAL RATIO {pol.critical_fractile.toFixed(2)}</p>
              {profitDelta !== null ? <p className="ledger-line mono-label">EXPECTED PROFIT {profitDelta >= 0 ? "+" : ""}{fmt(profitDelta)} GBP VS THE NEWSVENDOR ORDER</p> : null}
              {mdl === "normal" && neg > 0.05 ? <p className="note-line mono-label warn">NORMAL FIT PUTS {(neg * 100).toFixed(0)}% OF DEMAND BELOW ZERO · EMPIRICAL IS SAFER HERE</p> : null}
              {step >= 4 && cp ? <p className="ledger-line mono-label">OVER {cp.weeks_evaluated} WEEKS, ORDERING AT THE NEWSVENDOR QUANTITY EARNS {cp.uplift_pct.toFixed(2)}% MORE THAN ORDERING THE MEAN · {cp.caveat.toUpperCase()}</p> : null}
              <p className="caveat mono-label">{np.disclaimer.toUpperCase()} {cs.status === "ready" ? fs(cs.data, "not_advice").toUpperCase() : ""}</p>
              <HonestyChip tag="SIMULATED" detail="NOT ADVICE" />
            </>
          ) : null}</ArtifactStatus>
          <SourceFoot />
        </Lower>
      </Column>
    </Track>
  );
}

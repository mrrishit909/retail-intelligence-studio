import { useMemo, useState } from "react";
import { Track } from "../scroll/Track";
import { HonestyChip } from "../components/HonestyChip";
import { Radio } from "../components/Radio";
import { WordReveal } from "../components/WordReveal";
import { ArtifactStatus } from "../components/StateUI";
import { useArtifact } from "../data/useArtifact";
import { RFM, type Rfm } from "../app/artifacts";
import { fmt, gbp } from "../app/data";
import { setPair, type PairSpec } from "../app/pairView";
import { Column, Lower, SetNames, SourceFoot, useSteps } from "./common";
import type { SceneDef } from "../app/scenes";
import { classOf } from "../app/geometry";

export type RfmAxes = "R x F" | "R x M" | "F x M";
export type RfmUnit = "customers" | "gbp";
const GRID: Record<RfmAxes, [keyof Rfm["grid"], keyof Rfm["grid"]]> = { "R x F": ["r_by_f_customers", "r_by_f_revenue_gbp"], "R x M": ["r_by_m_customers", "r_by_m_revenue_gbp"], "F x M": ["f_by_m_customers", "f_by_m_revenue_gbp"] };
const NAMES: Record<string, [string, string]> = { R: ["RECENT", "R"], F: ["FREQUENT", "F"], M: ["BIG SPENDERS", "M"] };

/** the two threshold sets and what they share, from the published score grid (rows = first axis score 1..5, columns = second) */
export function rfmSpec(g: number[][], axes: RfmAxes, t1: number, t2: number, unit: RfmUnit): { spec: PairSpec; total: number; detail: string } {
  let a = 0, b = 0, ab = 0, total = 0;
  for (let i = 0; i < 5; i++) for (let j = 0; j < 5; j++) {
    const x = g[i]![j]!;
    total += x;
    const in1 = i + 1 >= t1, in2 = j + 1 >= t2;
    if (in1) a += x;
    if (in2) b += x;
    if (in1 && in2) ab += x;
  }
  const [n1, n2] = axes.split(" x ");
  return {
    spec: { id: `rfm:${axes}:${t1}:${t2}:${unit}`, unit: unit === "gbp" ? "GBP" : "CUSTOMERS", sizeA: a, sizeB: b, shared: ab, labelA: `${NAMES[n1!]![0]} (${n1} ≥ ${t1})`, labelB: `${NAMES[n2!]![0]} (${n2} ≥ ${t2})`, chance: (a * b) / Math.max(1, total), role: "observed", interval: null, hatch: false, refSize: Math.max(a, b, 1), axis: "cohort" },
    total, detail: `${fmt(ab)} OF ${fmt(total)}`,
  };
}

/** S04 Transformation: who matters, from heads to pounds. */
export function S04Matters({ def }: { def: SceneDef }) {
  const [art, retry] = useArtifact(RFM);
  const [axes, setAxes] = useState<RfmAxes>("R x F");
  const [t1, setT1] = useState(4), [t2, setT2] = useState(4);
  const [unit, setUnit] = useState<RfmUnit>("customers");
  const [step, setStep] = useState(0);
  const r = art.status === "ready" ? art.data : null;
  const grid = (u: RfmUnit) => (r ? r.grid[GRID[axes][u === "gbp" ? 1 : 0]] : null);
  const cur = useMemo(() => { const g = grid(unit); return g ? rfmSpec(g, axes, t1, t2, unit) : null; }, [r, axes, t1, t2, unit]); // eslint-disable-line react-hooks/exhaustive-deps
  const push = (ax: RfmAxes, a: number, b: number, u: RfmUnit) => {
    if (!r) return;
    const g = r.grid[GRID[ax][u === "gbp" ? 1 : 0]];
    setPair({ spec: rfmSpec(g, ax, a, b, u).spec, alpha: 1 });
  };
  useSteps(def.id, [0.1, 0.45, 0.8], (s) => {
    setStep(s);
    const u: RfmUnit = s >= 2 ? "gbp" : "customers";
    setUnit(u); push(axes, t1, t2, u);
  });
  const mobile = typeof document !== "undefined" && classOf(document.documentElement.clientWidth) === "M";
  const champs = r?.segments.find((s) => s.segment === "Champions");
  const custShare = cur && unit === "customers" ? (cur.spec.shared / cur.total) * 100 : null;
  return (
    <Track id={def.id} height={def.track} landing={def.landing} className="scene scene-matters">
      <Column>
        <p className="scene-kicker">RECENT · FREQUENT · AND WHAT THEY SPEND</p>
        <WordReveal text="Few in heads. Most in pounds." as="h2" className="serif scene-title" mode={{ kind: "scrub", track: def.id, from: 0.0, to: 0.1 }} id={`${def.id}-title`} tabIndex={-1} data-scene-heading />
        <div className="ctl-row">
          <Radio<RfmAxes> label="PAIR" value={axes} options={["R x F", "R x M", "F x M"] as const} onChange={(a) => { setAxes(a); push(a, t1, t2, unit); }} asSelect={mobile} />
          <Radio<RfmUnit> label="UNIT" value={unit} options={["customers", "gbp"] as const} render={(x) => (x === "gbp" ? "GBP" : "CUSTOMERS")} onChange={(u) => { setUnit(u); push(axes, t1, t2, u); }} asSelect={mobile} />
          <label className="slider"><span className="mono-label">{axes[0]} ≥ {t1}</span><input type="range" min={1} max={5} step={1} value={t1} aria-label="First threshold" onChange={(e) => { const v = Number(e.target.value); setT1(v); push(axes, v, t2, unit); }} /></label>
          <label className="slider"><span className="mono-label">{axes[4]} ≥ {t2}</span><input type="range" min={1} max={5} step={1} value={t2} aria-label="Second threshold" onChange={(e) => { const v = Number(e.target.value); setT2(v); push(axes, t1, v, unit); }} /></label>
        </div>
        <Lower>
          <ArtifactStatus file="rfm.json" state={art} retry={retry} empty="UNAVAILABLE">{(rf) => cur ? (
            <>
              <SetNames spec={cur.spec} />
              {cur.spec.sizeA === 0 || cur.spec.sizeB === 0 ? <p className="state-line">NO CUSTOMER SCORES THAT HIGH ON ONE SIDE</p> : null}
              <p className="ledger-line mono-label">
                {unit === "customers"
                  ? <>{fmt(cur.spec.shared)} OF {fmt(cur.total)} CUSTOMERS ARE BOTH ({custShare!.toFixed(1)}%)</>
                  : <>THEY BRING {gbp(cur.spec.shared)} ({((cur.spec.shared / cur.total) * 100).toFixed(1)}% OF KNOWN-CUSTOMER REVENUE)</>}
              </p>
              {step >= 3 && champs ? <p className="ledger-line mono-label">CHAMPIONS: {(champs.customer_share * 100).toFixed(1)}% OF CUSTOMERS, {(champs.revenue_share * 100).toFixed(1)}% OF REVENUE</p> : null}
              {step >= 3 ? (
                <ul className="step-list" aria-label="Named segments">
                  {rf.segments.map((s) => <li key={s.segment} className={s.segment === "Champions" ? "on" : ""}>{s.segment.toUpperCase()} · {fmt(s.customers)} · {(s.revenue_share * 100).toFixed(1)}% OF REVENUE · {s.rule}</li>)}
                </ul>
              ) : null}
              <p className="note-line mono-label">GUESTS EXCLUDED: {(rf.included.excluded_guest_revenue_share * 100).toFixed(1)}% OF REVENUE · SNAPSHOT {rf.snapshot_date}</p>
              <p className="caveat mono-label">{rf.definition.scoring.toUpperCase()}</p>
              <HonestyChip tag="DERIVED" />
            </>
          ) : null}</ArtifactStatus>
          <SourceFoot />
        </Lower>
      </Column>
    </Track>
  );
}

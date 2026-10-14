import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Track } from "../scroll/Track";
import { HonestyChip } from "../components/HonestyChip";
import { Radio } from "../components/Radio";
import { Sheet } from "../components/Sheet";
import { ArtifactStatus } from "../components/StateUI";
import { useArtifact } from "../data/useArtifact";
import { BASKETS, COHORTS, NVPARAMS, RFM } from "../app/artifacts";
import { fmt, useCore } from "../app/data";
import { setPair, pairView, type PairSpec } from "../app/pairView";
import { useActiveScene } from "../scroll/hooks";
import { drawn } from "../app/PairLayer";
import { pairFor } from "../model/euler";
import { cohortSpec } from "./S03bBack";
import { rfmSpec, type RfmAxes } from "./S04Matters";
import { nvPolicy, nvSpec } from "./S05Stock";
import { SetNames, SourceFoot, usePairView, fmtUnit } from "./common";
import { heroSpec } from "../app/specs";
import type { SceneDef } from "../app/scenes";
import { classOf } from "../app/geometry";

type Kind = "products" | "cohort" | "customers" | "stock";
const GRID: Record<RfmAxes, "r_by_f_customers" | "r_by_m_customers" | "f_by_m_customers"> = { "R x F": "r_by_f_customers", "R x M": "r_by_m_customers", "F x M": "f_by_m_customers" };

/** THE COUNTER: any two sets the ledger can honestly compare, one store, one pair. */
export function Counter({ def }: { def: SceneDef }) {
  const cs = useCore();
  const [bk, retryB] = useArtifact(BASKETS, false), [co, loadCo] = useArtifact(COHORTS, false), [rf, loadRf] = useArtifact(RFM, false), [nv, loadNv] = useArtifact(NVPARAMS, false);
  const active = useActiveScene();
  const [kind, setKind] = useState<Kind>("products");
  const [a, setA] = useState(""), [b, setB] = useState("");
  const [cohort, setCohort] = useState(0), [month, setMonth] = useState(12);
  const [axes, setAxes] = useState<RfmAxes>("R x F"), [t1, setT1] = useState(4), [t2, setT2] = useState(4);
  const [item, setItem] = useState(0);
  const v = usePairView();
  const wasActive = useRef(false);
  const B = bk.status === "ready" ? bk.data : null, C = co.status === "ready" ? co.data : null, R = rf.status === "ready" ? rf.data : null, N = nv.status === "ready" ? nv.data : null;
  useEffect(() => {
    if (active === def.id && !wasActive.current) { void retryB(); setPair({ alpha: 1, inspected: null, echoStart: 0 }); }
    wasActive.current = active === def.id;
  }, [active, def.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const skuA = a || B?.hero.a || "", skuB = b || B?.hero.b || "";
  const builtAll = useMemo((): { spec: PairSpec | null; note: string } => {
    let note = "";
    if (kind === "products" && B) {
      const na = B.nodes.find((n) => n.sku === skuA), nb = B.nodes.find((n) => n.sku === skuB);
      if (!na || !nb || skuA === skuB) return { spec: null, note };
      const e = B.edges.find((x) => (x.a === skuA && x.b === skuB) || (x.a === skuB && x.b === skuA));
      if (!e) note = `FEWER THAN ${B.params.support_count_min} BASKETS TOGETHER, OR NOT PUBLISHED`;
      const spec: PairSpec = { id: `ctr:p:${skuA}:${skuB}`, unit: "BASKETS", sizeA: na.baskets, sizeB: nb.baskets, shared: e ? e.count : 0, labelA: na.description, labelB: nb.description, chance: e ? (na.baskets * nb.baskets) / B.params.baskets : null, role: "observed", interval: null, hatch: false, refSize: Math.max(na.baskets, nb.baskets), axis: "h" };
      return { spec, note };
    }
    if (kind === "cohort" && C) return { spec: cohortSpec(C, cohort, month, "customers").spec, note: cohortSpec(C, cohort, month, "customers").note };
    if (kind === "customers" && R) return { spec: rfmSpec(R.grid[GRID[axes]], axes, t1, t2, "customers").spec, note };
    if (kind === "stock" && N) { const it = N.items[item]!; return { spec: nvSpec(it, nvPolicy(it, N.assumptions.find((x) => x.id === "cost_ratio")!.value, N.assumptions.find((x) => x.id === "salvage_ratio")!.value, "normal"), "normal"), note }; }
    return { spec: cs.status === "ready" ? heroSpec(cs.data) : null, note };
  }, [kind, B, C, R, N, skuA, skuB, cohort, month, axes, t1, t2, item, cs]);
  const built = builtAll.spec, note = builtAll.note;
  useEffect(() => { if (active === def.id && built) setPair({ spec: built }); }, [built, active, def.id]);
  // click a set: anchor, partner or overlap
  useEffect(() => {
    if (active !== def.id) return;
    const on = (e: MouseEvent) => {
      const el = e.target as HTMLElement | null;
      if (el?.closest("button, a, input, select, label, summary, .counter-side, .inspector, .sheet, .nav-bar, .menu-pill, .menu-panel")) return;
      const d = drawn; const sp = pairView.get().spec;
      if (!d.pair || !sp) return;
      const p = d.pair;
      const ax = d.cx - 0, ay = d.cy; void ax; void ay;
      const gx = geoOf();
      const inA = Math.hypot(e.clientX - gx.ax, e.clientY - gx.ay) <= p.ra, inB = Math.hypot(e.clientX - gx.bx, e.clientY - gx.by) <= p.rb;
      setPair({ inspected: inA && inB ? "overlap" : inA ? "anchor" : inB ? "partner" : null });
    };
    const geoOf = () => {
      const p = drawn.pair!;
      const a2 = p.kind === "identical" ? 0 : p.kind === "disjoint" ? p.ra + (p.d - p.ra - p.rb) / 2 : p.d > 0 ? (p.d * p.d + p.ra * p.ra - p.rb * p.rb) / (2 * p.d) : 0;
      const ax = drawn.cx - a2 * drawn.ux, ay = drawn.cy - a2 * drawn.uy;
      return { ax, ay, bx: ax + p.d * drawn.ux, by: ay + p.d * drawn.uy };
    };
    addEventListener("click", on);
    return () => removeEventListener("click", on);
  }, [active, def.id]);
  const mobile = typeof document !== "undefined" && classOf(document.documentElement.clientWidth) === "M";
  const spec = v.spec;
  const insp = v.inspected;
  const inspBody = spec && insp ? (
    <div className="inspector__body">
      <p className="mono-label">{insp === "overlap" ? "WHAT THEY SHARE" : insp === "anchor" ? "ANCHOR SET" : "PARTNER SET"}</p>
      <h3 className="serif insp-title">{insp === "overlap" ? `${fmtUnit(spec.shared, spec.unit)} IN COMMON` : insp === "anchor" ? spec.labelA : spec.labelB}</h3>
      <p className="mono-label">{insp === "anchor" ? fmtUnit(spec.sizeA, spec.unit) : insp === "partner" ? fmtUnit(spec.sizeB, spec.unit) : `${((spec.shared / Math.min(spec.sizeA, spec.sizeB)) * 100).toFixed(1)}% OF THE SMALLER SET`}</p>
      <p className="mono-label">ONLY IN {spec.labelA.toUpperCase()}: {fmtUnit(Math.max(0, spec.sizeA - spec.shared), spec.unit)}</p>
      <p className="mono-label">ONLY IN {spec.labelB.toUpperCase()}: {fmtUnit(Math.max(0, spec.sizeB - spec.shared), spec.unit)}</p>
      <button type="button" className="btn-square" onClick={() => setPair({ inspected: null })}>CLOSE</button>
    </div>
  ) : null;
  const names = B?.nodes ?? [];
  const pairKind = spec ? `${kind.toUpperCase()} · AREA = ${spec.unit} · ${kind === "stock" ? "SIMULATED" : kind === "products" ? "DERIVED" : "DERIVED"}` : "";
  void pairFor;
  return (
    <Track id={def.id} height="auto" landing={0} className="scene scene-counter">
      <div className="counter-wrap">
        <div className="counter-head">
          <p className="scene-kicker">THE COUNTER</p>
          <h2 id={`${def.id}-title`} tabIndex={-1} data-scene-heading className="serif scene-title">Put any two things side by side.</h2>
          <p className="mono-label">{pairKind}</p>
        </div>
        <div className="counter-side">
          <div className="counter-rail" role="group" aria-label="Controls">
            <Radio<Kind> label="KIND" value={kind} options={["products", "cohort", "customers", "stock"] as const} render={(x) => x.toUpperCase()} onChange={(k) => { setKind(k); if (k === "cohort") void loadCo(); if (k === "customers") void loadRf(); if (k === "stock") void loadNv(); }} asSelect={mobile} />
            {kind === "products" ? (
              <>
                <label className="seg-ctl seg-ctl--select"><span className="seg-ctl__label">A</span><input list="sku-list" className="rail-input" placeholder="SEARCH A PRODUCT" defaultValue="" aria-label="Product A" onChange={(e) => { const n = names.find((x) => x.description.toLowerCase() === e.target.value.toLowerCase()); if (n) setA(n.sku); }} /></label>
                <label className="seg-ctl seg-ctl--select"><span className="seg-ctl__label">B</span><input list="sku-list" className="rail-input" placeholder="SEARCH A PRODUCT" defaultValue="" aria-label="Product B" onChange={(e) => { const n = names.find((x) => x.description.toLowerCase() === e.target.value.toLowerCase()); if (n) setB(n.sku); }} /></label>
                <datalist id="sku-list">{names.map((n) => <option key={n.sku} value={n.description} />)}</datalist>
              </>
            ) : null}
            {kind === "cohort" && C ? (
              <>
                <label className="seg-ctl seg-ctl--select"><span className="seg-ctl__label">COHORT</span><select value={cohort} onChange={(e) => setCohort(Number(e.target.value))}>{C.cohort_months.map((m, i) => <option key={m} value={i}>{m}</option>)}</select></label>
                <label className="slider"><span className="mono-label">MONTH {month}</span><input type="range" min={0} max={24} value={month} aria-label="Month" onChange={(e) => setMonth(Number(e.target.value))} /></label>
              </>
            ) : null}
            {kind === "customers" ? (
              <>
                <Radio<RfmAxes> label="PAIR" value={axes} options={["R x F", "R x M", "F x M"] as const} onChange={setAxes} asSelect={mobile} />
                <label className="slider"><span className="mono-label">{axes[0]} ≥ {t1}</span><input type="range" min={1} max={5} value={t1} aria-label="First threshold" onChange={(e) => setT1(Number(e.target.value))} /></label>
                <label className="slider"><span className="mono-label">{axes[4]} ≥ {t2}</span><input type="range" min={1} max={5} value={t2} aria-label="Second threshold" onChange={(e) => setT2(Number(e.target.value))} /></label>
              </>
            ) : null}
            {kind === "stock" && N ? (
              <label className="seg-ctl seg-ctl--select"><span className="seg-ctl__label">ITEM</span><select value={item} onChange={(e) => setItem(Number(e.target.value))}>{N.items.map((i, k) => <option key={i.id} value={k}>{i.label}</option>)}</select></label>
            ) : null}
            <button type="button" className="btn-square" onClick={() => { setKind("products"); setA(""); setB(""); setCohort(0); setMonth(12); setAxes("R x F"); setT1(4); setT2(4); setItem(0); }}>RESET</button>
          </div>
          <div className="counter-read">
            <ArtifactStatus file="baskets.json" state={bk} retry={retryB} empty="UNAVAILABLE">{() => null}</ArtifactStatus>
            {spec ? (
              <>
                <SetNames spec={spec} />
                <p className="ledger-line mono-label" aria-live="polite">BOTH: {fmtUnit(spec.shared, spec.unit)}{spec.chance !== null ? ` · CHANCE WOULD GIVE ${fmt(spec.chance)}` : ""}</p>
                {note ? <p className="note-line mono-label">{note}</p> : null}
                <HonestyChip tag={kind === "stock" ? "SIMULATED" : "DERIVED"} />
              </>
            ) : <p className="state-line">CHOOSE TWO DIFFERENT PRODUCTS</p>}
            <p className="note-line mono-label">EVERY AREA IS A PUBLISHED COUNT. NOTHING HERE IS ADVICE. CLICK A SET FOR ITS INSPECTOR.</p>
          </div>
          <SourceFoot />
        </div>
      </div>
      {insp && typeof document !== "undefined" ? (classOf(document.documentElement.clientWidth) === "D" ? createPortal(<aside className="inspector" aria-label="Pair inspector">{inspBody}</aside>, document.body) : <Sheet open onClose={() => setPair({ inspected: null })} title="Pair inspector">{inspBody}</Sheet>) : null}
    </Track>
  );
}

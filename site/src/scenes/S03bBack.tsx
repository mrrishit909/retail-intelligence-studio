import { useMemo, useState } from "react";
import { Track } from "../scroll/Track";
import { HonestyChip } from "../components/HonestyChip";
import { Radio } from "../components/Radio";
import { WordReveal } from "../components/WordReveal";
import { ArtifactStatus } from "../components/StateUI";
import { useArtifact } from "../data/useArtifact";
import { COHORTS, type Cohorts } from "../app/artifacts";
import { fmt, fv, useCore } from "../app/data";
import { setPair, type PairSpec } from "../app/pairView";
import { Column, Lower, SourceFoot, useSteps } from "./common";
import type { SceneDef } from "../app/scenes";
import { classOf } from "../app/geometry";

export type CohortUnit = "customers" | "revenue";
export function cohortSpec(co: Cohorts, c: number, m: number, unit: CohortUnit): { spec: PairSpec | null; note: string } {
  const size = co.sizes[c]!, ret = co.retention[c]?.[m];
  const cal = c + m;
  if (cal >= co.active_customers.length || ret === null || ret === undefined) return { spec: null, note: "NOT YET OBSERVED" };
  const label = `COHORT ${co.cohort_months[c]}`;
  if (unit === "customers") {
    const retained = Math.round(ret * size);
    return {
      spec: { id: `cohort:${c}:${m}:c`, unit: "CUSTOMERS", sizeA: size, sizeB: co.active_customers[cal]!, shared: retained, labelA: label, labelB: `ACTIVE IN ${co.cohort_months[Math.min(cal, co.cohort_months.length - 1)]}`, chance: null, role: "observed", interval: null, hatch: false, refSize: Math.max(...co.sizes), axis: "cohort" },
      note: m === 0 && Math.abs(size - co.active_customers[cal]!) / size < 0.05 ? "ALMOST THE SAME SET: IN THE FIRST MONTH, NEARLY EVERY ACTIVE CUSTOMER IS NEW" : "",
    };
  }
  const rr = co.revenue_retention[c]?.[m];
  if (rr === null || rr === undefined) return { spec: null, note: "NOT YET OBSERVED" };
  return {
    spec: { id: `cohort:${c}:${m}:r`, unit: "GBP", sizeA: 100, sizeB: 100 * rr, shared: Math.min(100, 100 * rr), labelA: `${label} MONTH 0 = 100`, labelB: `SAME COHORT, MONTH ${m}`, chance: null, role: "observed", interval: null, hatch: false, refSize: 100, axis: "cohort" },
    note: "REVENUE INDEX, MONTH 0 = 100 (NOT POUNDS)",
  };
}

/** S03b Mechanism II: coming back. 24 monthly steps for the chosen cohort. */
export function S03bBack({ def }: { def: SceneDef }) {
  const [art, retry] = useArtifact(COHORTS);
  const cs = useCore();
  const [cohort, setCohort] = useState(0);
  const [month, setMonth] = useState(12);
  const [unit, setUnit] = useState<CohortUnit>("customers");
  const co = art.status === "ready" ? art.data : null;
  const cur = useMemo(() => (co ? cohortSpec(co, cohort, month, unit) : { spec: null, note: "" }), [co, cohort, month, unit]);
  const apply = (c: number, m: number, u: CohortUnit) => { if (!co) return; const r = cohortSpec(co, c, m, u); setPair({ spec: r.spec ?? cohortSpec(co, c, 1, u).spec, alpha: 1 }); };
  useSteps(def.id, [], (_s, p) => {
    const m = Math.min(24, Math.max(1, Math.round(1 + ((p - 0.04) / 0.92) * 23)));
    setMonth(m);
    apply(cohort, m, unit);
  });
  const maxM = co ? co.offsets.length - 1 : 24;
  const sel = (c: number, m: number, u: CohortUnit) => { setCohort(c); setMonth(m); setUnit(u); apply(c, m, u); };
  const mobile = typeof document !== "undefined" && classOf(document.documentElement.clientWidth) === "M";
  const spec = cur.spec;
  const guestShare = cs.status === "ready" ? (fv(cs.data, "guest_revenue_share") * 100).toFixed(1) : "";
  return (
    <Track id={def.id} height={def.track} landing={def.landing} className="scene scene-back">
      <Column>
        <p className="scene-kicker">A COHORT AND A LATER MONTH · WHAT THEY SHARE IS WHO STAYED</p>
        <WordReveal text="Who came back." as="h2" className="serif scene-title" mode={{ kind: "scrub", track: def.id, from: 0.0, to: 0.06 }} id={`${def.id}-title`} tabIndex={-1} data-scene-heading />
        <div className="ctl-row">
          <label className="seg-ctl seg-ctl--select"><span className="seg-ctl__label">COHORT</span>
            <select value={cohort} onChange={(e) => sel(Number(e.target.value), month, unit)}>
              {co?.cohort_months.map((m, i) => <option key={m} value={i} disabled={co.sizes[i]! < co.min_cohort_size}>{m} · {co.sizes[i]}{co.sizes[i]! < co.min_cohort_size ? ` · FEWER THAN ${co.min_cohort_size}` : ""}</option>)}
            </select></label>
          <Radio<CohortUnit> label="UNIT" value={unit} options={["customers", "revenue"] as const} render={(x) => (x === "customers" ? "CUSTOMERS" : "REVENUE")} onChange={(u) => sel(cohort, month, u)} asSelect={mobile} />
          <button type="button" className="btn-square" aria-label="Earlier month" onClick={() => sel(cohort, Math.max(0, month - 1), unit)}>◀</button>
          <button type="button" className="btn-square" aria-label="Later month" onClick={() => sel(cohort, Math.min(maxM, month + 1), unit)}>▶</button>
        </div>
        <Lower>
          <ArtifactStatus file="cohorts.json" state={art} retry={retry} empty="UNAVAILABLE">{(c) => (
            <>
              <p className="ledger-line mono-label">COHORT: FIRST BOUGHT {c.cohort_months[cohort]} · {fmt(c.sizes[cohort]!)} CUSTOMERS · MONTH {month} OF {maxM}</p>
              {spec && unit === "customers" ? (
                <>
                  <p className="ledger-line mono-label">STILL BUYING IN {c.cohort_months[Math.min(cohort + month, c.cohort_months.length - 1)]}: {fmt(spec.shared)} ({((spec.shared / spec.sizeA) * 100).toFixed(0)}%)</p>
                  <p className="ledger-line mono-label">ALL ACTIVE CUSTOMERS THAT MONTH: {fmt(spec.sizeB)}</p>
                </>
              ) : spec ? <p className="ledger-line mono-label">THE COHORT&apos;S REVENUE IN MONTH {month}: {spec.sizeB.toFixed(0)} VS 100 IN MONTH 0</p> : <p className="state-line">NOT YET OBSERVED · NO OVERLAP IS DRAWN</p>}
              {cur.note ? <p className="note-line mono-label">{cur.note}</p> : null}
              <p className="caveat mono-label">{c.right_censoring.toUpperCase()}</p>
              <p className="caveat mono-label">KNOWN CUSTOMERS ONLY · GUESTS ARE {guestShare}% OF REVENUE</p>
              <HonestyChip tag="DERIVED" />
            </>
          )}</ArtifactStatus>
          <SourceFoot />
        </Lower>
      </Column>
    </Track>
  );
}

import { useEffect, useRef, type ReactNode } from "react";
import { getActive, getProgress } from "../scroll/engine";
import { useActiveScene, useLatest, useProgress } from "../scroll/hooks";
import { stepState } from "../motion/progress";
import { useSyncExternalStore } from "react";
import { pairView, setPair, type PairSpec } from "../app/pairView";
import { fmt, gbp } from "../app/data";
import { chanceShared, liftOf } from "../model/euler";

/** Steps with hysteresis for a pinned scene; applied on every tick of the ACTIVE scene and again when a direct jump activates it. */
export function useSteps(id: string, thresholds: readonly number[], apply: (step: number, p: number) => void) {
  const prev = useRef(0);
  const cb = useLatest(apply);
  useProgress(id, (p) => {
    if (getActive() !== id) return;
    prev.current = stepState(prev.current, p, thresholds);
    cb.current(prev.current, p);
  });
  const active = useActiveScene();
  useEffect(() => {
    if (active !== id) return;
    const p = getProgress(id);
    prev.current = thresholds.filter((t) => p >= t).length;
    cb.current(prev.current, p);
  }, [active, id]); // eslint-disable-line react-hooks/exhaustive-deps
}

export function Column({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`scene-col ${className}`}>{children}</div>;
}
/** inline on D; a scrim panel above the nav on T and M (text never sits on the light) */
export function Lower({ children }: { children: ReactNode }) { return <div className="scene-lower">{children}</div>; }
export const SourceFoot = () => <p className="scene-foot mono-label">UCI ONLINE RETAIL II · CC BY 4.0 · DERIVED AGGREGATES · ANALYTICAL EXAMPLES, NOT ADVICE</p>;

const unitWord = { BASKETS: "BASKETS", CUSTOMERS: "CUSTOMERS", UNITS: "UNITS", GBP: "GBP" } as const;
export const fmtUnit = (n: number, u: PairSpec["unit"]) => (u === "GBP" ? gbp(n) : `${fmt(n)} ${unitWord[u]}`);

/** the two set names and sizes, outside the light, with the colour of their role */
export function SetNames({ spec }: { spec: PairSpec }) {
  return (
    <ul className="set-names">
      <li><i className="dot dot--a" />{spec.labelA.toUpperCase()} · {fmtUnit(spec.sizeA, spec.unit)}</li>
      <li><i className={`dot ${spec.role === "predicted" ? "dot--p" : "dot--b"}`} />{spec.labelB.toUpperCase()} · {fmtUnit(spec.sizeB, spec.unit)}</li>
    </ul>
  );
}
/** BOTH · CHANCE WOULD GIVE · LIFT (population-drawn pairs only) */
export function Readout({ spec, population }: { spec: PairSpec; population?: number }) {
  const chance = spec.chance ?? (population ? chanceShared(spec.sizeA, spec.sizeB, population) : null);
  return (
    <p className="readout mono-label">
      BOTH: {fmtUnit(spec.shared, spec.unit)}
      {chance !== null && population ? <> · CHANCE WOULD GIVE {fmt(chance)} · LIFT {liftOf(spec.shared, spec.sizeA, spec.sizeB, population).toFixed(1)}</> : null}
    </p>
  );
}
export function usePairView() { return useSyncExternalStore(pairView.subscribe, pairView.get, pairView.get); }
export { setPair };

/** scene-owned state a scene clears when it takes the pair back */
export const DEFAULT_PAIR_RESET = { inspected: null, echoStart: 0 } as const;

/** The one store the pair, labels, readouts and inspector derive from. */
import { store } from "../state/store";

export type Unit = "BASKETS" | "CUSTOMERS" | "UNITS" | "GBP";
export type CameraName = "G0" | "G1" | "G2" | "G5";
export interface PairSpec {
  id: string;
  unit: Unit;
  sizeA: number; sizeB: number; shared: number;
  labelA: string; labelB: string;
  /** chance overlap (the ghost position), or null when the sets are not drawn from one population */ chance: number | null;
  role: "observed" | "predicted";
  /** partner soft edge as a size interval [lo, hi] (PREDICTED), or null */ interval: [number, number] | null;
  /** a size that is not estimable: hatch, never light */ hatch: boolean;
  /** the largest anchor size the scene will show: k = pi R^2 / refSize */ refSize: number;
  axis: "h" | "diag" | "cohort";
}
export interface PairState {
  spec: PairSpec | null;
  camera: CameraName;
  alpha: number;
  /** performance.now() when the S08 echo started, 0 when idle */ echoStart: number;
  inspected: "anchor" | "partner" | "overlap" | null;
}
export const pairView = store<PairState>({ spec: null, camera: "G0", alpha: 1, echoStart: 0, inspected: null });
export function setPair(p: Partial<PairState>) {
  const cur = pairView.get() as unknown as Record<string, unknown>;
  for (const k of Object.keys(p)) {
    const a = cur[k], b = (p as Record<string, unknown>)[k];
    if (a !== b && JSON.stringify(a) !== JSON.stringify(b)) { pairView.set(p); return; }
  }
}

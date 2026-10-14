import { useEffect, useRef } from "react";
import { drawPair } from "../graphics/commonGround";
import { pairFor } from "../model/euler";

/** a small Common Ground pair inside a card (S02 card 2, S07 mini-visuals): same geometry, own k */
export function MiniPair({ a, b, shared, role = "observed", height = 120 }: { a: number; b: number; shared: number; role?: "observed" | "predicted"; height?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const cv = ref.current!, ctx = cv.getContext("2d")!;
    const w = cv.clientWidth || 300, dpr = Math.min(2, devicePixelRatio || 1);
    cv.width = Math.round(w * dpr); cv.height = Math.round(height * dpr);
    const R = height * 0.42, k = (Math.PI * R * R) / Math.max(a, b);
    const pair = pairFor(a, b, shared, k);
    drawPair(ctx, w, height, dpr, { pair, cx: w / 2, cy: height / 2, ux: 1, uy: 0, role, ghost: null, soft: 0, hatch: false, alpha: 1, lightOn: 1, overlap: 1 });
  }, [a, b, shared, role, height]);
  return <canvas ref={ref} className="mini-pair" style={{ height }} role="img" aria-label={`Two sets of ${a} and ${b}, sharing ${shared}`} />;
}

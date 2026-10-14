import { useEffect, useRef, useSyncExternalStore } from "react";
import { addFrame } from "../motion/loop";
import { getProgress } from "../scroll/engine";
import { useActiveScene } from "../scroll/hooks";
import { drawPair } from "../graphics/commonGround";
import { pairFor, type Pair } from "../model/euler";
import { camera, mixCam, type Cam } from "./geometry";
import { pairView, type PairSpec } from "./pairView";
import { intro, introTime } from "./intro";
import { pullAt, echoAt, ECHO_TOTAL } from "./timeline";
import { motionEnabled } from "../state/motion";
import { setPair } from "./pairView";

/** the geometry the layer draws, exported for the labels and the tests (areas drawn == numbers shown) */
export const drawn = { pair: null as Pair | null, cx: 0, cy: 0, ux: 1, uy: 0, k: 1, spec: null as PairSpec | null, alpha: 1, chancePair: null as Pair | null };

export function camFor(active: string | null, p: number, w: number, h: number, spec: PairSpec | null): Cam {
  const ax = spec?.axis ?? "h";
  switch (active) {
    case null: case "pattern": return mixCam(camera("G0", w, h, ax), camera("G1", w, h, ax), p / 0.4);
    case "ledger": case "evidence": return camera("G1", w, h, ax);
    case "counter": return camera("G5", w, h, ax);
    case "closing": return camera("G0", w, h, ax);
    default: return camera("G2", w, h, ax);
  }
}
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lg = (a: number, b: number, t: number) => (a > 0 && b > 0 ? Math.exp(Math.log(a) + (Math.log(b) - Math.log(a)) * t) : lerp(a, b, t));

export function PairLayer() {
  const ref = useRef<HTMLCanvasElement>(null);
  const v = useSyncExternalStore(pairView.subscribe, pairView.get, pairView.get);
  const active = useActiveScene();
  const activeRef = useRef(active); const viewRef = useRef(v);
  useEffect(() => { activeRef.current = active; }, [active]);
  useEffect(() => { viewRef.current = v; }, [v]);
  useEffect(() => {
    const cv = ref.current!, ctx = cv.getContext("2d")!;
    let W = 0, H = 0, dpr = 1, last = 0, sig = "";
    // eased current state of the pair
    let cur: { a: number; b: number; s: number; cx: number; cy: number; R: number; ux: number; uy: number; id: string } | null = null;
    const size = () => {
      W = document.documentElement.clientWidth; H = innerHeight;
      dpr = Math.min(W < 768 ? 1.5 : 2, devicePixelRatio || 1);
      cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
      cv.style.width = `${W}px`; cv.style.height = `${H}px`; sig = ""; cur = null;
    };
    size(); addEventListener("resize", size);
    const off = addFrame((now) => {
      const dt = last ? Math.min(100, now - last) : 16; last = now;
      const vv = viewRef.current, a = activeRef.current, spec = vv.spec;
      const motion = motionEnabled();
      if (!spec) { ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H); drawn.pair = null; return; }
      const playing = intro.playing && motion;
      const t = playing ? introTime(now) : 99999;
      const p = getProgress("pattern");
      const cam = camFor(a, p, W, H, spec);
      const targetBase = { a: spec.sizeA, b: spec.sizeB, s: spec.shared };
      const k = (Math.PI * cam.R * cam.R) / Math.max(1, spec.refSize);
      let echo = vv.echoStart > 0 ? now - vv.echoStart : -1;
      if (echo > ECHO_TOTAL) { echo = -1; setPair({ echoStart: 0 }); }
      const ease = motion && cur && cur.id === spec.id ? 1 - Math.exp(-dt / 160) : 1;
      const c = cur && cur.id === spec.id ? cur : null;
      const next = {
        id: spec.id,
        a: c ? lg(c.a, targetBase.a, ease) : targetBase.a, b: c ? lg(c.b, targetBase.b, ease) : targetBase.b, s: c ? lg(c.s, targetBase.s, ease) : targetBase.s,
        cx: c ? lerp(c.cx, cam.chord[0], 1 - Math.exp(-dt / 90)) : cam.chord[0], cy: c ? lerp(c.cy, cam.chord[1], 1 - Math.exp(-dt / 90)) : cam.chord[1],
        R: c ? lg(c.R, cam.R, 1 - Math.exp(-dt / 90)) : cam.R, ux: cam.axis[0], uy: cam.axis[1],
      };
      cur = next;
      const settled = Math.abs(next.a - targetBase.a) + Math.abs(next.b - targetBase.b) + Math.abs(next.s - targetBase.s) < 1e-6 * (targetBase.a + 1) && Math.abs(next.cx - cam.chord[0]) < 0.3 && Math.abs(next.R - cam.R) < 0.3;
      const chance = spec.chance;
      // the pull: from the chance position to the real overlap
      let pull = 1, light = 1, overlap = 1;
      if (playing && chance !== null) { const ph = pullAt(t); pull = ph.pull; light = ph.light; overlap = ph.overlap; }
      else if (echo >= 0 && chance !== null) pull = echoAt(echo).pull;
      const sharedNow = chance !== null ? lg(chance, next.s, pull) : next.s;
      const kk = (Math.PI * next.R * next.R) / Math.max(1, spec.refSize);
      void k;
      const pair = pairFor(next.a, next.b, sharedNow, kk);
      const ghost = chance !== null ? pairFor(next.a, next.b, chance, kk) : null;
      const soft = spec.interval ? Math.abs(Math.sqrt(spec.interval[1] * kk / Math.PI) - Math.sqrt(spec.interval[0] * kk / Math.PI)) / 2 : 0;
      const animating = playing || echo >= 0 || !settled || (playing === false && pull < 1);
      const key = `${spec.id}|${animating ? Math.round(now / 16) : 0}|${W}x${H}|${vv.alpha}|${cam.chord[0].toFixed(1)}|${cam.R.toFixed(1)}|${spec.shared}|${spec.sizeA}|${spec.sizeB}|${spec.hatch}`;
      if (key === sig && !animating) return;
      sig = key;
      Object.assign(drawn, { pair, cx: next.cx, cy: next.cy, ux: next.ux, uy: next.uy, k: kk, spec, alpha: vv.alpha, chancePair: ghost });
      drawPair(ctx, W, H, dpr, { pair, cx: next.cx, cy: next.cy, ux: next.ux, uy: next.uy, role: spec.role, ghost: chance !== null ? ghost : null, soft, hatch: spec.hatch, alpha: vv.alpha, lightOn: light, overlap });
    }, 30);
    return () => { off(); removeEventListener("resize", size); };
  }, []);
  return <canvas ref={ref} className="pair-layer" aria-hidden="true" />;
}

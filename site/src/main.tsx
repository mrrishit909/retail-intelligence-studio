import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "lenis/dist/lenis.css";
import "./styles/app.css";
import "./styles/scenes.css";
import { ErrorBoundary } from "./app/ErrorBoundary";
import { App } from "./app/App";
import { getActive, getProgress, jumpTo, startEngine } from "./scroll/engine";
import { intro } from "./app/intro";
import { getCore } from "./app/data";
import { pairView, setPair } from "./app/pairView";
import { drawn } from "./app/PairLayer";
import { lensArea } from "./model/euler";

// Test and evidence hook (rs = Retail Studio): the same instant-jump path the nav uses.
Object.assign(window, {
  __rs: {
    jumpTo, getProgress,
    freeze: (t: number) => { intro.frozen = t; if (t >= 0) intro.playing = true; },
    introStats: () => ({ playing: intro.playing }),
    debug: () => ({ frames: 2, scene: getActive() }),
    view: () => ({ ...pairView.get() }),
    set: (p: Parameters<typeof setPair>[0]) => setPair(p),
    /** what is drawn: radii, distance, and the overlap area in units, for the areas-drawn-equal-numbers-shown check */
    drawn: () => {
      const d = drawn;
      if (!d.pair || !d.spec) return null;
      const area = lensArea(d.pair.ra, d.pair.rb, d.pair.d) / d.k;
      return { ra: d.pair.ra, rb: d.pair.rb, d: d.pair.d, k: d.k, kind: d.pair.kind, overlapUnits: area, sizeA: (Math.PI * d.pair.ra ** 2) / d.k, sizeB: (Math.PI * d.pair.rb ** 2) / d.k, spec: d.spec.id, cx: d.cx, cy: d.cy };
    },
    discs: () => (drawn.pair && drawn.alpha >= 0.3 ? [{ cx: drawn.cx, cy: drawn.cy, R: drawn.pair.ra }] : []),
    marks: () => [] as { name: string; x: number; y: number; w: number; h: number }[],
    core: () => { const s = getCore(); return s.status; },
  },
});

startEngine();
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
);

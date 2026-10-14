import { useRef } from "react";
import { Track } from "../scroll/Track";
import { WordReveal } from "../components/WordReveal";
import { getActive, jumpTo } from "../scroll/engine";
import { useProgress } from "../scroll/hooks";
import { setPair, pairView } from "../app/pairView";
import { motionEnabled } from "../state/motion";
import { LINKS, type SceneDef } from "../app/scenes";
import { useCore } from "../app/data";

/** S08 Conclusion: the visitor's last pair at G0, pushed back to chance and pulled again (the echo). */
export function S08Closing({ def, onReplay }: { def: SceneDef; onReplay: () => void }) {
  const cs = useCore();
  const c = cs.status === "ready" ? cs.data : null;
  const armed = useRef(true);
  useProgress(def.id, (p) => {
    if (getActive() !== def.id) return;
    if (pairView.get().alpha !== 1 || pairView.get().inspected) setPair({ alpha: 1, inspected: null });
    if (p >= 0.7 && armed.current) { armed.current = false; if (motionEnabled()) setPair({ echoStart: performance.now() }); }
    if (p < 0.68) armed.current = true;
  });
  return (
    <Track id={def.id} height={def.track} landing={def.landing} className="scene scene-closing">
      <div className="s08-scrim" aria-hidden="true" />
      <WordReveal as="h2" id={`${def.id}-title`} tabIndex={-1} data-scene-heading className="serif s08-para" mode={{ kind: "scrub", track: def.id, from: 0.35, to: 0.65 }}
        text="Two bags, a cohort and a December, a forecast and a week of sales, a shelf and its demand. Every pattern in a shop is two groups and what they share, and the only light worth trusting is the part chance can't explain." />
      <ul className="s08-links">
        <li><button type="button" className="text-btn" onClick={() => jumpTo("counter", undefined, { push: true, focus: true })}>→ OPEN THE COUNTER</button></li>
        <li><button type="button" className="text-btn" onClick={onReplay}>→ REPLAY THE INTRO</button></li>
        <li><a className="text-btn" href={`${LINKS.source}/blob/main/docs/METHODOLOGY.md`}>→ READ THE METHODOLOGY</a></li>
        <li><a className="text-btn" href={LINKS.source}>→ SOURCE CODE</a></li>
      </ul>
      <footer className="s08-foot mono-label">
        {c ? <span>{c.meta.source.attribution.toUpperCase()} DOI {c.meta.source.doi}. CC BY 4.0. {c.meta.disclaimers.join(" ").toUpperCase()} SEED {c.meta.engine.seed}.</span> : null}
      </footer>
    </Track>
  );
}

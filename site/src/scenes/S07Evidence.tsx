import { useState } from "react";
import { Track } from "../scroll/Track";
import { HonestyChip } from "../components/HonestyChip";
import { useArtifact } from "../data/useArtifact";
import { BACKTEST, CLV, ELAST, RECON } from "../app/artifacts";
import { fmt, useCore } from "../app/data";
import { DEFAULT_PAIR_RESET } from "./common";
import { useSteps } from "./common";
import { setPair } from "../app/pairView";
import { heroSpec } from "../app/specs";
import type { SceneDef } from "../app/scenes";

/** S07 Evidence: the argument stack, seven objections and answers (VISUAL_DESIGN S07). */
export function S07Evidence({ def }: { def: SceneDef }) {
  const cs = useCore();
  const [bt] = useArtifact(BACKTEST), [cl] = useArtifact(CLV), [el] = useArtifact(ELAST), [rc] = useArtifact(RECON);
  const [n, setN] = useState(1);
  useSteps(def.id, [0.1, 0.24, 0.38, 0.52, 0.66, 0.8, 0.92], (s) => {
    setN(Math.max(1, s));
    if (cs.status === "ready") setPair({ spec: heroSpec(cs.data), alpha: 0.15, ...DEFAULT_PAIR_RESET });
  });
  const c = cs.status === "ready" ? cs.data : null;
  const B = bt.status === "ready" ? bt.data : null, C = cl.status === "ready" ? cl.data : null, E = el.status === "ready" ? el.data : null, R = rc.status === "ready" ? rc.data : null;
  const ex = c ? [
    { q: "WHO ARE THESE CUSTOMERS?", a: <>WE DON&apos;T KNOW AND WE DON&apos;T GUESS. {c.meta.no_demographics.toUpperCase()}</>, tag: <HonestyChip tag="OBSERVED" /> },
    { q: "WHAT ABOUT RETURNS?", a: <>REFUNDS STAY VISIBLE, MATCHED TO EARLIER SALES WHERE ONE EXISTS{R ? `: ${fmt(R.refunds.refunded_qty - R.refunds.matched_qty)} UNITS HAVE NO SALE ON RECORD` : ""}.</>, tag: <HonestyChip tag="OBSERVED" /> },
    { q: "IS LIFT JUST POPULARITY?", a: <>NO. LIFT DIVIDES BY WHAT EACH ITEM&apos;S OWN POPULARITY WOULD PREDICT.</>, tag: <HonestyChip tag="DERIVED" /> },
    { q: "DOES THE FORECAST BEAT A NAIVE ONE?", a: <>{(B?.verdict ?? "").toUpperCase()}</>, tag: <HonestyChip tag="PREDICTED" /> },
    { q: "CAN YOU TRUST THE CLV?", a: <>IT WAS TESTED ON {C ? C.calibration.holdout_weeks.toFixed(0) : ""} WEEKS IT NEVER SAW. GAMMA-GAMMA INDEPENDENCE CHECK: CORRELATION {C ? C.gamma_gamma_check.corr_frequency_monetary.toFixed(2) : ""}.</>, tag: <HonestyChip tag="PREDICTED" /> },
    { q: "WHAT HAPPENS IF YOU RAISE THE PRICE?", a: <>{E && !E.decision.estimable ? "WE CAN'T SAY FROM THIS LEDGER. " : ""}{(E?.decision.text ?? "").toUpperCase()}</>, tag: <HonestyChip tag="DERIVED" detail="NOT ESTIMABLE" /> },
    { q: "WHERE DOES THIS DATA COME FROM?", a: <>{c.meta.source.attribution.toUpperCase()} DOI {c.meta.source.doi}. CC BY 4.0. DERIVED AGGREGATES, NOT THE ORIGINAL FILE.</>, tag: <HonestyChip tag="OBSERVED" /> },
  ] : [];
  const shown = ex.slice(Math.max(0, n - 4), n);
  return (
    <Track id={def.id} height={def.track} landing={def.landing} className="scene scene-evidence">
      <p className="scene-kicker s07-kicker">EVIDENCE · 7 OBJECTIONS</p>
      <h2 id={`${def.id}-title`} tabIndex={-1} data-scene-heading className="serif s07-title">How we know.</h2>
      <div className="argstack" aria-live="polite">
        {shown.map((e, i) => {
          const older = shown.length - 1 - i;
          return (
            <div key={e.q} className={`ex ${older > 0 ? "ex--old" : ""}`} style={{ ["--back" as string]: older }}>
              <p className="ex__q mono-label">{e.q}</p>
              {older === 0 ? <div className="ex__a"><p>{e.a}</p><div>{e.tag}</div></div> : null}
            </div>
          );
        })}
      </div>
    </Track>
  );
}

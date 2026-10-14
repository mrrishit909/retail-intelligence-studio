import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { useProgress, useMotion } from "../scroll/hooks";
import { windowed } from "../motion/progress";
import { HonestyChip } from "../components/HonestyChip";
import { ErrorLine, LoadingLine } from "../components/StateUI";
import { WordReveal } from "../components/WordReveal";
import { fmt, fv, fs, retryCore, useCore } from "./data";
import { classOf } from "./geometry";
import { drawn } from "./PairLayer";
import { getProgress } from "../scroll/engine";
import { useFrame } from "../scroll/hooks";

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
const monthLabel = (ts: string) => `${MONTHS[Number(ts.slice(5, 7)) - 1]} ${ts.slice(0, 4)}`;

/** S00 corner labels, readout, set labels and chip; S01 statement and cards. Portaled into the static track. */
export function OpeningLayer() {
  const cs = useCore();
  const motion = useMotion();
  const head = useRef<HTMLElement | null>(null);
  const readout = useRef<HTMLParagraphElement>(null);
  const cards = useRef<HTMLDivElement>(null);
  const statement = useRef<HTMLDivElement>(null);
  const labelA = useRef<HTMLDivElement>(null);
  const labelB = useRef<HTMLDivElement>(null);
  const chip = useRef<HTMLDivElement>(null);
  useEffect(() => { head.current = document.querySelector<HTMLElement>("h1[data-hero]"); }, []);
  useProgress("pattern", (p) => {
    const m = motion ? 1 : 0;
    const a = windowed(p, 0, 0.4);
    if (head.current) {
      const cls = classOf(document.documentElement.clientWidth);
      head.current.style.transform = `translate(0, ${-a * (cls === "D" ? 26 : 10) * m}px) scale(${1 - (cls === "D" ? 0.44 : 0.3) * a * m})`;
    }
    const fade = 1 - windowed(p, 0.05, 0.35) * m;
    if (readout.current) readout.current.style.opacity = String(fade);
    if (chip.current) chip.current.style.opacity = String(1 - windowed(p, 0.2, 0.45) * m);
    if (statement.current) statement.current.style.opacity = String(motion ? windowed(p, 0.3, 0.4) : 1);
    if (cards.current) {
      const c = windowed(p, 0.6, 1);
      cards.current.style.opacity = String(motion ? c : 1);
      cards.current.style.transform = `translateY(${motion ? (1 - c) * 24 : 0}px)`;
      cards.current.style.pointerEvents = c > 0.2 || !motion ? "auto" : "none";
    }
  });
  // set labels follow the settled geometry, outside the light at the viewport's lower corners
  useFrame(() => {
    const A = labelA.current, B = labelB.current;
    if (!A || !B || !drawn.spec) return;
    const dim = 1 - windowed(getProgress("pattern"), 0.05, 0.35);
    A.style.opacity = B.style.opacity = String(motion ? dim : 1);
  }, 120);
  const portal = document.getElementById("pattern-portal");
  if (!portal) return null;
  const c = cs.status === "ready" ? cs.data : null;
  const hero = c ? { na: fv(c, "hero_pair_na"), nb: fv(c, "hero_pair_nb"), nab: fv(c, "hero_pair_nab"), chance: fv(c, "hero_pair_chance"), lift: fv(c, "hero_pair_lift"), a: fs(c, "hero_pair_a_desc"), b: fs(c, "hero_pair_b_desc") } : null;
  const windowLabel = c ? `${monthLabel(c.meta.window.first_ts)} TO ${monthLabel(c.meta.window.last_ts)}` : "";
  return createPortal(
    <>
      <div className="intro-corner" data-intro-corner>
        {c ? (
          <>
            <p className="intro-corner__a">{fmt(fv(c, "basket_count"))} BASKETS · {windowLabel} · UK GIFT-WARE WHOLESALER</p>
            <p className="intro-corner__b">AREA = BASKETS · OVERLAP = BOUGHT TOGETHER</p>
          </>
        ) : null}
      </div>
      {cs.status === "loading" ? <div className="s00-state"><LoadingLine file={cs.file} loaded={0} total={null} /></div> : null}
      {cs.status === "error" ? <div className="s00-state"><ErrorLine file={cs.file} reason={cs.reason} attempt={1} onRetry={retryCore} /></div> : null}
      {hero && c ? (
        <>
          <p className="s00-readout mono-label" ref={readout} aria-live="polite" data-readout>
            BOTH: {fmt(hero.nab)} BASKETS · CHANCE WOULD GIVE {fmt(hero.chance)} · LIFT {hero.lift.toFixed(1)}
          </p>
          <div className="set-label set-label--a" ref={labelA}><span>{hero.a.toUpperCase()}</span><span className="dim">{fmt(hero.na)} BASKETS</span></div>
          <div className="set-label set-label--b" ref={labelB}><span>{hero.b.toUpperCase()}</span><span className="dim">{fmt(hero.nb)} BASKETS</span></div>
          <div className="s00-chip" ref={chip}>
            <HonestyChip tag="DERIVED" detail="1 ITEM PAIR · UCI ONLINE RETAIL II · CC BY 4.0" />
            <a className="doi" href={`https://doi.org/${c.meta.source.doi}`} rel="noreferrer">DOI {c.meta.source.doi}</a>
          </div>
        </>
      ) : null}
      <div className="s01-statement" ref={statement}>
        <WordReveal text="A pattern is an overlap that chance can't explain." as="h2" className="serif s01-title" mode={{ kind: "scrub", track: "pattern", from: 0.35, to: 0.75 }} />
      </div>
      {c ? (
        <div className="s01-cards" ref={cards}>
          <div className="note note--dark">
            <div className="note__top"><p className="note__head mono-label">FROM: THE LEDGER / {windowLabel}</p><HonestyChip tag="OBSERVED" className="note__tag" /></div>
            <p className="note__body">{fmt(fv(c, "invoices"))} INVOICES, {fmt(fv(c, "customers_known"))} KNOWN CUSTOMERS, {fmt(fv(c, "countries"))} COUNTRIES. £{fmt(fv(c, "revenue_sales_gbp"))} SOLD, £{fmt(Math.abs(fv(c, "revenue_refunds_gbp")))} REFUNDED.</p>
          </div>
          <div className="note note--rose">
            <div className="note__top"><p className="note__head mono-label">FROM: THE STUDIO / DERIVED</p><HonestyChip tag="DERIVED" className="note__tag" /></div>
            <p className="note__body">{fmt(fv(c, "basket_rules_total"))} RULES PASS SUPPORT {fv(c, "basket_min_support")} AND CONFIDENCE {fv(c, "basket_min_confidence")}. EACH ONE IS TWO SETS AND WHAT THEY SHARE.</p>
          </div>
        </div>
      ) : null}
    </>,
    portal,
  );
}

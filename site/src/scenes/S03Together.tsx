import { useMemo, useState } from "react";
import { Track } from "../scroll/Track";
import { HonestyChip } from "../components/HonestyChip";
import { Radio } from "../components/Radio";
import { WordReveal } from "../components/WordReveal";
import { ArtifactStatus } from "../components/StateUI";
import { useArtifact } from "../data/useArtifact";
import { BASKETS, type Baskets, type Rule } from "../app/artifacts";
import { fmt } from "../app/data";
import { setPair, type PairSpec } from "../app/pairView";
import { Column, Lower, Readout, SetNames, SourceFoot, useSteps, usePairView } from "./common";
import type { SceneDef } from "../app/scenes";
import { classOf } from "../app/geometry";

/** the two sets of a rule, from its own numbers: anchor = antecedent baskets, partner = baskets holding the whole consequent */
export function ruleSpec(r: Rule, b: Baskets, id = "rule"): PairSpec {
  const N = b.params.baskets;
  const na = Math.round((r.count / r.confidence));
  const nb = Math.round((r.confidence / r.lift) * N);
  return {
    id: `${id}:${r.antecedent.join("+")}>${r.consequent.join("+")}`, unit: "BASKETS", sizeA: na, sizeB: nb, shared: r.count,
    labelA: r.antecedent_desc.join(" + "), labelB: r.consequent_desc.join(" + "), chance: (na * nb) / N,
    role: "observed", interval: null, hatch: false, refSize: Math.max(na, nb), axis: "h",
  };
}
export function showcaseRules(b: Baskets, order: "lift" | "count", across: boolean): Rule[] {
  const seen = new Set<string>();
  const hero = [b.hero.a, b.hero.b].sort().join("+");
  const ok = b.rules.filter((r) => {
    if (r.variant_of_same_product || (across && r.same_family)) return false;
    const key = [...r.antecedent, ...r.consequent].sort().join("+");
    if (key === hero || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  return [...ok].sort((x, y) => (order === "lift" ? y.lift - x.lift : y.count - x.count)).slice(0, 6);
}

/** S03a Mechanism I: bought together, 6 stepped rules, each pulled from chance. */
export function S03Together({ def }: { def: SceneDef }) {
  const [art, retry] = useArtifact(BASKETS);
  const [order, setOrder] = useState<"lift" | "count">("lift");
  const [across, setAcross] = useState(false);
  const [idx, setIdx] = useState(0);
  const b = art.status === "ready" ? art.data : null;
  const rules = useMemo(() => (b ? showcaseRules(b, order, across) : []), [b, order, across]);
  const rule = rules[Math.min(idx, rules.length - 1)];
  const spec = b && rule ? ruleSpec(rule, b) : null;
  const apply = (i: number) => { if (b && rules[i]) setPair({ spec: ruleSpec(rules[i]!, b), alpha: 1, inspected: null }); };
  useSteps(def.id, [0.08, 0.24, 0.4, 0.56, 0.72, 0.88], (s) => { const i = Math.max(0, s - 1); setIdx(i); apply(Math.min(i, rules.length - 1)); });
  const v = usePairView();
  void v;
  const go = (d: number) => { const n = Math.min(rules.length - 1, Math.max(0, idx + d)); setIdx(n); apply(n); };
  const mobile = typeof document !== "undefined" && classOf(document.documentElement.clientWidth) === "M";
  return (
    <Track id={def.id} height={def.track} landing={def.landing} className="scene scene-together">
      <Column>
        <p className="scene-kicker">SUPPORT · CONFIDENCE · LIFT · ONE RULE AT A TIME</p>
        <WordReveal text="Bought together, more than chance allows." as="h2" className="serif scene-title" mode={{ kind: "scrub", track: def.id, from: 0.0, to: 0.08 }} id={`${def.id}-title`} tabIndex={-1} data-scene-heading />
        <div className="ctl-row">
          <Radio<"lift" | "count"> label="ORDER" value={order} options={["lift", "count"] as const} render={(x) => (x === "lift" ? "BY LIFT" : "BY BASKETS")} onChange={(x) => { setOrder(x); setIdx(0); }} asSelect={mobile} />
          <Radio<"all" | "across"> label="FAMILIES" value={across ? "across" : "all"} options={["all", "across"] as const} render={(x) => (x === "all" ? "ALL" : "ACROSS FAMILIES")} onChange={(x) => { setAcross(x === "across"); setIdx(0); }} asSelect={mobile} />
          <button type="button" className="btn-square" onClick={() => go(-1)} aria-label="Previous rule">◀</button>
          <button type="button" className="btn-square" onClick={() => go(1)} aria-label="Next rule">▶</button>
        </div>
        <Lower>
          <ArtifactStatus file="baskets.json" state={art} retry={retry} empty="NO RULE ABOVE THESE THRESHOLDS">{(bk) => rule && spec ? (
            <>
              <SetNames spec={spec} />
              <p className="ledger-line mono-label">
                IN {fmt(rule.count)} OF {fmt(bk.params.baskets)} BASKETS (SUPPORT {rule.support.toFixed(3)}) · {(rule.confidence * 100).toFixed(0)}% OF {fmt(spec.sizeA)} BASKETS ALSO HOLD IT (CONFIDENCE) · {rule.lift.toFixed(1)}X CHANCE (LIFT)
              </p>
              <Readout spec={spec} population={bk.params.baskets} />
              <ul className="step-list" aria-label="Rule index">
                {rules.map((r, i) => <li key={i} className={i === idx ? "on" : ""}>{r.lift.toFixed(1)}X · {fmt(r.count)}</li>)}
              </ul>
              <p className="note-line mono-label">MIN SUPPORT {bk.params.min_support} · MIN CONFIDENCE {bk.params.min_confidence} · MIN LIFT {bk.params.min_lift} · {fmt(bk.rules_total)} RULES</p>
              <p className="caveat mono-label">{bk.caveat.toUpperCase()}</p>
              <HonestyChip tag="DERIVED" detail="COUNTS OBSERVED" />
            </>
          ) : <p className="state-line">NO RULE ABOVE THESE THRESHOLDS</p>}</ArtifactStatus>
          <SourceFoot />
        </Lower>
      </Column>
    </Track>
  );
}

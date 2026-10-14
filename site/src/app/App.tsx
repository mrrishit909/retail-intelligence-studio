import { useEffect, useLayoutEffect } from "react";
import { Nav } from "../components/Nav";
import { Track } from "../scroll/Track";
import { jumpTo, registerTrack, resolveInitialHash } from "../scroll/engine";
import { useActiveScene } from "../scroll/hooks";
import { NAV_ITEMS, SCENES, navActive, type SceneDef } from "./scenes";
import { useIntro } from "./useIntro";
import { loadCore, useCore } from "./data";
import { PairLayer } from "./PairLayer";
import { OpeningLayer } from "./OpeningLayer";
import { heroSpec } from "./specs";
import { setPair } from "./pairView";
import { S02Ledger } from "../scenes/S02Ledger";
import { S03Together } from "../scenes/S03Together";
import { S03bBack } from "../scenes/S03bBack";
import { S04Matters } from "../scenes/S04Matters";
import { S05Stock } from "../scenes/S05Stock";
import { S06Sells } from "../scenes/S06Sells";
import { S07Evidence } from "../scenes/S07Evidence";
import { Counter } from "../scenes/Counter";
import { S08Closing } from "../scenes/S08Closing";

const SCENE_COMPONENTS: Record<string, (p: { def: SceneDef }) => React.ReactNode> = {
  ledger: S02Ledger, together: S03Together, back: S03bBack, matters: S04Matters, stock: S05Stock, sells: S06Sells, evidence: S07Evidence, counter: Counter,
};

function Placeholder({ s }: { s: SceneDef }) {
  return (
    <Track id={s.id} height={s.track} landing={s.landing} className={`scene scene-${s.id} scene--placeholder`}>
      <div className="placeholder">
        <p className="scene-kicker">{s.code} · {s.nav ?? "CLOSING"}</p>
        <h2 id={`${s.id}-title`} tabIndex={-1} data-scene-heading className="placeholder__title">{s.title}</h2>
      </div>
    </Track>
  );
}

/** App: the static pattern track (index.html), the pair canvas layer, the React scenes and the nav. */
export function App() {
  const active = useActiveScene();
  const intro = useIntro();
  const cs = useCore();
  useLayoutEffect(() => {
    const el = document.getElementById("pattern");
    return el ? registerTrack("pattern", el, SCENES[0]!.landing) : undefined;
  }, []);
  useEffect(() => { void loadCore(); }, []);
  useEffect(() => { resolveInitialHash(); }, []);
  useEffect(() => { if (cs.status === "ready") setPair({ spec: heroSpec(cs.data) }); }, [cs]);
  return (
    <>
      <PairLayer />
      <OpeningLayer />
      <Nav
        items={NAV_ITEMS}
        active={navActive(active)}
        onJump={(id) => jumpTo(id, undefined, { push: true, focus: true })}
        introPlaying={!intro.navIn}
        onSkip={intro.skip}
        onReplay={intro.replay}
      />
      {SCENES.slice(1).map((s) => {
        if (s.id === "closing") return <S08Closing key={s.id} def={s} onReplay={intro.replay} />;
        const C = SCENE_COMPONENTS[s.id];
        return C ? <C key={s.id} def={s} /> : <Placeholder key={s.id} s={s} />;
      })}
    </>
  );
}

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
      {SCENES.slice(1).map((s) => <Placeholder key={s.id} s={s} />)}
    </>
  );
}

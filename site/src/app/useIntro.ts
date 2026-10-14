import { useCallback, useEffect, useState } from "react";
import { addFrame } from "../motion/loop";
import { Reveal } from "../motion/reveal";
import { motionEnabled } from "../state/motion";
import { INTRO_MS, intro, introTime } from "./intro";

const KEY = "hs.intro";
const seen = () => { try { return sessionStorage.getItem(KEY) === "done"; } catch { return false; } };
const markSeen = () => { try { sessionStorage.setItem(KEY, "done"); } catch { /* storage blocked: plays again next load */ } };

/** Drives the DOM from the S00 clock: corner labels 200-500 ms, headline sharpening from 3600 ms, nav at 4200 ms. */
export function useIntro() {
  const [playing, setPlaying] = useState(() => motionEnabled() && !seen());
  const [navIn, setNavIn] = useState(() => !playing);
  const [run, setRun] = useState(0);

  const complete = useCallback(() => {
    if (!intro.playing || intro.completeFrom >= 0 || intro.frozen >= 0) return;
    const now = performance.now();
    intro.completeFrom = introTime(now);
    intro.completeAt = now;
    setNavIn(true);
  }, []);

  useEffect(() => {
    const h = document.querySelector<HTMLElement>("h1[data-hero]");
    const reveal = h ? new Reveal(h) : null;
    const corners = document.querySelectorAll<HTMLElement>("[data-intro-corner]");
    if (!playing) {
      intro.playing = false;
      reveal?.set(1);
      corners.forEach((c) => (c.style.opacity = ""));
      return;
    }
    Object.assign(intro, { playing: true, start: 0, completeFrom: -1, completeAt: 0 });
    reveal?.set(0);
    let navShown = false;
    const off = addFrame((now) => {
      const t = introTime(now);
      const c = String(Math.max(0, Math.min(1, (t - 200) / 300)));
      corners.forEach((el) => (el.style.opacity = c));
      reveal?.timed(t - 3600, 350, 80);
      if (!navShown && t >= 4200) { navShown = true; setNavIn(true); }
      if (t >= INTRO_MS && intro.frozen < 0) {
        off();
        intro.playing = false;
        reveal?.set(1);
        markSeen();
        setPlaying(false);
      }
    }, 20);
    const onKey = (e: KeyboardEvent) => {
      if (["Escape", "ArrowDown", "ArrowUp", "PageDown", "PageUp", " ", "End", "Home"].includes(e.key)) complete();
    };
    addEventListener("wheel", complete, { passive: true });
    addEventListener("sco:jump", complete);
    addEventListener("touchmove", complete, { passive: true });
    addEventListener("keydown", onKey);
    return () => {
      off();
      removeEventListener("wheel", complete);
      removeEventListener("sco:jump", complete);
      removeEventListener("touchmove", complete);
      removeEventListener("keydown", onKey);
    };
  }, [playing, run, complete]);

  const replay = useCallback(() => {
    scrollTo(0, 0);
    if (!motionEnabled()) return;
    setNavIn(false);
    setPlaying(true);
    setRun((r) => r + 1);
  }, []);

  return { playing, navIn, skip: complete, replay };
}

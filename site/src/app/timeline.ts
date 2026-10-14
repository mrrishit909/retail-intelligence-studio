/** S00 "The Pull" as a pure function of time (ms): disc lighting, the chance position, then the pull to the real overlap. */
const clamp = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);
const ease = (t: number) => t * t * (3 - 2 * t);
export interface PullPhase { light: number; /** 0 = at the chance position, 1 = at the real overlap */ pull: number; overlap: number; readout: "none" | "chance" | "real" }
export function pullAt(t: number): PullPhase {
  const light = ease(clamp((t - 300) / 1100));
  const pull = ease(clamp((t - 2000) / 1600));
  return { light, pull, overlap: clamp((t - 1600) / 600), readout: t < 1700 ? "none" : t < 3600 ? "chance" : "real" };
}
export const REAL: PullPhase = { light: 1, pull: 1, overlap: 1, readout: "real" };
/** S08 echo: push back to chance over 800 ms, hold, pull again over 1600 ms */
export const ECHO_PUSH = 800, ECHO_HOLD = 300, ECHO_PULL = 1600, ECHO_TOTAL = ECHO_PUSH + ECHO_HOLD + ECHO_PULL;
export function echoAt(te: number): { pull: number; active: boolean } {
  if (te < 0) return { pull: 1, active: false };
  if (te < ECHO_PUSH) return { pull: 1 - ease(te / ECHO_PUSH), active: true };
  if (te < ECHO_PUSH + ECHO_HOLD) return { pull: 0, active: true };
  if (te < ECHO_TOTAL) return { pull: ease((te - ECHO_PUSH - ECHO_HOLD) / ECHO_PULL), active: true };
  return { pull: 1, active: false };
}

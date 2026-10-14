/** S00 clock (MOTION_SYSTEM 5.1): 4.6 s, SKIP/Esc/scroll complete it in 350 ms; scroll is never locked. */
export const INTRO_MS = 4600;
export const intro = { playing: false, start: 0, completeFrom: -1, completeAt: 0, frozen: -1 };
export function introTime(now: number): number {
  if (intro.frozen >= 0) return intro.frozen;
  if (!intro.start) intro.start = now;
  if (intro.completeFrom >= 0) {
    const k = Math.min(1, (now - intro.completeAt) / 350);
    return intro.completeFrom + (INTRO_MS - intro.completeFrom) * k;
  }
  return now - intro.start;
}

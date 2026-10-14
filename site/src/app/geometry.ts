/** Camera states for the pair (VISUAL_DESIGN 3.3). R = reference radius of the scene's largest anchor, chord = centre of the common chord. */
export type Cls = "D" | "T" | "M";
export interface Cam { chord: [number, number]; R: number; axis: [number, number] }
const REF = { D: [1440, 900], T: [768, 1024], M: [390, 844] } as const;
const H: [number, number] = [1, 0], DG: [number, number] = [0.6, 0.8], CO: [number, number] = [0.55, 0.835];
const G = {
  D: { G0: { chord: [1000, 450], R: 558, axis: H }, G1: { chord: [1100, 470], R: 300, axis: H }, G2: { chord: [1000, 470], R: 330, axis: H }, G5: { chord: [980, 500], R: 300, axis: H } },
  T: { G0: { chord: [430, 620], R: 560, axis: DG }, G1: { chord: [384, 760], R: 260, axis: DG }, G2: { chord: [384, 340], R: 150, axis: DG }, G5: { chord: [384, 380], R: 240, axis: DG } },
  M: { G0: { chord: [205, 480], R: 300, axis: DG }, G1: { chord: [195, 640], R: 170, axis: DG }, G2: { chord: [195, 300], R: 100, axis: DG }, G5: { chord: [195, 300], R: 150, axis: DG } },
} as const;
export const classOf = (w: number): Cls => (w < 768 ? "M" : w < 1024 ? "T" : "D");
export function camera(name: "G0" | "G1" | "G2" | "G5", w: number, h: number, axisKind: "h" | "diag" | "cohort" = "h"): Cam {
  const cls = classOf(w), [rw, rh] = REF[cls];
  const sx = w / rw, sy = h / rh, sr = Math.min(sx, sy);
  const g = G[cls][name];
  let axis: [number, number] = [g.axis[0], g.axis[1]];
  if (cls === "D" && axisKind !== "h" && name !== "G0") axis = [CO[0], CO[1]];
  return { chord: [g.chord[0] * sx, g.chord[1] * sy], R: g.R * sr, axis };
}
export function mixCam(a: Cam, b: Cam, t: number): Cam {
  const u = Math.min(1, Math.max(0, t));
  return {
    chord: [a.chord[0] + (b.chord[0] - a.chord[0]) * u, a.chord[1] + (b.chord[1] - a.chord[1]) * u],
    R: Math.exp(Math.log(a.R) + (Math.log(b.R) - Math.log(a.R)) * u),
    axis: [a.axis[0] + (b.axis[0] - a.axis[0]) * u, a.axis[1] + (b.axis[1] - a.axis[1]) * u],
  };
}

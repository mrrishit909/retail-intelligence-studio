/** Common Ground renderer: two discs of light whose areas are set sizes, the overlap in white light, a ghost at the chance position. */
import { pairFor, type Pair } from "../model/euler";

export type Role = "observed" | "predicted";
export interface Geometry {
  ax: number; ay: number; bx: number; by: number; ra: number; rb: number; d: number;
  ux: number; uy: number; kind: Pair["kind"];
}
export interface PairDraw {
  pair: Pair;
  /** chord point (the centre of the overlap's common chord) and the axis unit vector, px */
  cx: number; cy: number; ux: number; uy: number;
  role: Role;
  /** the chance pair, drawn as a 6% ghost, or null */ ghost: Pair | null;
  /** partner soft edge: blur radius in px (PREDICTED only) */ soft: number;
  /** hatch the partner instead of lighting it (a size that is not estimable) */ hatch: boolean;
  alpha: number;
  /** 0..1 light-on progress of the discs (S00: from the far rim inward) */ lightOn: number;
  /** overlap visibility 0..1 */ overlap: number;
}

export function geometryOf(p: Pair, cx: number, cy: number, ux: number, uy: number): Geometry {
  let a: number;
  if (p.kind === "identical") a = 0;
  else if (p.kind === "disjoint") a = p.ra + (p.d - p.ra - p.rb) / 2;
  else a = p.d > 0 ? (p.d * p.d + p.ra * p.ra - p.rb * p.rb) / (2 * p.d) : 0;
  const ax = cx - a * ux, ay = cy - a * uy;
  return { ax, ay, bx: ax + p.d * ux, by: ay + p.d * uy, ra: p.ra, rb: p.rb, d: p.d, ux, uy, kind: p.kind };
}

// role ramps, far rim to near rim
const ANCHOR = ["#4A0A24", "#A0105A", "#FF2F7A", "#FFB3CC"];
const PARTNER_OBS = ["#4A1206", "#B8321A", "#FF4C25", "#FFD2B0"];
const PARTNER_PRED = ["#141A4A", "#3C4FD0", "#8FA2FF", "#DCE2FF"];
const LEVEL = [0.18, 0.3, 0.62, 0.72];

function discFill(ctx: CanvasRenderingContext2D, x: number, y: number, r: number, ux: number, uy: number, ramp: string[], towardPartner: number) {
  // lit from the side that faces the partner: far rim (dim) to near rim (bright)
  const sgn = towardPartner;
  const g = ctx.createLinearGradient(x - sgn * ux * r, y - sgn * uy * r, x + sgn * ux * r, y + sgn * uy * r);
  const off = [0, 0.45, 0.85, 1];
  ramp.forEach((c, i) => g.addColorStop(off[i]!, withAlpha(c, 0.35 + 0.65 * LEVEL[i]! / 0.72)));
  ctx.fillStyle = g;
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
}
function withAlpha(hex: string, a: number) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${Math.min(1, a)})`;
}

let hatchPat: CanvasPattern | null = null;
function hatch(ctx: CanvasRenderingContext2D) {
  if (hatchPat) return hatchPat;
  const c = document.createElement("canvas"); c.width = c.height = 6;
  const g = c.getContext("2d")!; g.strokeStyle = "rgba(255,255,255,0.12)"; g.lineWidth = 1.4;
  g.beginPath(); g.moveTo(0, 6); g.lineTo(6, 0); g.stroke();
  hatchPat = ctx.createPattern(c, "repeat")!;
  return hatchPat;
}

export function drawPair(ctx: CanvasRenderingContext2D, w: number, h: number, dpr: number, p: PairDraw) {
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  ctx.globalAlpha = p.alpha;
  const g = geometryOf(p.pair, p.cx, p.cy, p.ux, p.uy);
  const partnerRamp = p.role === "predicted" ? PARTNER_PRED : PARTNER_OBS;
  // chance ghost: the partner where independence would put it
  if (p.ghost && p.ghost.kind !== "identical") {
    const gg = geometryOf({ ...p.ghost, ra: p.pair.ra, rb: p.pair.rb }, p.cx, p.cy, p.ux, p.uy);
    // anchor position is fixed: re-anchor the ghost on the real anchor centre
    const gx = g.ax + p.ghost.d * p.ux, gy = g.ay + p.ghost.d * p.uy;
    void gg;
    ctx.fillStyle = "rgba(255,255,255,0.06)";
    ctx.beginPath(); ctx.arc(gx, gy, p.pair.rb, 0, Math.PI * 2); ctx.fill();
  }
  const lo = Math.min(1, Math.max(0, p.lightOn));
  const reveal = (x: number, y: number, r: number, draw: () => void) => {
    // the disc lights from its far rim inward: a growing disc clip is the cheapest honest version
    if (lo >= 1) { draw(); return; }
    ctx.save();
    ctx.beginPath(); ctx.arc(x, y, r * Math.max(0.001, lo), 0, Math.PI * 2); ctx.clip();
    draw();
    ctx.restore();
  };
  if (p.pair.kind === "identical") {
    reveal(g.ax, g.ay, g.ra, () => { ctx.fillStyle = "#FFFFFF"; ctx.beginPath(); ctx.arc(g.ax, g.ay, g.ra, 0, Math.PI * 2); ctx.fill(); });
    ctx.globalAlpha = 1;
    return;
  }
  // anchor, then the partner (soft edge for a PREDICTED partner), both lit from the side that faces the other
  reveal(g.ax, g.ay, g.ra, () => discFill(ctx, g.ax, g.ay, g.ra, p.ux, p.uy, ANCHOR, 1));
  reveal(g.bx, g.by, g.rb, () => {
    if (p.hatch) {
      ctx.fillStyle = hatch(ctx);
      ctx.beginPath(); ctx.arc(g.bx, g.by, g.rb, 0, Math.PI * 2); ctx.fill();
      return;
    }
    if (p.soft > 0.5) { ctx.save(); ctx.filter = `blur(${p.soft}px)`; }
    discFill(ctx, g.bx, g.by, g.rb, p.ux, p.uy, partnerRamp, -1);
    if (p.soft > 0.5) ctx.restore();
  });
  // the overlap: white light, luminance from a distance-to-boundary field (min of the two radial distances, 'darken')
  if (p.pair.kind !== "disjoint" && p.overlap > 0 && !p.hatch) {
    const lensHalf = Math.max(2, Math.min(g.ra, g.rb, (g.ra + g.rb - g.d) / 2));
    const stops = (x: number, y: number, r: number) => {
      const gr = ctx.createRadialGradient(x, y, Math.max(0, r - lensHalf), x, y, r);
      gr.addColorStop(0, "#FFFFFF"); gr.addColorStop(0.5, "#FFE9E2"); gr.addColorStop(1, "#FF9A8A");
      return gr;
    };
    // static bloom of the overlap only, spilling just past its arcs
    ctx.save();
    ctx.globalAlpha = p.alpha * 0.35 * p.overlap;
    ctx.filter = "blur(18px)";
    ctx.globalCompositeOperation = "screen";
    ctx.beginPath(); ctx.arc(g.ax, g.ay, g.ra, 0, Math.PI * 2); ctx.clip();
    ctx.fillStyle = "#FFE9E2";
    ctx.beginPath(); ctx.arc(g.bx, g.by, g.rb, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
    ctx.save();
    ctx.globalAlpha = p.alpha * p.overlap;
    ctx.beginPath(); ctx.arc(g.ax, g.ay, g.ra, 0, Math.PI * 2); ctx.clip();
    ctx.beginPath(); ctx.arc(g.bx, g.by, g.rb, 0, Math.PI * 2); ctx.clip();
    ctx.fillStyle = stops(g.ax, g.ay, g.ra);
    ctx.fillRect(0, 0, w, h);
    ctx.globalCompositeOperation = "darken";
    ctx.fillStyle = stops(g.bx, g.by, g.rb);
    ctx.fillRect(0, 0, w, h);
    ctx.restore();
  }
  ctx.globalAlpha = 1;
}

export { pairFor };

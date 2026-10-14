/** Area-proportional Euler pair (Common Ground): two discs whose areas are set sizes and whose overlap area is exactly `shared`. */
export interface Pair {
  /** radii in px, anchor and partner */ ra: number; rb: number;
  /** centre distance in px */ d: number;
  /** relation of the two sets */ kind: "disjoint" | "overlap" | "contained" | "identical";
}

/** Area of the intersection of two discs of radii r1, r2 whose centres are d apart. */
export function lensArea(r1: number, r2: number, d: number): number {
  if (d >= r1 + r2) return 0;
  const lo = Math.min(r1, r2);
  if (d <= Math.abs(r1 - r2)) return Math.PI * lo * lo;
  const a = r1 * r1 * Math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1));
  const b = r2 * r2 * Math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2));
  const c = 0.5 * Math.sqrt((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2));
  return a + b - c;
}

/** Centre distance whose lens area equals `target` (the area is monotone decreasing in d: bisection to 1e-12 relative). */
export function solveDistance(r1: number, r2: number, target: number): number {
  const lo0 = Math.abs(r1 - r2), hi0 = r1 + r2;
  const full = Math.PI * Math.min(r1, r2) ** 2;
  if (target >= full * (1 - 1e-12)) return lo0;
  if (target <= 0) return hi0;
  let lo = lo0, hi = hi0;
  for (let i = 0; i < 200; i++) {
    const mid = (lo + hi) / 2;
    if (lensArea(r1, r2, mid) > target) lo = mid; else hi = mid;
    if (hi - lo < 1e-13 * hi) break;
  }
  return (lo + hi) / 2;
}

/** radius from a size and the scene's px^2-per-unit constant k */
export const radiusOf = (size: number, k: number) => Math.sqrt((Math.max(0, size) * k) / Math.PI);

/** The exact pair for sizes (a, b) sharing `shared` units at scale k. Disjoint sets sit apart with a gap of 0.06 r_partner. */
export function pairFor(sizeA: number, sizeB: number, shared: number, k: number): Pair {
  const ra = radiusOf(sizeA, k), rb = radiusOf(sizeB, k);
  const s = Math.min(Math.max(0, shared), Math.min(sizeA, sizeB));
  if (sizeA > 0 && sizeB > 0 && Math.abs(sizeA - sizeB) < 1e-9 * sizeA && s >= sizeA * (1 - 1e-12)) return { ra, rb, d: 0, kind: "identical" };
  if (s <= 0) return { ra, rb, d: ra + rb + 0.06 * rb, kind: "disjoint" };
  const target = s * k;
  const d = solveDistance(ra, rb, target);
  return { ra, rb, d, kind: s >= Math.min(sizeA, sizeB) * (1 - 1e-12) ? "contained" : "overlap" };
}

/** the chance overlap of two sets drawn from one population: size_a * size_b / population (lift = shared / chance) */
export const chanceShared = (na: number, nb: number, population: number) => (na * nb) / population;
export const liftOf = (nab: number, na: number, nb: number, population: number) => (nab * population) / (na * nb);

/** the area of the smaller set that lies outside the overlap, as a share (for "almost the same set") */
export const crescentShare = (sizeSmall: number, shared: number) => (sizeSmall > 0 ? (sizeSmall - shared) / sizeSmall : 0);

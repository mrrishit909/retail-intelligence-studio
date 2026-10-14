import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { lensArea, pairFor, solveDistance, radiusOf, liftOf, chanceShared } from "./euler";
import { normalPolicy, empiricalPolicy, normCdf, normInv, negativeMass } from "./newsvendor";

const D = join(process.cwd(), "public/data");
const J = <T,>(f: string) => JSON.parse(readFileSync(join(D, f), "utf8")) as T;

describe("area-proportional Euler pair", () => {
  it("lens area has the textbook limits", () => {
    expect(lensArea(3, 2, 6)).toBe(0);
    expect(lensArea(3, 2, 1)).toBeCloseTo(Math.PI * 4, 12);
    expect(lensArea(1, 1, 0)).toBeCloseTo(Math.PI, 12);
    // two unit circles at d = 1: 2 acos(1/2) - sqrt(3)/2 = 2.0944 - 0.8660
    expect(lensArea(1, 1, 1)).toBeCloseTo((2 * Math.PI) / 3 - Math.sqrt(3) / 2, 12);
  });
  it("the solved distance reproduces the target overlap to 1e-9 relative", () => {
    for (const [r1, r2, f] of [[558, 417, 0.4], [300, 20, 0.5], [100, 100, 0.01], [100, 100, 0.99], [330, 57, 0.7]] as const) {
      const target = Math.PI * Math.min(r1, r2) ** 2 * f;
      const d = solveDistance(r1, r2, target);
      expect(Math.abs(lensArea(r1, r2, d) - target) / target).toBeLessThan(1e-9);
    }
  });
  it("the design fixture: 4,013 / 2,245 / 1,428 baskets, k = pi 558^2 / 4013", () => {
    const k = (Math.PI * 558 ** 2) / 4013;
    expect(k).toBeCloseTo(243.75, 1);
    const p = pairFor(4013, 2245, 1428, k);
    expect(p.ra).toBeCloseTo(558, 6);
    expect(p.rb).toBeCloseTo(417.4, 0);
    expect(p.d).toBeCloseTo(411.2, 0);
    expect(Math.abs(lensArea(p.ra, p.rb, p.d) - 1428 * k) / (1428 * k)).toBeLessThan(1e-9);
  });
  it("disjoint, contained and identical sets are explicit states", () => {
    const k = 1;
    expect(pairFor(100, 50, 0, k).kind).toBe("disjoint");
    const c = pairFor(100, 50, 50, k);
    expect(c.kind).toBe("contained");
    expect(c.d).toBeCloseTo(radiusOf(100, k) - radiusOf(50, k), 9);
    expect(pairFor(80, 80, 80, k).kind).toBe("identical");
  });
  it("hero pair in facts: chance and lift follow na*nb/baskets", () => {
    const f = J<{ facts: Record<string, { value: number }> }>("facts.json").facts;
    const v = (k: string) => f[k]!.value;
    expect(chanceShared(v("hero_pair_na"), v("hero_pair_nb"), v("basket_count"))).toBeCloseTo(v("hero_pair_chance"), 8);
    expect(liftOf(v("hero_pair_nab"), v("hero_pair_na"), v("hero_pair_nb"), v("basket_count"))).toBeCloseTo(v("hero_pair_lift"), 8);
  });
});

describe("newsvendor parity (newsvendor_vectors.json)", () => {
  const v = J<{ tolerance_rel: number; vectors: { case: string; model: string; inputs: { cost: number; mu: number; price: number; salvage: number; sigma: number; samples: number[] | null; q?: number }; expected: Record<string, number> }[] }>("newsvendor_vectors.json");
  it("normal CDF and its inverse agree to 1e-9", () => {
    expect(normCdf(0)).toBeCloseTo(0.5, 15);
    expect(normCdf(1.959963984540054)).toBeCloseTo(0.975, 10);
    expect(normCdf(-5)).toBeCloseTo(2.866515718791939e-7, 14);
    for (const p of [1e-6, 0.01, 0.3, 0.5, 0.9, 0.999999]) expect(Math.abs(normCdf(normInv(p)) - p) / p).toBeLessThan(1e-9);
  });
  for (const vec of v.vectors) {
    it(`reproduces ${vec.case}`, () => {
      const { price, cost, salvage, mu, sigma, samples } = vec.inputs;
      const r = vec.model === "normal" ? normalPolicy(price, cost, salvage, mu, sigma, vec.inputs.q) : empiricalPolicy(price, cost, salvage, samples!, vec.inputs.q);
      for (const [k, e] of Object.entries(vec.expected)) {
        const g = (r as unknown as Record<string, number>)[k]!;
        const tol = Math.max(Math.abs(e) * v.tolerance_rel, 1e-9);
        expect(Math.abs(g - e), `${vec.case}.${k}`).toBeLessThanOrEqual(tol);
      }
    });
  }
  it("flags the item whose normal fit puts >5% below zero", () => {
    const p = J<{ items: { id: string; mean_weekly_units: number; sd_weekly_units: number }[] }>("newsvendor_params.json");
    const bad = p.items.filter((i) => negativeMass(i.mean_weekly_units, i.sd_weekly_units) > 0.05).map((i) => i.id);
    expect(bad.some((id) => id.includes("84077"))).toBe(true);
  });
});

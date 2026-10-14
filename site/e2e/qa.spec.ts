/* eslint-disable @typescript-eslint/no-explicit-any */
/** P09 release gate: areas drawn == numbers shown, parity with the artifacts, state machines, collisions, contrast, axe, reduced motion. */
import { expect, test, type Browser } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { WALK, collideAll, contrastFails, goScene, openSite } from "./qa";

test.skip(({ isMobile }) => isMobile, "viewports are set per test");
test.describe.configure({ timeout: 600_000 });
const BASE = "http://localhost:4391/retail-intelligence-studio/";
const VP = (w: number, h: number) => ({ width: w, height: h });
async function at(browser: Browser, vp: { width: number; height: number }, opts: { reduced?: boolean } = {}) {
  const ctx = await browser.newContext({ viewport: vp, isMobile: vp.width < 768, hasTouch: vp.width < 768, reducedMotion: opts.reduced ? "reduce" : "no-preference", baseURL: BASE });
  return { ctx, page: await ctx.newPage() };
}
const D = join(process.cwd(), "public/data");
const J = <T,>(f: string) => JSON.parse(readFileSync(join(D, f), "utf8")) as T;
const text = (page: any) => page.evaluate(() => document.body.innerText);
const fmt = (n: number) => Math.round(n).toLocaleString("en-US");

test("S00: the hero pair on screen is the exact Euler pair of the published counts", async ({ browser }) => {
  const { ctx, page } = await at(browser, VP(1440, 900));
  await openSite(page);
  await page.waitForFunction(() => (window as any).__rs.core() === "ready");
  await page.waitForTimeout(1500);
  const f = J<{ facts: Record<string, { value: number }> }>("facts.json").facts;
  const d = await page.evaluate(() => (window as any).__rs.drawn());
  expect(d.spec).toBe("hero");
  expect(Math.abs(d.sizeA - f.hero_pair_na!.value) / f.hero_pair_na!.value).toBeLessThan(1e-6);
  expect(Math.abs(d.sizeB - f.hero_pair_nb!.value) / f.hero_pair_nb!.value).toBeLessThan(1e-6);
  expect(Math.abs(d.overlapUnits - f.hero_pair_nab!.value) / f.hero_pair_nab!.value).toBeLessThan(1e-6);
  const t = await text(page);
  expect(t).toContain(`${fmt(f.basket_count!.value)} BASKETS`);
  expect(t).toContain(`BOTH: ${fmt(f.hero_pair_nab!.value)} BASKETS`);
  await ctx.close();
});

test("areas drawn equal the numbers shown in every scene state", async ({ browser }) => {
  const { ctx, page } = await at(browser, VP(1440, 900));
  await openSite(page);
  const bad: string[] = [];
  for (const [id, p] of WALK) {
    await goScene(page, id, p);
    await page.waitForTimeout(id === "closing" && p >= 0.7 ? 3400 : 900); // the echo pulls the pair for 2.7 s
    const r = await page.evaluate(() => ({ d: (window as any).__rs.drawn(), v: (window as any).__rs.view() }));
    if (!r.d || !r.v.spec) { bad.push(`${id}@${p}: nothing drawn`); continue; }
    const s = r.v.spec;
    if (s.hatch) continue;
    const rel = (a: number, b: number) => Math.abs(a - b) / Math.max(1, Math.abs(b));
    if (rel(r.d.sizeA, s.sizeA) > 1e-5 || rel(r.d.sizeB, s.sizeB) > 1e-5) bad.push(`${id}@${p}: sizes ${r.d.sizeA}/${r.d.sizeB} vs ${s.sizeA}/${s.sizeB}`);
    if (r.d.kind === "overlap" && rel(r.d.overlapUnits, s.shared) > 1e-5) bad.push(`${id}@${p}: overlap ${r.d.overlapUnits} vs ${s.shared}`);
  }
  expect(bad).toEqual([]);
  await ctx.close();
});

test("S03a: the first rule's counts, confidence and lift are the artifact's", async ({ browser }) => {
  const { ctx, page } = await at(browser, VP(1440, 900));
  await openSite(page);
  await goScene(page, "together", 0.1);
  const b = J<any>("baskets.json");
  const nonVariant = b.rules.filter((r: any) => !r.variant_of_same_product);
  const top = [...nonVariant].sort((x: any, y: any) => y.lift - x.lift)[0];
  await expect(page.locator("#together .ledger-line").first()).toContainText(`IN ${fmt(top.count)} OF ${fmt(b.params.baskets)} BASKETS`);
  await expect(page.locator("#together")).toContainText(`${top.lift.toFixed(1)}X CHANCE`);
  await expect(page.locator("#together")).toContainText(b.caveat.toUpperCase().slice(0, 60));
  await ctx.close();
});

test("S03b: cohort retention on screen equals retention x size", async ({ browser }) => {
  const { ctx, page } = await at(browser, VP(1440, 900));
  await openSite(page);
  await goScene(page, "back", 0.5);
  const c = J<any>("cohorts.json");
  const m = await page.evaluate(() => (window as any).__rs.view().spec.id);
  const month = Number(String(m).split(":")[2]);
  const retained = Math.round(c.retention[0][month] * c.sizes[0]);
  await expect(page.locator("#back")).toContainText(`${fmt(retained)} (${Math.round((retained / c.sizes[0]) * 100)}%)`);
  await expect(page.locator("#back")).toContainText(c.right_censoring.toUpperCase().slice(0, 40));
  await ctx.close();
});

test("S04: heads and pounds are the grid sums", async ({ browser }) => {
  const { ctx, page } = await at(browser, VP(1440, 900));
  await openSite(page);
  const r = J<any>("rfm.json");
  const sum = (g: number[][]) => { let ab = 0, tot = 0; g.forEach((row, i) => row.forEach((x, j) => { tot += x; if (i + 1 >= 4 && j + 1 >= 4) ab += x; })); return { ab, tot }; };
  const heads = sum(r.grid.r_by_f_customers), pounds = sum(r.grid.r_by_f_revenue_gbp);
  await goScene(page, "matters", 0.2);
  await expect(page.locator("#matters")).toContainText(`${fmt(heads.ab)} OF ${fmt(heads.tot)} CUSTOMERS ARE BOTH`);
  await goScene(page, "matters", 0.6);
  await expect(page.locator("#matters")).toContainText(`£${fmt(pounds.ab)}`);
  await ctx.close();
});

test("S05: the order at the default assumptions equals the published vector; the disclaimer is on screen", async ({ browser }) => {
  const { ctx, page } = await at(browser, VP(1440, 900));
  await openSite(page);
  await goScene(page, "stock", 0.12);
  const v = J<any>("newsvendor_vectors.json").vectors.find((x: any) => x.case === "normal_family:Bags and purses_c0.6_s0.2_default");
  await expect(page.locator("#stock .ledger-line").first()).toContainText(`ORDER ${fmt(v.expected.q_star)}`);
  const np = J<any>("newsvendor_params.json");
  expect(await text(page)).toContain(np.disclaimer.toUpperCase().slice(0, 50));
  await ctx.close();
});

test("S06: backtest verdict and CLV holdout figures are the artifact's", async ({ browser }) => {
  const { ctx, page } = await at(browser, VP(1440, 900));
  await openSite(page);
  const bt = J<any>("backtest.json"), cl = J<any>("clv.json");
  await goScene(page, "sells", 0.3);
  await expect(page.locator("#sells")).toContainText(bt.verdict.toUpperCase().slice(0, 50));
  await goScene(page, "sells", 0.75);
  await expect(page.locator("#sells")).toContainText(`TOTAL ERROR ${cl.holdout.total_error_pct.toFixed(1)}%`);
  await ctx.close();
});

test("THE COUNTER: products, an unpublished pair is drawn apart, inspector, reset", async ({ browser }) => {
  const { ctx, page } = await at(browser, VP(1440, 900));
  await openSite(page);
  await goScene(page, "counter", 0);
  await page.waitForTimeout(1500);
  const f = J<{ facts: Record<string, { value: number }> }>("facts.json").facts;
  await expect(page.locator("#counter")).toContainText(`BOTH: ${fmt(f.hero_pair_nab!.value)} BASKETS`);
  const b = J<any>("baskets.json");
  const lonely = b.nodes.find((n: any) => n.sku !== b.hero.a && b.nodes.filter((x: any) => x.description.toLowerCase() === n.description.toLowerCase()).length === 1 && !b.edges.some((e: any) => (e.a === b.hero.a && e.b === n.sku) || (e.b === b.hero.a && e.a === n.sku)));
  await page.getByLabel("Product B").fill(lonely.description);
  await expect(page.locator("#counter")).toContainText("FEWER THAN");
  const d = await page.evaluate(() => (window as any).__rs.drawn());
  await page.waitForTimeout(1200);
  const d2 = await page.evaluate(() => (window as any).__rs.drawn());
  expect(d2.kind).toBe("disjoint");
  void d;
  await page.locator("#counter").getByRole("button", { name: "RESET" }).click();
  await page.waitForTimeout(800);
  await expect(page.locator("#counter")).toContainText("BOTH:");
  await ctx.close();
});

test("zero external requests and zero console errors across every scene", async ({ browser }) => {
  const { ctx, page } = await at(browser, VP(1440, 900));
  const ext: string[] = [], errs: string[] = [];
  page.on("request", (r) => { if (!r.url().startsWith("http://localhost:4391") && !r.url().startsWith("data:") && !r.url().startsWith("blob:")) ext.push(r.url()); });
  page.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); });
  page.on("pageerror", (e) => errs.push(String(e)));
  await openSite(page);
  for (const [id, p] of WALK) await goScene(page, id, p);
  expect(ext).toEqual([]);
  expect(errs).toEqual([]);
  await ctx.close();
});

test("route-blocked baskets.json: error line with RETRY, then recovery", async ({ browser }) => {
  const { ctx, page } = await at(browser, VP(1440, 900));
  let block = true;
  await page.route("**/baskets.json", (r) => (block ? r.fulfill({ status: 500, body: "x" }) : r.continue()));
  await openSite(page);
  await goScene(page, "together", 0.3);
  await expect(page.locator("#together")).toContainText(/COULD NOT LOAD/i, { timeout: 8000 });
  block = false;
  await page.locator("#together").getByRole("button", { name: "RETRY" }).click();
  await expect(page.locator("#together .ledger-line").first()).toContainText("BASKETS", { timeout: 8000 });
  await ctx.close();
});

for (const vp of [VP(1440, 900), VP(1280, 720), VP(768, 1024), VP(390, 844), VP(375, 812), VP(360, 800)]) {
  test(`whole-document collision walk and text floor at ${vp.width}x${vp.height}`, async ({ browser }) => {
    const { ctx, page } = await at(browser, vp);
    await openSite(page);
    const bad: string[] = [];
    for (const [id, p] of WALK) {
      await goScene(page, id, p);
      for (const x of await collideAll(page)) bad.push(`${id}@${p}: ${x}`);
      const small = await page.evaluate(() => {
        const out: string[] = [], w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        for (let n = w.nextNode(); n; n = w.nextNode()) {
          const el = n.parentElement!;
          if (!n.textContent?.trim() || el.closest(".sr-only, script, style, [aria-hidden=true]")) continue;
          const r = el.getBoundingClientRect();
          if (r.width < 1 || r.bottom < 0 || r.top > innerHeight) continue;
          const cs = getComputedStyle(el);
          if (cs.display === "none" || cs.visibility === "hidden" || Number(cs.opacity) < 0.3) continue;
          if (parseFloat(cs.fontSize) < 9.99) out.push(`${n.textContent!.trim().slice(0, 24)} ${cs.fontSize}`);
        }
        return out;
      });
      for (const s of small) bad.push(`${id}@${p} small: ${s}`);
    }
    expect(bad).toEqual([]);
    await ctx.close();
  });
}

test("no sideways scroll at 1440, 1024, 768, 390, 360 in every scene", async ({ browser }) => {
  const bad: string[] = [];
  for (const w of [1440, 1024, 768, 390, 360]) {
    const { ctx, page } = await at(browser, VP(w, w < 768 ? 800 : 900));
    await openSite(page);
    for (const [id, p] of WALK) {
      await goScene(page, id, p);
      const sw = await page.evaluate(() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth));
      if (sw > w) bad.push(`${w} ${id}@${p}: ${sw}`);
    }
    await ctx.close();
  }
  expect(bad).toEqual([]);
});

test("pixel contrast >= 4.5:1 (3:1 large) for visible text at 1440 and 390", async ({ browser }) => {
  const bad: string[] = [];
  for (const vp of [VP(1440, 900), VP(390, 844)]) {
    const { ctx, page } = await at(browser, vp);
    await openSite(page);
    for (const [id, p] of [["pattern", 0.9], ["together", 0.5], ["back", 0.5], ["matters", 0.6], ["stock", 0.4], ["sells", 0.3], ["sells", 0.75], ["evidence", 0.95], ["counter", 0], ["closing", 0.95]] as [string, number][]) {
      await goScene(page, id, p);
      for (const f of await contrastFails(page)) bad.push(`${vp.width} ${id}@${p}: ${f}`);
    }
    await ctx.close();
  }
  expect(bad).toEqual([]);
});

test("axe: no serious or critical violations, motion and reduced motion", async ({ browser }) => {
  for (const reduced of [false, true]) {
    const { ctx, page } = await at(browser, VP(1440, 900), { reduced });
    await openSite(page);
    for (const [id, p] of [["pattern", 0.9], ["ledger", 0.3], ["together", 0.5], ["back", 0.5], ["matters", 0.6], ["stock", 0.4], ["sells", 0.3], ["evidence", 0.95], ["counter", 0], ["closing", 0.95]] as [string, number][]) {
      await goScene(page, id, p);
      const r = await new AxeBuilder({ page }).analyze();
      const bad = r.violations.filter((v) => v.impact === "serious" || v.impact === "critical").map((v) => `${id} ${v.id}: ${v.nodes.slice(0, 2).map((n) => n.target.join(" ")).join(" | ")}`);
      expect(bad, `reduced=${reduced}`).toEqual([]);
    }
    await ctx.close();
  }
});

test("reduced motion: scenes render in flow with their content and no intro", async ({ browser }) => {
  const { ctx, page } = await at(browser, VP(1440, 900), { reduced: true });
  await openSite(page);
  expect(await page.evaluate(() => document.documentElement.dataset.motion)).toBe("off");
  expect(await text(page)).toContain("The hidden patterns behind every purchase.");
  for (const id of ["ledger", "together", "back", "matters", "stock", "sells", "evidence", "counter", "closing"]) expect(await page.locator(`#${id}`).count()).toBe(1);
  await ctx.close();
});

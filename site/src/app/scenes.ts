/** Scene registry (VISUAL_DESIGN 3.1). `pattern` (S00 overlay + S01) is static HTML in index.html so the LCP headline paints before JS. */
export interface SceneDef { id: string; code: string; nav: string | null; track: string; landing: number; title: string }
export const SCENES: SceneDef[] = [
  { id: "pattern", code: "S01", nav: "PATTERN", track: "200vh", landing: 0.78, title: "A pattern is an overlap that chance can't explain." },
  { id: "ledger", code: "S02", nav: "THE LEDGER", track: "300vh", landing: 0.1, title: "A million lines, every one counted." },
  { id: "together", code: "S03a", nav: "TOGETHER", track: "300vh", landing: 0.1, title: "Bought together." },
  { id: "back", code: "S03b", nav: "COMING BACK", track: "300vh", landing: 0.1, title: "Coming back." },
  { id: "matters", code: "S04", nav: "WHO MATTERS", track: "300vh", landing: 0.1, title: "From heads to pounds." },
  { id: "stock", code: "S05", nav: "HOW MANY", track: "300vh", landing: 0.1, title: "How many to stock." },
  { id: "sells", code: "S06", nav: "WHAT SELLS", track: "300vh", landing: 0.1, title: "What will sell, and who will come back." },
  { id: "evidence", code: "S07", nav: "EVIDENCE", track: "250vh", landing: 0.05, title: "How we know." },
  { id: "counter", code: "COUNTER", nav: "THE COUNTER", track: "auto", landing: 0, title: "Put any two things side by side." },
  { id: "closing", code: "S08", nav: null, track: "200vh", landing: 0.3, title: "The pull, again." },
];
export const NAV_ITEMS = SCENES.filter((s) => s.nav).map((s) => ({ id: s.id, label: s.nav! }));
export const navActive = (scene: string | null) => (scene === "closing" ? "counter" : scene ?? "pattern");
export const sceneIndex = (id: string) => SCENES.findIndex((s) => s.id === id);
export const LINKS = {
  site: "https://mrrishit909.github.io/retail-intelligence-studio/",
  source: "https://github.com/mrrishit909/retail-intelligence-studio",
} as const;

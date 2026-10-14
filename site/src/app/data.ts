/** Core artifacts for S00 and S01 (facts, meta); the rest load per scene through useArtifact. */
import { useSyncExternalStore } from "react";
import { fetchJson, dataUrl, LoadError } from "../data/loader";

export interface FactsFile { facts: Record<string, { value: number | string; unit?: string; tag?: string; note?: string }> }
export interface MetaFile {
  source: { attribution: string; doi: string; licence: string; licence_url: string; dataset: string; publisher: string };
  no_demographics: string; disclaimers: string[];
  window: { first_ts: string; last_ts: string; first_week: string; last_complete_week: string; weeks_complete: number };
  engine: { seed: number; dbt_version: string; duckdb_version: string };
  pipeline_version: string;
}
export interface Core { facts: FactsFile; meta: MetaFile }
export type CoreState = { status: "initial" } | { status: "loading"; file: string } | { status: "ready"; data: Core } | { status: "error"; file: string; reason: string };

let state: CoreState = { status: "initial" };
const ls = new Set<() => void>();
const set = (s: CoreState) => { state = s; ls.forEach((l) => l()); };
const obj = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null;

export async function loadCore() {
  if (state.status === "loading" || state.status === "ready") return;
  let file = "facts.json";
  try {
    set({ status: "loading", file });
    const facts = await fetchJson(dataUrl("facts.json"), () => {});
    if (!obj(facts) || !obj((facts as Record<string, unknown>).facts)) throw new LoadError("FAILED ITS CHECKS");
    file = "meta.json";
    set({ status: "loading", file });
    const meta = await fetchJson(dataUrl("meta.json"), () => {});
    if (!obj(meta) || !obj((meta as Record<string, unknown>).source)) throw new LoadError("FAILED ITS CHECKS");
    set({ status: "ready", data: { facts: facts as unknown as FactsFile, meta: meta as unknown as MetaFile } });
  } catch (e) {
    set({ status: "error", file, reason: e instanceof LoadError ? e.message : "UNEXPECTED ERROR" });
  }
}
export const retryCore = () => { if (state.status === "error") { state = { status: "initial" }; void loadCore(); } };
export const useCore = () => useSyncExternalStore((l) => { ls.add(l); return () => void ls.delete(l); }, () => state, () => state);
export const getCore = () => state;
export const fv = (c: Core, k: string): number => Number(c.facts.facts[k]?.value);
export const fs = (c: Core, k: string): string => String(c.facts.facts[k]?.value ?? "");
export const fmt = (n: number, d = 0) => n.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
export const gbp = (n: number) => `£${Math.round(n).toLocaleString("en-US")}`;

/** Newsvendor closed forms (analytics/newsvendor.py ported; SIMULATED costs). Parity-tested against newsvendor_vectors.json. */
function erfSeries(x: number): number {
  // Maclaurin series, accurate to ~1e-13 for |x| < 3
  let term = x, sum = x;
  for (let n = 1; n < 80; n++) {
    term *= (-x * x) / n;
    const t = term / (2 * n + 1);
    sum += t;
    if (Math.abs(t) < 1e-17 * Math.abs(sum)) break;
  }
  return (2 / Math.sqrt(Math.PI)) * sum;
}
function erfcFraction(x: number): number {
  // continued fraction erfc(x) = exp(-x^2) / (sqrt(pi) (x + (1/2)/(x + 1/(x + (3/2)/(x + ...))))), evaluated from the tail, x >= 3
  let t = x;
  for (let k = 120; k >= 1; k--) t = x + k / 2 / t;
  return Math.exp(-x * x) / (Math.sqrt(Math.PI) * t);
}
function erfc(x: number): number {
  const ax = Math.abs(x);
  const v = ax < 3 ? 1 - erfSeries(ax) : erfcFraction(ax);
  return x < 0 ? 2 - v : v;
}
export const normCdf = (z: number) => 0.5 * erfc(-z / Math.SQRT2);
export const normPdf = (z: number) => Math.exp(-0.5 * z * z) / Math.sqrt(2 * Math.PI);
/** Phi^-1 by Newton with a bisection guard (cf strictly in (0, 1)) */
export function normInv(p: number): number {
  if (p <= 0) return -Infinity;
  if (p >= 1) return Infinity;
  let lo = -40, hi = 40, z = 0;
  for (let i = 0; i < 100; i++) {
    const f = normCdf(z) - p;
    if (f > 0) hi = z; else lo = z;
    const next = z - f / Math.max(normPdf(z), 1e-300);
    z = next >= lo && next <= hi ? next : (lo + hi) / 2;
    if (Math.abs(f) < 1e-16) break;
  }
  return z;
}
const loss = (z: number) => normPdf(z) - z * (1 - normCdf(z));

export interface Policy { critical_fractile: number; q_star: number; expected_profit: number; expected_sales: number; expected_leftover: number; expected_shortage: number; service_level: number }
export const fractile = (p: number, c: number, s: number) => (p - c) / (p - s);

export function normalPolicy(p: number, c: number, s: number, mu: number, sigma: number, q?: number): Policy {
  const cf = fractile(p, c, s);
  const Q = q ?? Math.max(0, mu + sigma * normInv(cf));
  const zq = (Q - mu) / sigma, z0 = -mu / sigma;
  const es = sigma * (loss(z0) - loss(zq));
  const left = Q - es;
  return { critical_fractile: cf, q_star: Q, expected_profit: p * es - c * Q + s * left, expected_sales: es, expected_leftover: left, expected_shortage: sigma * loss(zq), service_level: normCdf(zq) };
}
export function empiricalPolicy(p: number, c: number, s: number, samples: number[], q?: number): Policy {
  const d = [...samples].sort((a, b) => a - b);
  const cf = fractile(p, c, s), n = d.length;
  const Q = q ?? d[Math.max(Math.ceil(cf * n - 1e-12), 1) - 1]!;
  let sales = 0, below = 0, mean = 0;
  for (const x of d) { sales += Math.min(x, Q); mean += x; if (x <= Q) below++; }
  const es = sales / n;
  const left = Q - es;
  return { critical_fractile: cf, q_star: Q, expected_profit: p * es - c * Q + s * left, expected_sales: es, expected_leftover: left, expected_shortage: mean / n - es, service_level: below / n };
}
/** share of the normal fit's mass below zero, P(D < 0) = Phi(-mu / sigma) */
export const negativeMass = (mu: number, sigma: number) => normCdf(-mu / sigma);

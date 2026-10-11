"""Renders the P09 "Common Ground" sketches as SVG from cd_fixture.json (stdlib only).

cd_fixture.json is the Creative Director's own computation from the raw UCI file (2026-10-11),
used only to draw sketches. The build binds to the contracted artifacts (VISUAL_DESIGN section 6).
Run from the project root:  python3 design/sketches/render_pair_sketch.py
then rasterize:  NODE_PATH=../01-atlas-human-mobility/site/node_modules node design/sketches/render_sheet.mjs
"""
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
FX = json.loads((HERE / "cd_fixture.json").read_text())

ROSE = ("#4A0A24", "#A0105A", "#FF2F7A", "#FFB3CC")      # far rim .. near edge (anchor set)
ORANGE = ("#4A1206", "#B8321A", "#FF4C25", "#FFD2B0")    # partner set
PERI = ("#141A4A", "#3C4FD0", "#8FA2FF", "#DCE2FF")      # PREDICTED partner


def lens_area(r1, r2, d):
    if d >= r1 + r2:
        return 0.0
    if d <= abs(r1 - r2):
        return math.pi * min(r1, r2) ** 2
    a1 = r1 * r1 * math.acos((d * d + r1 * r1 - r2 * r2) / (2 * d * r1))
    a2 = r2 * r2 * math.acos((d * d + r2 * r2 - r1 * r1) / (2 * d * r2))
    k = 0.5 * math.sqrt((-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2))
    return a1 + a2 - k


def solve_d(r1, r2, area):
    """Centre distance whose overlap area equals `area` (bisection, monotone decreasing in d)."""
    lo, hi = abs(r1 - r2), r1 + r2
    if area >= math.pi * min(r1, r2) ** 2 - 1e-9:
        return lo
    for _ in range(200):
        mid = (lo + hi) / 2
        if lens_area(r1, r2, mid) > area:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def disc(id_, cx, cy, r, ux, uy, ramp, blend, alpha=1.0):
    """A disc lit from the side facing its partner (unit vector ux, uy toward the partner)."""
    x1, y1 = cx - ux * r, cy - uy * r
    x2, y2 = cx + ux * r, cy + uy * r
    g = (f'<linearGradient id="{id_}" gradientUnits="userSpaceOnUse" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}">'
         f'<stop offset="0" stop-color="{ramp[0]}" stop-opacity="{0.18*alpha:.2f}"/>'
         f'<stop offset="0.45" stop-color="{ramp[1]}" stop-opacity="{0.30*alpha:.2f}"/>'
         f'<stop offset="0.85" stop-color="{ramp[2]}" stop-opacity="{0.62*alpha:.2f}"/>'
         f'<stop offset="1" stop-color="{ramp[3]}" stop-opacity="{0.72*alpha:.2f}"/></linearGradient>')
    c = f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="url(#{id_})" style="mix-blend-mode:{blend}"/>'
    return g, c


def pair_svg(W, H, ca, ra, rb, overlap, axis, ramps=(ROSE, ORANGE), ghost=None, texts="", glow=True, extra=""):
    d = solve_d(ra, rb, overlap)
    ux, uy = axis
    cb = (ca[0] + ux * d, ca[1] + uy * d)
    defs, body = [], []
    g, c = disc("ga", ca[0], ca[1], ra, ux, uy, ramps[0], "normal"); defs.append(g); body.append(c)
    if ghost is not None:
        dg = solve_d(ra, rb, ghost)
        gx, gy = ca[0] + ux * dg, ca[1] + uy * dg
        body.append(f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="{rb:.1f}" fill="#fff" fill-opacity="0.06"/>')
    g, c = disc("gb", cb[0], cb[1], rb, -ux, -uy, ramps[1], "plus-lighter", alpha=1.35); defs.append(g); body.append(c)
    if glow and d < ra + rb:
        inner = max(d - rb, -ra)                                          # lens near end along the axis
        lx = (inner + ra) / 2                                             # lens midpoint along the axis
        mx, my = ca[0] + ux * lx, ca[1] + uy * lx
        half = (ra - inner) / 2
        defs.append(f'<clipPath id="ov"><circle cx="{ca[0]:.1f}" cy="{ca[1]:.1f}" r="{ra:.1f}"/></clipPath>'
                    f'<radialGradient id="hot" gradientUnits="userSpaceOnUse" cx="{mx:.1f}" cy="{my:.1f}" r="{max(half, 40) * 1.6:.1f}">'
                    '<stop offset="0" stop-color="#FFFFFF" stop-opacity="0.98"/><stop offset="0.45" stop-color="#FFE9E2" stop-opacity="0.85"/>'
                    '<stop offset="1" stop-color="#FF9A8A" stop-opacity="0.35"/></radialGradient>'
                    '<filter id="bl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="18"/></filter>')
        body.append(f'<g clip-path="url(#ov)"><circle cx="{cb[0]:.1f}" cy="{cb[1]:.1f}" r="{rb:.1f}" fill="url(#hot)" style="mix-blend-mode:plus-lighter"/></g>')
        body.append(f'<g style="mix-blend-mode:screen" opacity="0.35" filter="url(#bl)"><g clip-path="url(#ov)">'
                    f'<circle cx="{cb[0]:.1f}" cy="{cb[1]:.1f}" r="{rb:.1f}" fill="#fff" fill-opacity="0.6"/></g></g>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
           f'<defs>{"".join(defs)}</defs><rect width="{W}" height="{H}" fill="#000"/>'
           f'<g style="isolation:isolate">{"".join(body)}</g>{extra}{texts}</svg>')
    return svg, d, cb


SERIF = "font-family:Newsreader,Georgia,serif"
MONO = "font-family:'JetBrains Mono',ui-monospace,monospace"


def t(x, y, s, size, fill="#fff", mono=False, anchor="start", op=1.0):
    fam = MONO if mono else SERIF
    s = s.replace("&", "&amp;")
    return (f'<text x="{x}" y="{y}" style="{fam};font-size:{size}px" fill="{fill}" fill-opacity="{op}" '
            f'text-anchor="{anchor}" paint-order="stroke" stroke="#000" stroke-width="{3 if mono else 0}">{s}</text>')


def chip(x, y, s, color="#fff"):
    w = 8 * 2 + len(s) * 7.8
    return (f'<rect x="{x}" y="{y-14}" width="{w:.0f}" height="22" fill="#fff" fill-opacity="0.1"/>'
            + t(x + 8, y + 2, s, 13, color, mono=True))


hero = dict(FX["pairs_by_count"][0])   # the pair bought together most often (DR-1 rule)
if hero["na"] < hero["nb"]:              # the anchor (giant, left) is always the larger set
    for x, y in (("a", "b"), ("a_desc", "b_desc"), ("na", "nb")):
        hero[x], hero[y] = hero[y], hero[x]
N, NA, NB, NAB = FX["baskets"], hero["na"], hero["nb"], hero["nab"]
CHANCE = NA * NB / N


def s00(W, H, mode, t_state):
    if mode == "d":
        ra = 0.62 * H                       # 558: diameter 1.24 x frame height
        k = math.pi * ra * ra / NA          # px^2 per basket, constant within the viewport
        rb = math.sqrt(NB * k / math.pi)
        ov = (NAB if t_state == "end" else CHANCE) * k
        rb0 = math.sqrt(NB / NA) * ra
        d0 = solve_d(ra, rb0, NAB / NA * math.pi * ra * ra)
        xc = (d0 * d0 + ra * ra - rb0 * rb0) / (2 * d0)          # common chord, from A's centre
        ca, axis = (1000 - xc, 450), (1, 0)                     # chord at x 1000; cusps inside the frame
        head = (t(96, 160, "The hidden patterns", 72) + t(96, 236, "behind every", 72) + t(96, 312, "purchase.", 72)
                + t(96, 360, "THE PAIR BOUGHT TOGETHER MOST OFTEN", 15, mono=True, op=0.7))
        corner = (t(96, 48, "RETAIL INTELLIGENCE STUDIO", 13, mono=True)
                  + t(W - 96, 48, f"{N:,} BASKETS · DEC 2009 TO DEC 2011 · UK GIFT-WARE WHOLESALER", 13, mono=True, anchor="end")
                  + t(W - 96, 68, "AREA = BASKETS · OVERLAP = BOUGHT TOGETHER", 13, mono=True, anchor="end", op=0.6))
        scrim = ('<defs><linearGradient id="sc" x1="0" x2="1"><stop offset="0" stop-color="#000" stop-opacity=".88"/>'
                 '<stop offset="1" stop-color="#000" stop-opacity="0"/></linearGradient></defs>'
                 '<rect x="0" y="80" width="760" height="310" fill="url(#sc)"/>')
        foot = chip(96, 820, "OBSERVED · 1 ITEM PAIR · UCI ONLINE RETAIL II · CC BY 4.0")
        svg, d, cb = pair_svg(W, H, ca, ra, rb, ov, axis, extra=scrim, texts=head + corner + foot)
        cap_x = ca[0] + ra - 0.5 * (ra + rb - d) + 30
        lab = (t(ca[0] - 120, 640, hero["a_desc"], 13, mono=True, anchor="end")
               + t(ca[0] - 120, 660, f"{NA:,} BASKETS", 13, mono=True, anchor="end", op=0.6)
               + t(cb[0] + 140, 640, hero["b_desc"], 13, mono=True)
               + t(cb[0] + 140, 660, f"{NB:,} BASKETS", 13, mono=True, op=0.6))
        if t_state == "end":
            lab += (t(W - 96, 790, f"BOTH: {NAB:,} BASKETS · CHANCE WOULD GIVE {CHANCE:.0f} · LIFT {NAB / CHANCE:.1f}", 13,
                      mono=True, anchor="end"))
        else:
            lab += t(W - 96, 790, f"WHERE CHANCE ALONE PUTS THEM: {CHANCE:.0f} BASKETS IN COMMON", 13, mono=True, anchor="end")
        return svg.replace("</svg>", lab + "</svg>")
    # mobile: vertical axis, anchor above, partner pulled up from below
    ra = 300                                # diameter 600 = 1.54 x width: cropped left and right
    k = math.pi * ra * ra / NA
    rb = math.sqrt(NB * k / math.pi)
    ov = NAB * k
    d0 = solve_d(ra, rb, ov)
    xc = (d0 * d0 + ra * ra - rb * rb) / (2 * d0)
    ux, uy = 0.6, 0.8                        # diagonal axis: both cusps (chord 447px) inside the frame
    ca, axis = (205 - ux * xc, 480 - uy * xc), (ux, uy)
    head = (t(16, 92, "The hidden patterns", 36) + t(16, 132, "behind every", 36) + t(16, 172, "purchase.", 36))
    scrim = ('<defs><linearGradient id="sc" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#000" stop-opacity=".9"/>'
             '<stop offset="1" stop-color="#000" stop-opacity="0"/></linearGradient></defs>'
             '<rect x="0" y="0" width="390" height="230" fill="url(#sc)"/>')
    corner = t(16, 30, "RETAIL INTELLIGENCE STUDIO", 11, mono=True)
    foot = (chip(16, 730, "OBSERVED · CC BY 4.0") + t(16, 764, f"BOTH: {NAB:,} OF {N:,} BASKETS · LIFT {NAB / CHANCE:.1f}", 11, mono=True)
            + '<rect x="115" y="796" width="160" height="32" fill="#fff"/>' + t(195, 817, "= MENU · THE PULL", 12, "#000", mono=True, anchor="middle"))
    svg, d, cb = pair_svg(W, H, ca, ra, rb, ov, axis, extra=scrim, texts=head + corner + foot)
    return svg


def s03b(W, H):
    coh = FX["cohort_2009_12"]
    size, kept, active = coh[0], coh[12], FX["active_by_month"]["2010-12"]
    ra = 330
    k = math.pi * ra * ra / size
    rb = math.sqrt(active * k / math.pi)
    texts = (t(96, 150, "Who came back.", 64)
             + t(96, 210, "COHORT: FIRST BOUGHT DEC 2009", 15, mono=True)
             + t(96, 236, f"{size:,} CUSTOMERS · MONTH 12 OF 24", 15, mono=True, op=0.7)
             + t(96, 300, f"STILL BUYING IN DEC 2010: {kept} ({kept / size:.0%})", 15, mono=True)
             + t(96, 326, f"ALL ACTIVE CUSTOMERS THAT MONTH: {active:,}", 15, mono=True, op=0.7)
             + chip(96, 380, "DERIVED · KNOWN CUSTOMERS ONLY · GUESTS EXCLUDED", "#58B8E1")
             + t(96, 440, "MONTH  0  1  2  3 ... 12 ... 24", 13, mono=True, op=0.6)
             + t(820, 840, "AREA = CUSTOMERS · OVERLAP = RETAINED", 13, mono=True, anchor="middle", op=0.6))
    svg, d, cb = pair_svg(W, H, (860, 470), ra, rb, kept * k, (0.55, 0.835), texts=texts)
    return svg


def s05(W, H):
    nv = FX["nv_item"]
    mu, sd, p = nv["mean"], nv["sd"], nv["price"]
    c, s = 0.5 * p, 0.1 * p                          # illustrative cost and salvage ratios (SIMULATED)
    cf = (p - c) / (p - s)
    z = nd_ppf(cf)
    q = mu + z * sd
    pdf, cdf = math.exp(-z * z / 2) / math.sqrt(2 * math.pi), cf
    short = sd * (pdf - z * (1 - cdf))               # E[(D - q)+]
    sales = mu - short
    left = q - sales
    ra = 340
    k = math.pi * ra * ra / mu                       # demand disc = expected demand
    rb = math.sqrt(q * k / math.pi)                  # stock disc = order quantity
    texts = (t(96, 150, "How many to stock.", 64)
             + t(96, 210, "WHITE HANGING HEART T-LIGHT HOLDER · ONE WEEK", 15, mono=True)
             + t(96, 250, f"DEMAND (FITTED NORMAL) {mu:,.0f} ± {sd:,.0f} UNITS", 15, mono=True, op=0.7)
             + t(96, 276, f"COST 50% OF PRICE · SALVAGE 10% · CRITICAL RATIO {cf:.2f}", 15, mono=True, op=0.7)
             + t(96, 330, f"ORDER {q:,.0f}", 15, mono=True)
             + t(96, 356, f"EXPECTED SOLD {sales:,.0f} · LEFT OVER {left:,.0f} · SHORT {short:,.0f}", 15, mono=True)
             + chip(96, 410, "SIMULATED · ASSUMPTIONS ARE ILLUSTRATIVE", "#FF4C25")
             + t(96, 470, "COST RATIO  [ 0.30 ── 0.50 ── 0.80 ]", 13, mono=True, op=0.7)
             + t(96, 496, "SALVAGE     [ 0.00 ── 0.10 ── 0.40 ]", 13, mono=True, op=0.7)
             + t(1010, 840, "LEFT: DEMAND · RIGHT: STOCK · OVERLAP = EXPECTED SALES", 13, mono=True, anchor="middle", op=0.6))
    svg, d, cb = pair_svg(W, H, (860, 470), ra, rb, sales * k, (1, 0), ramps=(ROSE, ORANGE), texts=texts)
    return svg


def nd_ppf(pr):
    lo, hi = -10.0, 10.0
    for _ in range(200):
        m = (lo + hi) / 2
        if 0.5 * (1 + math.erf(m / math.sqrt(2))) < pr:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def selfcheck():
    r1, r2 = 300.0, 220.0
    for a in (1.0, 5000.0, 60000.0, math.pi * r2 * r2 * 0.99):
        assert abs(lens_area(r1, r2, solve_d(r1, r2, a)) - a) < 1e-6 * max(a, 1)
    assert abs(nd_ppf(0.975) - 1.959964) < 1e-5


if __name__ == "__main__":
    selfcheck()
    out = {
        "pair-s00-d.svg": s00(1440, 900, "d", "end"),
        "pair-s00-t0-d.svg": s00(1440, 900, "d", "t0"),
        "pair-s00-m.svg": s00(390, 844, "m", "end"),
        "pair-s03b-d.svg": s03b(1440, 900),
        "pair-s05-d.svg": s05(1440, 900),
    }
    for name, svg in out.items():
        (HERE / name).write_text(svg)
    print("wrote", list(out), f"hero {NA}/{NB}/{NAB} of {N}, chance {CHANCE:.1f}, lift {NAB / CHANCE:.2f}")

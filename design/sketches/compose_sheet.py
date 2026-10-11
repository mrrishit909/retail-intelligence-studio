"""Composes distinctness-sheet.png (240px-tall tiles, ENGINEERING_DECISIONS #17) and p09-pair-check.png.
Real build frames for P01-P05; P06, P07, P08 and P10 have no build frames yet, so their CD sketches are used and labelled.
Run from the project root: uv run --with pillow python design/sketches/compose_sheet.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

HERE = Path(__file__).parent
PJ = HERE / "../../.."
tiles = [
    (PJ / "01-atlas-human-mobility/artifacts/evidence/stage-b3/1440x900/06-futures-a-busier.png", "P01 REAL FRAME: STROKED RING, CHORDS"),
    (PJ / "02-market-microstructure-lab/artifacts/evidence/stage-a/1440x900/00-s00-t3600.png", "P02 REAL FRAME: ELECTRIC ORB, S00"),
    (PJ / "03-climate-signal-observatory/artifacts/evidence/stage-a/1440x900/01-s00-t4600-end.png", "P03 REAL FRAME: SOLAR GLOBE, S00 END"),
    (PJ / "04-pulse-energy-grid/artifacts/evidence/stage-b/1440x900/fix1-s00-t3500.png", "P04 REAL FRAME: DAY ROSE, S00"),
    (PJ / "05-economic-atlas/artifacts/evidence/stage-a/1440x900/01-s00-t4600-end.png", "P05 REAL FRAME: SEED HEAD, S00 END"),
    (PJ / "06-sentinel-anomaly-lab/design/sketches/lens-s00-d.png", "P06 SKETCH (NO FRAMES): THE LENS"),
    (PJ / "07-supply-chain-orchestra/design/sketches/dock-s00-d.png", "P07 SKETCH (NO FRAMES): CROSS-DOCK"),
    (PJ / "08-healthscape/design/sketches/tissue-s00-d.png", "P08 IN-PROGRESS SKETCH: TISSUE DISC"),
    (PJ / "10-decision-universe/design/sketches/turn-s00-d.png", "P10 SKETCH (APPROVED): THE TURN"),
    (HERE / "pair-s00-d.png", "P09 SKETCH: COMMON GROUND, S00 END"),
    (HERE / "pair-s00-t0-d.png", "P09 SKETCH: S00 T0, AT CHANCE"),
    (HERE / "pair-s03b-d.png", "P09 SKETCH: S03B COHORT X MONTH 12"),
    (HERE / "pair-s05-d.png", "P09 SKETCH: S05 STOCK X DEMAND"),
]
W, H, LAB, G = 384, 240, 18, 8


def fit(p):
    im = Image.open(p).convert("RGB")
    return ImageOps.fit(im, (W, H), Image.LANCZOS) if abs(im.width / im.height - W / H) > 0.2 else im.resize((W, H), Image.LANCZOS)


ROWS = -(-len(tiles) // 4)
sheet = Image.new("RGB", (4 * W + 5 * G + 140, ROWS * (H + LAB) + (ROWS + 1) * G), "#111")
d = ImageDraw.Draw(sheet)
for i, (p, label) in enumerate(tiles):
    x, y = G + (i % 4) * (W + G), G + (i // 4) * (H + LAB + G)
    sheet.paste(fit(p), (x, y + LAB))
    d.text((x + 2, y + 3), label, fill="#FF8FB0" if label.startswith("P09") else "#fff")
m = Image.open(HERE / "pair-s00-m.png").convert("RGB")
mh = 2 * (H + LAB) - LAB + G
mw = round(m.width * mh / m.height)
x = G + 4 * (W + G)
sheet.paste(m.resize((mw, mh), Image.LANCZOS), (x, G + LAB))
d.text((x + 2, G + 3), "P09 S00 M", fill="#FF8FB0")
sheet.save(HERE / "distinctness-sheet.png")

pair = [tiles[1], tiles[2], tiles[6], tiles[9]]
ps = Image.new("RGB", (4 * W + 5 * G, 2 * (H + LAB) + 3 * G), "#111")
d = ImageDraw.Draw(ps)
for i, (p, label) in enumerate(pair):
    im = fit(p)
    for row, img in enumerate((im, ImageOps.grayscale(im).convert("RGB"))):
        x, y = G + i * (W + G), G + row * (H + LAB + G)
        ps.paste(img, (x, y + LAB))
        d.text((x + 2, y + 3), label + (" (GREY)" if row else ""), fill="#fff")
ps.save(HERE / "p09-pair-check.png")
print("sheet", sheet.size, "pair", ps.size)

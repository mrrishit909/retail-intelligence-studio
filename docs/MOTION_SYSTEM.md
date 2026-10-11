# Motion system: Retail Intelligence Studio

This is the phase 17 motion bible. It pairs with `VISUAL_DESIGN.md`, and all references point there:

- scene ids S00-S08 and THE COUNTER
- geometry states G0 (giant), G0 chance, G1 (aside), G2 (scene) and G5 (counter)
- interaction numbers 1-11

Every value here is binding for the frontend engineer. A deviation needs a written reason in `docs/ENGINEERING_DECISIONS.md` (the orchestrator owns that file).

## Contents

1. [Global principles and the six motion layers](#1-global-principles-and-the-six-motion-layers)
2. [Hard rules](#2-hard-rules)
3. [Token mapping](#3-token-mapping)
4. [The scroll engine and the pair transition model](#4-the-scroll-engine-and-the-pair-transition-model)
5. [Animation specifications](#5-animation-specifications)
6. [Navigation, chapter jumps, interruption](#6-navigation-chapter-jumps-interruption)
7. [Operational state motion](#7-operational-state-motion)
8. [Reduced motion](#8-reduced-motion)
9. [Performance budgets and rendering](#9-performance-budgets-and-rendering)
10. [Technical stack recommendation](#10-technical-stack-recommendation)
11. [Motion test plan](#11-motion-test-plan)

---

## 1. Global principles and the six motion layers

1. **Motion performs the analysis. Nothing moves to decorate.** Every motion is the visible form of an operation:

   | Motion | Operation |
   |---|---|
   | A disc *lights* from its far rim inward to its size | a set is counted |
   | The partner *is pulled* along the axis from its chance position | lift: the pattern exceeds what popularity alone predicts |
   | The partner *is pushed* back toward chance (or apart) | the closing's rewind; a rule weaker than chance (lift < 1) settles further out than its ghost |
   | The overlap *widens and whitens*, or *narrows and dims* | more or less shared ground (retention over months, a better or worse forecast) |
   | A disc *swells or shrinks* in place | its set changes size (the active customers each month, the order quantity) |
   | Both discs *re-size together* | a change of unit (customers to pounds, S04) |
   | A partner's edge *softens* | a prediction and its interval |
   | A disc *goes to hatch* | the quantity is unknown or not estimable |

2. **Along the axis, or in place. Never around.** Discs move only along the line through their centres, or change radius in place. Nothing rotates, nothing orbits, nothing travels along a circumference, nothing sweeps, and centres never coincide.
3. **Two motion modes,** from the reference:
   - **Scrubbed.** A pure function of scroll progress, reversible and stateless: G-state camera moves, card decks, word reveals.
   - **Stepped.** A threshold triggers a timed, retargetable transition: rule steps, months, RFM states, stock states, backtest states, argument cards, the echo.
4. **Data is shown only at real states.**
   - Every rule, month, threshold, item and model on screen is a published record or a closed-form browser value with vector parity.
   - In transit, the pair is an exact Euler pair of interpolated sizes (4), but **no readout shows a value in transit**. Ledgers swap to the new record on landing (numerals tween 600ms from old to new real values in a fixed `ch` box).
   - Set labels follow their discs; they never show an interpolated size.
5. **Light follows meaning.** The overlap's brightness is fixed by the encoding (VISUAL_DESIGN section 0); it changes only because the overlap's area changes. No flicker, no pulse, no "breathing" glow. The bloom is static and redrawn only on settle.
6. **One luminous form at a time:**
   - In S00 and S08 it is the giant pair at G0 and its overlap bloom.
   - From S01 to THE COUNTER it is the pair at scene size. In S02 it dims to 20%, in S07 to 15%, behind the cards. S02 card 2's small pair is the only second pair on the page, inside a card, while the stage pair is at 20%.
7. **Slow structure, quick data.** Camera moves take 800-1200ms or are scrubbed. The pull takes 1600ms in the intro and echo, 1200ms on scroll steps, 800ms on a control change. Crossfades take 200ms, numerals 600ms.
8. **Keyed continuity:**
   - the anchor disc by the scene's anchor role, the partner by its role: they persist across steps within a scene and travel; they never swap identity
   - between scenes with different units (S03a → S03b, S04 → S05), the pair **crossfades** (350ms) instead of travelling, because the sets are different things
   - between scenes with the same unit (S03b → S04, both customers), the pair **re-sizes in place**
9. **Settle, don't bounce.** No overshoot on any disc or overlap. Springs (damping ratio 1.0 or more) only on bottom sheets.
10. **The visitor always wins.** Any input retargets or completes an animation immediately. Nothing queues.

### The six motion layers (directive requirement)

| Layer | Where it lives | Spec |
|---|---|---|
| 1. Intro | S00 The Pull: the anchor lights, the partner lights at chance, the pull, the overlap whitens, readout, labels, headline, nav | 5.1 |
| 2. Navigation transitions | Bottom bar active block, MENU pill with the current section name, chapter jumps with a stage fade, focus moves | 6 |
| 3. Scroll storytelling | G-state moves, the S01 aside, the S02 deck, rule steps, the month scrub, the unit switch, the stock states, the backtest and CLV states, the echo | 4, 5.2-5.11 |
| 4. Component interaction | Steppers, segmented controls, sliders, native selects, the inspector, bottom sheets, disc hover | 5.12, 5.13 |
| 5. Data transitions | The pull, re-sizes, the unit switch, PREDICTED soft-edge changes, hatch in and out, numerals | 4, 5.4-5.9 |
| 6. Microinteractions | Hover, press and focus on squares and chips, tooltips, ✓ and ✗ marks, the RESET confirmation, the loading percentage | 5.13, 7 |

## 2. Hard rules

Each rule is checked in QA.

| Rule | Test |
|---|---|
| **LCP:** `h1[data-hero]` is in the HTML and painted from first paint as ghost text (opacity 0.55, `filter: blur(12px)`, ENGINEERING_DECISIONS #10), never at opacity 0. The display font is preloaded, with a metric-matched fallback (ENGINEERING_DECISIONS #9). The canvas is created after first paint | Lighthouse: the LCP element is `h1[data-hero]`, LCP 2.5s or less, CLS 0.1 or less (mobile and desktop presets) |
| **Nothing heavy on the LCP path.** First paint needs only `facts.json` and `meta.json` (DR-1 puts the hero pair in facts). Every other artifact loads at its scene's approach (9.3) | A Lighthouse waterfall shows no other data request before FCP |
| **Area rule.** At every rest state: each disc area / k = its set size, overlap area / k = the shared size (1e-9 relative). At S00 t0 and in any ghost: overlap / k = chance | A debug hook (`window.__p09.pair()`) reports `{sizeA, sizeB, shared, k, rA, rB, d, overlapPx}`; checked at the S00 end, every S03a step, S03b months 0/12/24, every S04 state, the S05 default and all four S06 states |
| **Never concentric, never around.** No rotation transform or angular parameter exists in `src/pair`; `d` is never 0 (containment is internally tangent, `d = rA − rB` with `rA > rB`, or the larger set becomes the anchor) | Code review plus a grep for `rotate(` and angle uniforms in `src/pair` (the hatch's fixed 45° pattern transform is allowlisted) |
| **No value in transit.** No ledger, label or tooltip shows an interpolated size | Playwright samples 10 frames of a rule step and a month step: ledgers hold either the old or the new record's numbers, never others |
| **The only blur is meaning.** CSS `filter: blur` appears only on the ghost-word state and the static bloom canvas; the canvas blurs only a PREDICTED partner's edge band | Code review; a grep for `blur(` lists exactly those three call sites |
| Animate only `transform`, `opacity` and `filter` (at most 14 word spans at once) in the DOM. The canvas draws its own pixels. Never animate layout properties or `backdrop-filter` | A DevTools trace shows no Layout events inside scrubbed frames |
| **One `requestAnimationFrame` loop** owns Lenis, progress, tweens and the canvas draw | Grep finds one `requestAnimationFrame` call site (`src/motion/loop.ts`) |
| No artificial delays, no fake progress, no fake spinner | Code review: no `setTimeout` gates any data display |
| No drawing on hidden stages. The canvas redraws only when dirty (progress changed, a transition is active, a control moved) | Playwright: with S07 centred, the canvas frame counter is flat for 2s once the cards settle |

## 3. Token mapping

| Token | Value | Used for |
|---|---|---|
| `--motion-fast` | 200ms | Nav hover (reference `0.2s ease-in-out`), tooltips, legend and label swaps, the pill label swap, the unit label crossfade |
| `--motion-standard` | 350ms | Argument card stack (reference `all .35s ease-in-out`), intro completion on input, chapter-jump stage fade, segmented active block, scene crossfades between units, dims, inspector exit |
| `--motion-panel` | 600ms | Numeral tweens, hatch in and out, soft-edge width changes, data entering after load |
| `--motion-card` | 800ms | Story-card settle, G-state moves on a jump, **control-driven pulls and re-sizes**, the S05 to S06 recolour, the S08 push back |
| `--motion-scene` | 1200ms | **Scroll-step pulls** (S03a rules, S03b months, S04 states, S06 states), the reference's `transform 1.2s cubic-bezier(.33,1,.68,1)` |
| 1600ms | (composite, the intro's and echo's pull) | The S00 pull and the S08 pull only |
| `--ease-premium` `cubic-bezier(.5,0,0,1)` | | Entrances and departures: cards, nav enter, inspector, a disc lighting |
| `--ease-symmetric` `cubic-bezier(.5,0,.5,1)` | | Every scrubbed interpolation (G-state camera), the S08 push back |
| `--ease-smooth` `cubic-bezier(.33,1,.68,1)` | | Every pull and re-size, numeral tweens, word sharpening |
| `linear` | | Story progress segments, loading percentages (no easing on measurements) |
| `ease-in-out` | | Nav hover only (matches the reference) |

These fall inside the directive's ranges:

| Directive category | Directive range (ms) | Our value (ms) |
|---|---|---|
| Hover | 120-250 | 120-200 |
| Buttons | 150-300 | 200-350 |
| Panels | 250-600 | 350-600 |
| Charts | 400-1000 | 600-800 |
| Section transitions | 700-1800 | 800-1200 |
| Cinematic | 1000-3000 | 1200-1600, plus the 4.6s composite intro |

## 4. The scroll engine and the pair transition model

Reuse the app shell already ported through P01-P07 (`site/src/motion`, `scroll`, the loader and the nav). Do not rebuild it.

**The scroll engine:**

- **Tracks.** A `<section>` with the track height from VISUAL_DESIGN 3.1, and a sticky `100dvh` stage inside it. Progress is `p = clamp((scrollY - trackTop) / (trackHeight - innerHeight), 0, 1)` from Lenis's value, with geometry cached and re-measured on resize.
- **Active set.** Only the scene at the viewport centre and the next scene receive `update(p, dt)`. One canvas serves every scene except the S02 card 2 pair (its own small canvas, drawn once on card activation).
- **Scrubbed** functions take the form `s = ease((p - a) / (b - a))`, clamped. They hold no state.
- **Stepped** thresholds use **hysteresis ±0.02**.
- **Lenis:** `lerp 0.1` on D, native touch scroll on T/M (`syncTouch: false`), and off under reduced motion.
- **Viewport class** from `matchMedia`/`innerWidth`, one source shared with CSS (ENGINEERING_DECISIONS #39).

**The pair transition model** (`src/pair/`):

- **Geometry** (`geometry.ts`, pure). `lensArea(rA, rB, d)` in closed form (VISUAL_DESIGN reference 5); `solveD(rA, rB, area)` by bisection on `[|rA − rB|, rA + rB]` to 1e-12 of the radius (monotone decreasing), returning `|rA − rB|` for full containment and `rA + rB + 0.06 rB` for zero. Vitest checks `lensArea(solveD(a)) = a` at 10,000 random points and the containment and disjoint edges.
- **A pair state** is `{sizeA, sizeB, shared, chance | null, k, camera: {chord point, axis, scale}}`. Radii are `sqrt(size × k / π) × scale`. The chord point is where the common chord crosses the axis, so the overlap stays where the composition put it as sizes change (the anchor's centre is `chord − axis × xc`, with `xc = (d² + rA² − rB²) / (2d)`).
- **A transition** from state S to state T with eased parameter `e`:
  - `sizeA`, `sizeB` and `shared` interpolate in **log space** (`exp(mix(ln x0, ln x1, e))`; a zero endpoint uses `ln(1e-6 × max)` so it fades through tiny, never negative)
  - `shared` is clamped every frame to `[0, min(sizeA, sizeB)]`
  - `d` is **re-solved every frame** from the interpolated sizes: every frame is an exact Euler pair
  - the camera interpolates linearly (chord point) and in log space (scale)
- **The pull** is the transition from `shared = chance` to `shared = observed` with sizes fixed: only `d` changes, so the partner travels along the axis. **The push** is its reverse.
- **Retargeting.** On a new transition mid-flight, the current interpolated state becomes the new `from`. No queue.
- **Lighting** (`light.ts`). Each disc's linear gradient is re-anchored to the current axis every frame (two gradients, no allocation churn: cached `CanvasGradient`s rebuilt only when the centre moves by more than 0.5px). The overlap is drawn by clipping to disc A and filling disc B with the overlap field. The **overlap field** is a pre-rendered 256x256 almond-agnostic texture of the distance-to-boundary falloff, drawn with a transform that maps it to the overlap's bounding box along the axis (its midline on the axis's perpendicular bisector of the lens extent). It is never a radial gradient centred on a point (VISUAL_DESIGN section 0, Light).
- **Soft edge** (PREDICTED). The partner is drawn as the median disc plus a ring-free radial alpha falloff from `r(lo)` to `r(hi)`: a radial gradient on the disc's own centre whose stops sit at those radii (alpha 1 at `r(lo)`, 0 at `r(hi)`). It reads as a blurred edge, never as a ring (no stop rises again).
- **Hatch** (unknown). A cached 6px-pitch 45° pattern, clipped to the disc, 12% white.

## 5. Animation specifications

Format for each entry: **Trigger**, **Initial → End**, **Duration / Easing**, **Sync** (scrubbed or stepped), **Interruption**, **Input**, **Reduced motion**, **Performance**.

### 5.1 S00 intro: "The Pull" (4.6s total)

| t (ms) | Event | Duration / easing |
|---|---|---|
| 0 | Black. `h1[data-hero]` is ghost text under its scrim. SKIP INTRO visible | |
| 200 | Corner labels fade in (opacity 0 → 1) | 350ms `--ease-premium` |
| 500 | **The anchor lights:** its gradient's alpha multiplier 0 → 1, revealed from the far rim toward the near rim (a moving clip along the axis, linear in x) | 900ms `--ease-premium` |
| 1100 | **The partner lights at the chance position** (G0 chance, d 819 on D), same reveal from its far rim | 700ms `--ease-premium` |
| 1700 | The chance readout fades in: `WHERE CHANCE ALONE PUTS THEM: {{chance}} BASKETS IN COMMON`; the ghost (6% white) is born at the partner's position and stays | 200ms |
| 2100 | **The pull:** chance → observed (4), the overlap widens and whitens | **1600ms `--ease-smooth`** |
| 3700 | The overlap bloom canvas is drawn once and fades in (0 → 0.35) | 350ms |
| 3700 | Readout crossfades to `BOTH: {{shared}} … LIFT {{lift}}`; set labels sharpen (ghost → sharp) | 200ms / 600ms |
| 3900 | Headline sharpens word by word (5.2) | 600ms + 60ms stagger |
| 4300 | Nav enters (`--ease-premium`, translateY 16px → 0, opacity) | 300ms |
| 4600 | Done; `intro = 'done'`; focus stays where it was |  |

- **Interruption:** SKIP, Esc, any wheel/touch/key scroll: every running tween completes to its end value in 350ms `--ease-smooth`; the intro is marked done.
- **Data late:** if DR-1's facts are not in by 500ms, the timeline holds at t 500 (labels on, headline ghost) until data arrives or 6s pass; then the end state fades in over 350ms.
- **Reduced motion:** the end state at t 0 (ghost visible), headline sharp, nav present.
- **Performance:** two gradient discs, one clipped overlap fill, one ghost per frame; target under 2ms per frame on D, measured in QA.

### 5.2 Word blur reveal (S00 headline, S01 statement, S08 paragraph, statement swaps)

- Each word: opacity 0.55 → 1 and `blur(12px)` → 0, 600ms `--ease-smooth`, 60ms stagger (scrubbed in S01 and S08: word i sharpens at `p = a + (b − a) × i / n`).
- At most 14 word spans animate at once; longer statements reveal by line.
- Statement swaps (scene to scene): old words fade to 0 (200ms), new words enter as ghosts and sharpen.
- **Reduced motion:** sharp at once.

### 5.3 Camera moves (G0 → G1 → G2, G5, and back to G0)

- **Trigger:** scrubbed by scroll in S01 (G0 → G1), S02 exit (G1 → G2), S08 (→ G0); stepped (800ms `--ease-symmetric`) on a chapter jump.
- **Initial → End:** chord point linear, scale log-space, axis rotates **never**: a scene with a different axis (S03b, S04 diagonal; S03a, S05, S06 horizontal) **crossfades** the pair (350ms) instead of turning it.
- **Interruption:** scrubbed moves follow scroll; a jump mid-move retargets from the current camera.
- **Reduced motion:** cuts.

### 5.4 Bought Together: rule steps (S03a)

- **Trigger:** scroll steps p 0.08-0.92 (6 steps, hysteresis ±0.02), RULE ◀ ▶, ORDER, ACROSS FAMILIES.
- **Sequence per step:**
  1. The current pair is **pushed** to its chance position (600ms `--ease-smooth`) while the ledger dims to 50%.
  2. Sizes re-size in place to the new rule's anchor and partner, at the new rule's chance overlap (600ms); the ghost moves with the partner's chance position.
  3. The new pair is **pulled** to its observed overlap (1200ms `--ease-smooth`; 800ms on a control).
  4. On landing: the ledger swaps (numerals 600ms), the bloom is redrawn.
- **A rule with lift < 1** settles **further out** than its ghost: the pull is a push. It never happens in the published set (min lift), but THE COUNTER's edges may include it (`edges[].lift`).
- **Interruption:** a new step mid-sequence retargets from the current interpolated state straight to step 3's target (skipping the push).
- **Reduced motion:** cut to the observed pair with the ghost visible.
- **Performance:** as 5.1.

### 5.5 Coming Back: the month scrub (S03b)

- **Trigger:** scroll steps p 0.04-0.96 (25 steps), MONTH ◀ ▶, COHORT, UNIT.
- **Month step:** the partner (active set) re-sizes and the overlap re-solves (1200ms on scroll, 800ms on a control, `--ease-smooth`). The anchor (the cohort) holds. The month strip's active tick moves (200ms).
- **Censored month:** the partner crossfades to hatch (600ms); the overlap fades out (600ms); the ledger reads `NOT YET OBSERVED`.
- **Cohort change:** both discs re-size together (800ms); the month holds if published for the new cohort, else clamps to its last month with a 200ms label flash of `MONTH {{m}} IS NOT PUBLISHED FOR THIS COHORT`.
- **Unit change:** 5.6's unit switch, here scene-local (`k` re-set: the scene's declared second k for revenue).
- **Reduced motion:** cuts.

### 5.6 Heads to Pounds: the unit switch (S04)

- **Trigger:** the stepped state at p 0.45, or UNIT.
- **Sequence:**
  1. The encoding label crossfades `AREA = CUSTOMERS` → `AREA = GBP` (200ms) **first**: the reader is told the unit changed before anything moves.
  2. Both discs and the overlap re-size in log space to the GBP sizes under the scene's second `k` (1200ms `--ease-smooth`). The overlap visibly swells relative to the discs.
  3. On landing, the ledger swaps (600ms numerals) and the bloom is redrawn.
- **Thresholds (R ≥, F ≥):** both discs and the overlap re-size (800ms). A threshold at 1 makes that set "all customers": the other disc is then contained (internally tangent).
- **Pair change (R x F → R x M):** crossfade 350ms (a different partner set).
- **Reduced motion:** cuts, label first.

### 5.7 The Stock Decision (S05)

- **Trigger:** stepped states (p 0.08, 0.30, 0.52, 0.74) and every control.
- **Motion:** the partner (the order `q`) re-sizes; the overlap (expected sales) re-solves; the anchor (expected demand) holds unless ITEM or MODEL changes (then it re-sizes too). 1200ms on scroll, 800ms on a slider release, **direct (no tween) while a slider is dragged** at frame rate, so the crescents track the thumb.
- **Crescent labels** (`SHORT {{shortage}}`, `LEFT OVER {{leftover}}`) sit outside the light at each crescent's far side and update only on release.
- **Interruption:** dragging always wins; a scroll step during a drag is ignored until release.
- **Reduced motion:** instant updates.
- **Performance:** the empirical quantile is a sort-once, index lookup; the normal uses a rational approximation of the inverse CDF (accuracy 1e-9, parity-tested). Both under 0.2ms.

### 5.8 What Will Sell (S06)

- **Forecast states** (p 0.06, 0.22, 0.38, 0.54): sizes re-size in place (1200ms). Model → seasonal-naive swaps only the partner. The **soft edge** appears at p 0.54 (its band grows from zero width to `[r(lo), r(hi)]` over 600ms) and disappears when leaving that state.
- **The recolour at entry** (from S05): the partner's ramp crossfades orange → periwinkle (800ms) while it re-sizes to the forecast total; the anchor crossfades to the actual total.
- **CLV states** (p 0.70, 0.86): crossfade (350ms) to the CLV pair (a new unit: purchases). DECILE re-sizes in place.
- **Reduced motion:** cuts; the soft edge is drawn statically.

### 5.9 Hatch, unknown and not estimable

- A disc whose size becomes unknown crossfades its light to hatch (600ms); its overlap fades out (600ms); a disc that becomes known lights from its far rim (600ms `--ease-premium`).
- S07 answer 6's not-estimable pair is two hatched discs, drawn once, apart, never animated toward each other.

### 5.10 Data transitions (keyed, everywhere)

| Change | Motion |
|---|---|
| Same sets, new sizes (months, thresholds, items, horizons) | Re-size in place (log space), `d` re-solved per frame |
| Same sizes, new shared (chance → observed) | The pull along the axis |
| Different sets, same unit and axis (rule to rule) | Push to chance, re-size, pull (5.4) |
| Different unit or axis | Crossfade 350ms |
| Text readouts | Numerals 600ms in a fixed `ch` box; words crossfade 200ms |
| Chips and tags | Crossfade 200ms; a tag never changes while its visual is in transit |

### 5.11 Argument stack (S07)

- 7 stepped exchanges, each: the objection card enters (translateY 24px → 0, opacity, 350ms `--ease-premium`), then 250ms later the answer card (offset +24, +16). Older cards recede by palette (to `#1f1f1f`) and scale 0.96 (350ms `ease-in-out`), never by opacity under 1 for text (ENGINEERING_DECISIONS #13).
- The stage pair holds at 15%, no motion.
- **Reduced motion:** a vertical list.

### 5.12 THE COUNTER

- Every control change runs the matching 5.4-5.8 transition at control speed (800ms); a change of KIND crossfades the pair (350ms).
- The inspector enters from the right (D, translateX 24px → 0, 350ms `--ease-premium`) or as a bottom sheet (T/M, spring, damping ratio 1.0).
- A product pair without an edge: both discs light apart; the hatch gap fades in (600ms).
- RESET: a 200ms white flash on the button only, then the hero pair returns (800ms).

### 5.13 Component microinteractions

| Component | Hover | Press | Focus | Active |
|---|---|---|---|---|
| Square buttons (◀ ▶, RETRY, RESET, CONTROLS) | bg `rgba(242,242,242,.1)` → white, text → black, 200ms `ease-in-out` | scale 0.98, 120ms | 2px white outline, 2px offset | white block |
| Segmented controls (ORDER, UNIT, MODEL, KIND) | as buttons | as buttons | as buttons | the active block slides (translateX/scaleX, 350ms `--ease-smooth`; ENGINEERING_DECISIONS #9) and is `#192CE4` fill with white text in THE COUNTER |
| Sliders | thumb grows 12 → 16px, 120ms | | outline on the thumb | value label above the thumb, tabular mono |
| Discs (stage) | the hovered disc's light rises 8% (200ms); its label goes to 100% | | 2px white outline on an invisible focus proxy over the disc's label, never on the disc | |
| Chips | none | | outline | |
| Tooltips | enter 200ms opacity + translateY 4px; 400ms delay on hover, none on focus | | | |

## 6. Navigation, chapter jumps, interruption

### 6.1 Nav

- D: the bottom bar, 13px mono uppercase items with 8px padding; the active item a white block with black text; hover bg to white over 200ms `ease-in-out` (reference).
- T/M: the MENU pill (160x32) shows the current section name (crossfade 200ms on change). Tap expands a blurred translucent list upward (clip-path reveal, 300ms, ENGINEERING_DECISIONS #9); the icon morphs from = to a dash-shaped bar (a CSS transform of two spans, no dash character).
- SKIP INTRO during S00; REPLAY INTRO afterwards.

### 6.2 Direct chapter jumps: instant, with a stage fade

- Click or Enter on a nav item: the stage fades to black (350ms), `scrollTo` the track start **instantly** (the reference jumps), the target scene's state is set to its p = 0 state without transitions, and the stage fades in (350ms). Total 700ms.
- `pushState` on jumps, `replaceState` from scroll position (ENGINEERING_DECISIONS #9): Back/Forward work.
- Focus moves to the target scene's heading.

### 6.3 Scroll interruption

- Reverse scroll replays stepped transitions backwards from their current interpolated state (retarget, not a rewind of the animation).
- Rapid scroll across many steps: only the final step's transition runs; intermediate steps are skipped (the hysteresis window collapses).
- Resize mid-scene: geometry re-measures, `k` and the camera recompute for the new viewport class, and the current state redraws without transition.

## 7. Operational state motion

| State | Motion |
|---|---|
| Initial | Nothing drawn on the canvas; headings sharp; set labels ghost |
| Loading | `LOADING {{ARTIFACT}} · {{pct}}%` updates as bytes arrive, linear, no easing; no fake progress |
| Ready | Discs light from their far rims (600ms `--ease-premium`), then the scene's first state transition |
| Error | Text line fades in (200ms) with RETRY; any drawn light from the previous state stays; no shake |
| Retry | RETRY presses, the line reads `RETRYING`, the real fetch re-runs; on success, Ready |
| Empty | Copy fades in (200ms); the pair fades to 0 (350ms) |
| Disabled | Instant `aria-disabled` + 50% white; tooltip on hover/focus |
| Reset | 200ms flash on RESET; transition to defaults at control speed |

## 8. Reduced motion

Under `prefers-reduced-motion: reduce` (and the in-page MOTION OFF toggle, persisted in `localStorage` in try/catch):

- Durations go to 0 through the tokens; Lenis is off; pinned tracks become normal flow (each scene one viewport, its states as stacked static frames listed in VISUAL_DESIGN section 4 per interaction).
- The intro shows its end state at once, **with the chance ghost visible** so the lift is still visible without the pull.
- Every control still works with instant updates.
- No word blur; no bloom fade (the bloom is drawn static).
- Never trapping: reduced motion has no pinned stage at all.

## 9. Performance budgets and rendering

### 9.1 Rendering decisions

- **Canvas2D only.** A pair is two filled circles, a clip and a textured fill: Canvas2D's `lighter` composite does the additive light natively (VISUAL_DESIGN reference 29). WebGL would add a context, shaders and a fallback for no gain. No three, no R3F, no deck.gl.
- **One stage canvas,** DPR capped at 2, sized to the viewport; **one bloom canvas** at 1/4 resolution, redrawn only on settle (CSS `filter: blur(18px)`, `mix-blend-mode: screen`, opacity 0.35).
- **The overlap field texture** (256x256, generated once at boot in an `OffscreenCanvas` where available, else a regular canvas).
- **DOM** for every word, label and control. Labels are positioned from the geometry each frame a transition is active (transform only).
- **No worker:** the heaviest computation is a newsvendor quantile (under 0.2ms) or a 25-cell RFM sum.

### 9.2 Budgets

| Item | Budget | How measured |
|---|---|---|
| Canvas draw per frame in transition (D, M1-class laptop) | ≤ 2ms (target; to be measured, not claimed) | Performance marks around `draw()`, median over a 10s scripted scroll |
| Main-thread work per scrubbed frame | ≤ 6ms | DevTools trace |
| Frame rate | ~60fps D, ≥ 30fps M (Moto G Power class throttle) | Evidence harness frame pacing |
| `solveD` per frame | ≤ 0.05ms (about 50 bisection steps) | Vitest bench |
| JS, gzip, initial | ≤ 110 KB (shell + S00/S01) | Build report |
| JS, gzip, total | ≤ 180 KB | Build report |
| Fonts | ≤ 60 KB (Latin subsets, ENGINEERING_DECISIONS #30) | Network panel |

### 9.3 Loading budget (Lighthouse perf 90+, LCP 2.5s or less, CLS 0.1 or less)

| Artifact | Loaded at | Note |
|---|---|---|
| `facts.json`, `meta.json` | First paint (preload) | DR-1 makes S00 need nothing else |
| `reconciliation.json` | S01 p 0.5 | S02 cards 1-3 |
| `baskets.json` | S02 p 0.5 | S03a, THE COUNTER |
| `cohorts.json`, `rfm.json` | S03a p 0.5 | S03b, S04 |
| `newsvendor_params.json`, `newsvendor_vectors.json`, `newsvendor_scenarios.json` | S04 p 0.5 | S05 (vectors used only by the parity test and the debug hook in dev; production loads them lazily for the guard check) |
| `backtest.json`, `forecast.json`, `clv.json` | S05 p 0.5 | S06 |
| `elasticity.json`, `validation.json` | S06 p 0.5 | S07 |
| `products.json`, `landscape.json`, `overview.json` | First inspector open, or THE COUNTER entry | Inspector details |
| Any artifact on a deep link | Immediately for the target scene | |

Each artifact is under 400 KB gzip by contract (`DATA_CONTRACTS.md`); the frontend logs `meta.artifact_bytes` against the measured transfer in the dev console.

## 10. Technical stack recommendation

- React + TypeScript strict + Vite + Tailwind (shared shell), Lenis, one rAF loop (ENGINEERING_DECISIONS #6; no GSAP: no timeline here needs it).
- `src/pair/geometry.ts`, `light.ts`, `transition.ts`, `draw.ts`: about 400 lines, no dependency (venn.js is a look and a dependency we do not need, VISUAL_DESIGN reference 7).
- `src/models/newsvendor.ts` (normal and empirical, parity against `newsvendor_vectors`), `src/models/rfm.ts` (threshold sums), `src/models/backtestAreas.ts` (DR-5 areas and WAPE identity).
- JSON Schema guards generated from `data/contracts` (types plus a runtime validator per artifact); a failed guard is the `FAILED ITS CHECKS` state.
- Self-hosted fonts (`@fontsource-variable/newsreader`, `@fontsource-variable/jetbrains-mono`), zero external requests (Playwright test).

## 11. Motion test plan

| # | Test | Tool |
|---|---|---|
| 1 | `lensArea(solveD(x)) = x` at 10,000 points; containment and disjoint edges | Vitest |
| 2 | Area rule at every rest state listed in section 2 (debug hook) | Playwright |
| 3 | S00: SKIP visible at 100ms; nav within 400ms of SKIP; LCP element `h1[data-hero]`; both cusps in frame at the end on D and M; anchor diameter ≥ 1.2 x height (D) | Playwright + Lighthouse |
| 4 | No value in transit: 10 sampled frames of a rule step and a month step show only old or new ledger numbers | Playwright |
| 5 | Never concentric: across a scripted pass of every scene, the debug hook's `d` is never below `|rA − rB| − 1e-9` and never 0 | Playwright |
| 6 | Sticky scenes release at the right point; reverse and rapid scroll; direct jumps land at p = 0 states; Back/Forward | Playwright |
| 7 | Resize mid-scene (D → M → D at S03b month 12) redraws the same state with the new `k` | Playwright |
| 8 | Reduced motion: no pinned stage; intro end state with the ghost; every control works | Playwright (emulated media) |
| 9 | Newsvendor parity: every `newsvendor_vectors` case within `tolerance_rel`; every `newsvendor_scenarios` grid point reproduces `q_normal`, `q_empirical` | Vitest |
| 10 | RFM sums equal `rfm.segments` totals; backtest areas satisfy the WAPE identity (DR-5) | Vitest |
| 11 | Slider drag on touch never scrolls the page; vertical swipe on the stage always scrolls | Playwright (touch) |
| 12 | Canvas frame counter flat for 2s at S07 after settle | Playwright |
| 13 | Frame pacing: ~60fps D, ≥ 30fps M through S00 and S03a | Evidence harness |
| 14 | Operational states: forced 404 shows the error and RETRY re-fetches; schema-guard failure shows `FAILED ITS CHECKS`; empty filter shows its copy | Playwright (route interception) |
| 15 | **Distinctness on real frames:** the QA contact sheet places P09 S00 end and S08 p 0.75 beside real P01-P08 S00 frames, in colour and greyscale; the reviewer confirms the overlap reads as a flat almond, not a lit sphere (VISUAL_DESIGN section 2) | Evidence harness + independent QA |
| 16 | Zero external requests; no U+2014/U+2015 in the built HTML/JS | Playwright, grep |

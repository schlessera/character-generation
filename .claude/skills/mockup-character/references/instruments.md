# Instruments: `just compare NAME [flags]` and friends

`compare` snaps the mockup to its pixel grid, places each view over the render, scores it and
writes `build/preview/NAME_compare.png` (rows: mockup, render, head close-ups, heat maps). The
score is symmetric: every opaque pixel of either image looks for a same-colour pixel within one
pixel in the other; a missing or clearly different one costs 1. `mean` over the five views is the
number in the notes. The printed **loss table** splits it per body part (render side / mockup
side).

| flag | prints | read it for |
|---|---|---|
| `--text VIEW…` / `all` | mockup \| render, every pixel as a palette letter (`H` hair base, `H-` shade, `H=` deep, `H#` ink, `##` outline, `??` no colour close) | drawing grids; finding structure that is off; the first thing to look at for any complaint |
| `--fit` | per render colour: pixel count, median mockup colour under it, distance | palette moves for large flat areas |
| `--fit-part CODES` | the same restricted to label codes (`T` torso, `Rr` cyber-arm, `PQpq` legs+feet, `H.` head) with mean cost | which colours on a part are misplaced |
| `--optimize` | bounded coordinate descent over ramp slots, moves with gains, applies nothing | end of a phase; accept moves with a reading |
| `--ceiling` | the mockup quantized to the recipe's palette, scored against itself | the target; ~0.92 for a 30-colour palette |
| `--slack` | per view and part: loss now / loss at the ceiling | where there is still room |
| `--split` | silhouette match (one-pixel drift allowed) and colour loss per view | whether shape work is done (0.99+) |
| `--widths` | per row: mockup vs render extents and the difference per side, labels at the edges | where to grow (≥2 only) |
| `--digits VIEW…` | the cost maps as digits 0–9 per pixel, mockup side \| render side | hot spots, read against `--text` |
| `--shift` | best whole-grid offset per head grid with its gain | hair volume direction |
| `--fit-grid VIEW… [--chars …]` | the head grid traced cell by cell to the mockup, only changes that gain | a diagnostic; look at the cells before applying |
| `--recipe PATH` | score a variant file instead of the character's recipe | every experiment |

Other commands:

- `just heads NAME` — each facing's head template rows beside its grid, for alignment.
- `just crops NAME --box y0,y1 [--recipe v.toml …]` — the eight idle facings cropped to frame rows
  y0..y1 at 16×, one row per recipe (`17,31` torso, `24,32` feet, `4,20` head). The fastest way to
  judge a trim change from every angle at once.
- `just preview NAME [anims…]` — contact sheet of every animation × facing, plus 12× idle facings
  (`build/preview/NAME_facings.png`); crop and zoom the sheet to review, it is tall.
- `just smoke` — builds the sheets and drives the playground headless.
- `just media` — every README figure from source, including the iteration figure and similarity
  chart from `history/step-*.toml`.

Reading the heat-map rows in `NAME_compare.png`: dim = matched, red = unmatched; too small to
read at the sheet's scale, use `--digits` instead.

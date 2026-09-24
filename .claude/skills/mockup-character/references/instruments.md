# Instruments: `just compare NAME [flags]` and friends

`compare` snaps the mockup to its pixel grid, places each view over the render, scores it and
writes `build/preview/NAME_compare.png` (rows: mockup, render, head close-ups, heat maps). The
views are matched to facings by their count: five (down, down_side, side, up_side, up) or eight
(the turn-around: down, down_side, side, up_side, up, up_side_l, side_l, down_side_l); any other
count is an extraction problem (a figure split by a light row) and an error. The
score is symmetric: every opaque pixel of either image looks for a same-colour pixel within one
pixel in the other; a missing or clearly different one costs 1. `mean` over the five views is the
number in the notes. The printed **loss table** splits it per body part (render side / mockup
side).

Geometry: frames are 32×32 (rows and columns 0..31); head grids are the head template padded by
3 on every side. Palette letters are assigned **per recipe**: a colour the head legend references prints as that
legend character (`k` hair outline, `b` hair, `u` stubble, `v` lens, `o` outline…), so the text
view reads like a grid; every other colour is ramp initial + slot mark (`J` base, `J-` shade, `J+`
light, `J=` deep, `J#` ink). The `legend:` line printed with `--text`, `--fit` and `--fit-part`
says what they mean for this recipe. All flags combine; `--quiet` drops the loss table.

| flag | prints | read it for |
|---|---|---|
| `--draft-grid VIEW…` / `all` | a head grid drafted from the mockup: nearest legend colour per cell on the head, `.` elsewhere; `--chars` limits the candidates. For a `VIEW_l`: the right twin mirrored about the template width, `--mirror-swap` exchanges mane and shaved side | phase 2; paste, clean, score |
| `--hex VIEW y0,y1,x0,x1` | raw mockup hex per pixel for a box of frame coordinates | palette reads where the letters blur (dark ramps a few RGB steps apart) |
| `--text VIEW…` / `all` | mockup \| render, every pixel as a palette letter (`H` hair base, `H-` shade, `H=` deep, `H#` ink, `##` outline, `??` no colour close) | drawing grids; finding structure that is off; the first thing to look at for any complaint |
| `--fit` | per render colour: pixel count, median mockup colour under it, distance, spread (`~` = wide: the median is not a colour the mockup uses much) | palette moves for large flat areas, **after** the grids exist |
| `--fit-part CODES` | the same restricted to label codes (`T` torso, `Rr` cyber-arm, `PQpq` legs+feet, `H.` head) with mean cost | which colours on a part are misplaced |
| `--optimize [--min-gain 0.0004]` | bounded coordinate descent over ramp slots, moves with gains, applies nothing (the default threshold 0.0015 is coarse; a finer one finds more, and lifts the ceiling too) | end of a phase; accept moves with a reading |
| `--ceiling` | the mockup quantized to the recipe's palette, scored against itself | the target; ~0.92 for a 30-colour palette |
| `--slack` | per view and part: loss now / loss at the ceiling | where there is still room |
| `--split` | silhouette match (one-pixel drift allowed) and colour loss per view | whether shape work is done (0.99+) |
| `--widths` | per row: mockup vs render extents and the difference per side, labels at the edges | where to grow (≥2 only) |
| `--digits VIEW…` | the cost maps as digits 0–9 per pixel, mockup side \| render side | hot spots, read against `--text` |
| `--shift [--chars kbHDi]` | best one-pixel offset per head grid (of the given cells only) with its gain | hair volume direction; act by adding hair, not by shifting |
| `--fit-grid VIEW… [--chars …]` | the head grid traced cell by cell to the mockup, only changes that gain | a diagnostic; look at the cells before applying |
| `--recipe PATH` | score a variant file instead of the character's recipe | every experiment |
| `--oracle` | per part, the gain from copying the mockup's quantized pixels over the render | where the gap lives; the most any rule set could add |
| `--sweep N [--sweep-parts P,P]` | forward search: ~1,400 simple rule shapes (rows, band, stripe, region, grow, shrink on every part in every ramp) each scored across all views, the N best with the mean gain, the gain if limited to the views where it helps, and those facings; ~12 s | after the design's own rules: what a per-facing trim is still worth; every pick goes through `crops --diff` and `--hex` before it stays |
| `--ablate` | score gain from removing each rule, sorted | candidates for details the mockup lacks; confirm with `--hex` |
| `--goal PCT` | the ceiling, the threshold PCT percent below it, and whether the mean reaches it | the definition of done |
| `--hot N` | the N costliest pixels: view, row, col, mockup letter, render letter, cost | a "nothing big is left" check: scattered singles at cost ~1 mean done |
| `--init-palette` | median mockup colour per template tone for each line of the recipe's own `[parts]` (body only; the head needs grids); `~` marks two populations | a new design's palette, after `[parts]` names its parts and before the grids |
| `--draft-grid … --all-slots` | the draft may also pick every palette slot the legend does not reference and is not within a few RGB steps of a legend colour; a body ramp can land inside the hair when it is the nearest colour, which couples the grid to that ramp (a colorway swapping it recolours the strands): give the hair its own slot for that colour if that matters (a coat collar in the head's last rows, skin light, trim); with `--apply` the new letters are appended to `[head.legend]`. The ceiling quantizes to every slot, so a short legend is a built-in gap | step 1, on any design whose legend was written before the mockup was read |
| `--draft-grid … --clean --apply` | `--clean`: rim chars off the non-lens rows, then lone speckles and the hair-only last row — each of those two kept per view only where it does not lower the score (the print says what it skipped); `--apply`: write into the recipe, in two passes (the placement moves once the head is covered) | step 1 in one command |

Other commands:

- `just lint NAME` — parts order, unknown ramps, one-sided rules with mirrored facings, tone-relative
  legend entries, missing left grids, grid cells on the body, unused characters.
- `just turntable NAME [anims…]` — a GIF of the character turning through the eight facings (idle
  by default) → `build/preview/NAME_turntable.gif`.
- `just review NAME` — one image, every cell labelled with its facing: eight facings at 12×, the
  heads at 24× (look here first), torso and feet crops at 16×, the turn-around and walk/run/jump/
  attack in the angled views at 6× → `build/preview/NAME_review.png`.
- `just step NAME "message" [--goal PCT] [--snapshot] [--amend]` — score, append the NOTES row (or
  replace the last one — message and all — with `--amend`), snapshot every fifth step; with `--goal`, the ceiling and
  the threshold.
- `just selftest` — every command and flag on a scratch copy; run it after touching `chargen/`.
- `just heads NAME` — each facing's head template rows beside its grid, with the grid↔frame
  column and row offsets in the header.
- `just crops NAME --box y0,y1 [--recipe v.toml …] [--diff]` — the eight idle facings cropped to
  frame rows y0..y1 at 16×; the current recipe is always the first row, one more row per
  `--recipe` variant (`17,31` torso, `24,32` feet, `4,20` head); `--diff` outlines every pixel a
  variant changes. The fastest way to judge a trim change from every angle.
- `just preview NAME [anims…]` — contact sheet of every animation × facing (`build/preview/NAME.png`,
  or `NAME_walk_run.png` when animations are given), plus 12× idle facings
  (`build/preview/NAME_facings.png`); crop and zoom the sheet to review, it is tall.
- `just smoke` — builds the sheets and drives the playground headless.
- `just media` — every README figure from source, including the iteration figure and similarity
  chart from `history/step-*.toml`.

Reading the heat-map rows in `NAME_compare.png`: dim = matched, red = unmatched; too small to
read at the sheet's scale, use `--digits` instead.

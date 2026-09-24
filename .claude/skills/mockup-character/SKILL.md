---
name: mockup-character
description: Turn a character's concept art and pixel mockup into a finished recipe for this repo's semantic sprite skinning generator (characters/NAME/recipe.toml), then iterate it against the mockup with `just compare` until it matches as closely as the rule system allows (0.90 similarity is reachable; the palette ceiling is about 0.92). Use this whenever the user adds a new character, has a mockup or concept image to turn into a sprite, wants to "iterate on" or "improve" a character against its mockup, asks to raise the similarity score, or reports a visual problem with a character's hair, visor, collar, jacket, sleeves, shoes or turn-around — even if they don't say "recipe" or "mockup". It encodes everything learned in 110 iteration steps on Juno: the order of work that pays, the instruments to read, the rule patterns per facing, and the mistakes not to repeat.
---

# Character from a pixel mockup

A character here is a recipe: colour ramps per body part, geometric trim rules keyed to body-part
labels, and per-facing head grids, skinned onto every frame of the labelled template. The mockup
(five views: down, down_side, side, up_side, up, stacked vertically) is the reference; `just compare
NAME` snaps it to its pixel grid and scores it against the render. This skill is the shortest known
path from mockup to a recipe that scores about 0.90 and looks right from all eight angles.

Read `references/playbook.md` for the phases in detail (rule snippets per facing), `references/
instruments.md` for what each `compare` flag shows, `references/pitfalls.md` before touching grids,
`[parts]` or `grow`. The worked example is `characters/juno/recipe.toml`; its full log is
`characters/juno/history/NOTES.md`, and README chapter 5 tells the story with numbers.

## What makes this fast

Juno took 110 steps because the instruments were built along the way and several problems were only
found by a human watching. Three things cut that down:

1. **Order.** Palette and outline first (three steps gave +0.06), head grids from the text view
   second (+0.02), trim semantics third, silhouette last. Doing grids before the palette wastes
   effort: you redraw them once the colours settle.
2. **Read text, not just pictures.** `compare --text VIEW` prints mockup | render as palette letters.
   Every grid in Juno's final recipe was drawn from that view, row by row, and both real semantic
   bugs (a jacket-coloured neck, a shading rule overpainting the collar) were only visible there.
3. **Know the ceiling and where the room is.** `--ceiling` gives the palette's maximum;
   `--slack` says which body part still has room; `--split` confirms whether the silhouette is done.
   Without these the loop chases noise. Silhouettes match at 0.99+ once the grow rules are in; the
   remaining gap is colour placement, and most of it is the mockup's 300-colour noise.

## Workflow

Work in a branch. Log every step in `characters/NAME/history/NOTES.md` (one row: step, change,
similarity) and snapshot the recipe every five steps as `history/step-NN.toml` — the README figures
are built from those. Commit per phase. Every five steps render `just preview NAME` and look at
every animation; every phase run `just smoke`.

### Phase 0 — set up (1 step)

- `characters/NAME/concept/NAME-pixel-mockup.png` (the five views, on a plain background) and
  `NAME-concept.png`. `chargen/mockup.py` measures the pixel pitch itself.
- Copy `assets/recipe-skeleton.toml` to `characters/NAME/recipe.toml`. It has the structure that
  survived: `[parts]` in the right order, grow rules first, the collar per facing, the zipper per
  facing, the hem before the zipper, sleeves, shoes, head legend, empty grids.
- `just compare NAME` renders and scores. Expect about 0.6 with placeholder colours.

### Phase 1 — palette and outline (3–4 steps, the biggest gain)

- `just compare NAME --fit` prints the median mockup colour under every render colour. Apply the
  medians for every ramp slot with a plausible reading (skin, hair, jacket, pants, shoes, chrome,
  trim). Sample the outline colour too: mockups from image generation use a warm dark brown
  (`#241a17` for Juno), not near-black, and the outline is the largest single colour by pixel count.
- Then `--optimize` (bounded coordinate descent, prints moves, applies nothing). Take a move only
  when it has a semantic reading; see pitfalls for the one that was refused twice and then accepted.
- Run `--ceiling` now and write it in the notes: that is the number to measure progress against.

### Phase 2 — head grids from the text view (4–6 steps)

One grid per facing in the mockup (down, down_side, side, up_side, up), each drawn from
`--text VIEW`, then the three left-facing grids by hand for the mane side. The playbook has the
column-offset derivation (it differs per facing, and getting it wrong shifts the whole head).
Decide the visor row per angle up front: front view keeps a brow row above the rim; 3/4 and
profile sit at eye level. Lens ends are the frame's dark caps, no glint. Then `--shift` once: a
consistent direction across views means the hair wants more volume on that side.

### Phase 3 — trim semantics per facing (4–6 steps)

The rules in the skeleton are the Juno answers; keep what fits the design and check every facing
with `just crops NAME --box 17,31` (torso) and `--box 24,32` (feet), one row per `--recipe`
variant. Test any change as a variant file first (`compare NAME --recipe tmp.toml`), never in place.
The things that were wrong at first and are worth checking on any character:

- collar: a straight row (an edge against the neck follows the neck's U); front = torso top row,
  from behind = the whole neck, profile = the neck's back columns;
- zipper: front ±1 with the shirt between; 3/4 offsets 0/1/2 toward the facing side with `ink =
  true` (the far edge sits on the template's ink column); profile on the front edge column;
- hem before the zipper rules (an open jacket's hem is split by the opening);
- flank shade with `region` before the trim; cuffs a shade darker than the hem; sneakers grown one
  pixel each side (front/back), toward the toes in 3/4, not in profile; long sleeves cover all
  but the fingertips.

### Phase 4 — silhouette where the mockup is ≥2 wider (2–4 steps)

`--widths` per view. Differences of 1 are free (the metric tolerates one pixel); grow only where
the mockup is 2 or more wider, with a reason: the far sleeve and shoulder beside the torso in 3/4,
the far arm's shoulder cap from 3/4 behind, the near arm one column out with a shadow seam. A
general "bulk" grow overshoots and loses. Check `--split`: silhouettes should read 0.99+.

### Phase 5 — the last thousandths (2–3 steps)

`--slack` names the parts with room; `--fit-part CODES` (e.g. `T`, `Rr`) shows which colours on
that part sit where the mockup has something else; `--digits VIEW` shows the pixels. `--fit-grid`
is a diagnostic: if it finds nothing, the grids are done; if it finds much, look at the cells
before applying — unrestricted it paints junk. Finish with `--optimize` at a finer threshold via
`optimize_palette(..., radius=20, step=4, min_gain=0.0004)`.

### Done when

The score is within about 0.02 of `--ceiling`, `--split` shows silhouettes at 0.99+, and the
turn-around (`just preview NAME rotate`) reads as one character from eight sides. Then `just media`
and update README/notes. Human complaints outrank the score: a bent collar, a low visor or small
shoes cost nothing on the metric and were the most visible faults.

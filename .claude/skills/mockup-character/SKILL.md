---
name: mockup-character
description: Turn a character's concept art and pixel mockup into a finished recipe for this repo's semantic sprite skinning generator (characters/NAME/recipe.toml), then iterate it against the mockup with `just compare` until it matches as closely as the rule system allows (0.90 similarity in one to five steps; the goal is a percentage below the measured palette ceiling). Use this whenever the user adds a new character, has a mockup or concept image to turn into a sprite, wants to "iterate on" or "improve" a character against its mockup, asks to raise the similarity score, or reports a visual problem with a character's hair, visor, collar, jacket, sleeves, shoes or turn-around — even if they don't say "recipe" or "mockup". It encodes what 110 iteration steps on Juno and four replays by fresh agents taught (the last one probed how far the rule system can go at all): the order of work that pays, the instruments to read, the rule patterns per facing, and the mistakes not to repeat.
---

# Character from a pixel mockup

A character here is a recipe: colour ramps per body part, geometric trim rules keyed to body-part
labels, and per-facing head grids, skinned onto every frame of the labelled template. The mockup
(five views: down, down_side, side, up_side, up, stacked vertically) is the reference; `just compare
NAME` snaps it to its pixel grid and scores it against the render. Measured path: the skeleton
recipe plus one `--draft-grid all` command reaches 0.90; a review pass, a trim check from all
eight angles and the last thousandths take three to five steps more.

Read `references/playbook.md` for the phases in detail (rule snippets per facing, the near-side
table for the left-facing grids), `references/instruments.md` for what each `compare` flag shows,
`references/pitfalls.md` before touching grids, `[parts]`, grow rules or a fit table. The skeleton
and these references are self-contained; do not start from another character's finished recipe,
the skeleton is the distilled version of it.

## What makes this fast

1. **The skeleton already contains the rule set** (`assets/recipe-skeleton.toml`): collar per
   facing, zipper per facing, hem before zipper, sleeves and fingertips, sneakers, cyber-arm,
   the 3/4 silhouette grows, `fx` mapped. Its palette is Juno's. On a design like hers most of
   phase 3 and 4 is verification; on a different design, delete what the design lacks and refit
   the colours — the structure still applies.
2. **Head grids are drafted, not drawn.** `just compare NAME --draft-grid VIEW` quantizes the
   mockup's head to the legend's colours at every grid cell and prints a ready grid; each view
   went from ~0.6 to ~0.9 on its first paste in both replays. `--draft-grid VIEW_l
   [--mirror-swap]` drafts a left-facing grid from its twin. Hand transcription from the text
   view — Juno's method — is where the time went.
3. **Read text, not just pictures.** `--text VIEW` (palette letters), `--hex VIEW y0,y1,x0,x1`
   (raw colours), `--digits`, `--widths`: the structural mistakes (a jacket-coloured neck, a
   shading rule overpainting the collar, an arm flush against the torso) were only visible there.
4. **Know the ceiling and where the room is.** `--ceiling` moves when ramps are added, so run it
   at the end too; `--slack` names the part with room; `--split` says whether the silhouette is
   done (0.99+ means it is). Without these the loop chases the mockup's noise.

## Workflow

Work in a branch. `just step NAME "what changed" --goal 4` after every change: it scores, appends
the row to `history/NOTES.md` (four decimals), snapshots every fifth step, and reports the goal.
The goal is not a fixed number: it is a distance below the palette ceiling (the mockup quantized
to the recipe's palette, scored against itself — the most this palette could express). Palette
moves lift the ceiling as much as the score, so only structure closes the gap; that is the
point of measuring it this way. What the percentages mean, measured: **4%** is one command
(the drafted grids); **3%** is a reviewed, finished character; **2.4%** is the most anyone has
reached with rules that hold in every frame (run 4, ten steps); **1%** is where a despeckled
pixel copy of the mockup's own body lands — reachable only by tracing the body, which breaks
the other 243 frames. Set 4 for done, 3 for polish; do not chase lower. `just review NAME` after every
visible change: one image with the eight facings at 12×, torso and feet crops, the turn-around
and the angled animations. `just lint NAME` before any scoring. Commit per phase; `just smoke`
at the end. Human complaints outrank the score: a bent collar, a low visor, small shoes and a
jacket that looked broken from 3/4 cost nothing on the metric and were the most visible faults.

### Step 0 — set up and lint

- `characters/NAME/concept/NAME-pixel-mockup.png` (five views on a plain background) and
  `NAME-concept.png`. Copy `assets/recipe-skeleton.toml` to `characters/NAME/recipe.toml`, set
  `name`. `just lint NAME` (parts order, one-sided rules with mirrored facings, legend, grids).
  `just step NAME "skeleton" --goal 4` → about 0.64 and the ceiling.
- Palette check: `just compare NAME --init-palette --quiet` gives the median mockup colour per
  body part and template tone (reliable before grids exist for the body; the head is not). Compare
  with the skeleton's ramps; refit the ramps that differ (large flat areas; a `~` means two
  populations, look with `--hex VIEW y0,y1,x0,x1`). On a design like Juno's nothing changes.

### Step 1 — all head grids in one command

`just compare NAME --draft-grid all --clean --apply --mirror-swap --quiet`: the five mockup views
are drafted (nearest legend colour per cell on the head), cleaned (visor characters off the rim
and lens rows, lone speckles, the row below the jaw keeps hair only) and written into the recipe
— twice, because the mockup's placement over the render moves once the head is covered and the
second pass aligns to the final one (+0.003 on the replay); the three left-facing views come
from their twins (the 3/4 mirrored with a far-edge strip of shaved side, the profile mirrored
all mane, the 3/4-back unmirrored since her right is screen-right in both; drop `--mirror-swap`
for a symmetric cut). Score: ~0.905 on the replay.
Then `just review NAME` and look, first at the heads row (24×): the three left views are drafts
of a different kind (a mirror with the mane put back on her own side) and are where the
non-metric risk lives — a character facing screen-right shows the camera her *right* side, so the
left-facing views show her left; the playbook's table says what each must show. Fix what you see
by editing the grid rows; `just heads NAME` shows the template alignment. The visor row per angle
comes out of the draft: check, do not move.

### Step 2 — trim and silhouette check (1–3 steps)

The skeleton's rules are the Juno answers; `just crops NAME --box 17,31 --diff --recipe
variant.toml` shows every changed pixel from all eight angles when you try one. Check the collar
(straight rows), zipper offsets per facing, the split hem, cuffs, fingertips, the flank region.
`--widths` per view: grow only where the mockup is 2+ wider, with a name; `--split` should show
silhouettes at 0.99+. One-sided features must not carry `_l` twins (lint says so).

### Step 3 — the last thousandths (0–2 steps)

`--oracle` first: it copies the mockup's pixels over the render per part and reports the gain —
where the remaining gap lives and the most any rule could add (torso+arms on Juno's mockup,
the head is done). Then `--slack`, `--fit-part CODES`, and rule ablation: drop a skeleton rule
in a variant and score; a rule that scores better removed is a Juno detail this mockup lacks —
confirm with `--hex` before deleting. `--fit`/`--optimize` last; they lift the ceiling too. `--hot 20` lists the costliest pixels: scattered
single pixels at cost ~1 mean nothing big is left. `--fit-grid` is a diagnostic; if it finds
nothing, or only speckles, the grids are done. A fix to an unscored view (a left grid) can go on
the previous row with `just step ... --amend`.

### Done when

`just step ... --goal 4` says REACHED, `--split` shows silhouettes at 0.99+, `just lint` is
clean, and `just review NAME` shows nothing a person would complain about from any of the eight
sides or in the attack, jump and run. Then `just smoke`, `just media`, and update README/notes.

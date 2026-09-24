---
name: mockup-character
description: Turn a character's concept art and pixel mockup into a finished recipe for this repo's semantic sprite skinning generator (characters/NAME/recipe.toml), then iterate it against the mockup with `just compare` until it matches as closely as the rule system allows (the goal is a percentage below the measured palette ceiling; a design like the ones done before reaches it in six to eighteen steps). Use this whenever the user adds a new character, has a mockup or concept image to turn into a sprite, wants to "iterate on" or "improve" a character against its mockup, asks to raise the similarity score, or reports a visual problem with a character's hair, eyewear, mask, collar, coat, jacket, sleeves, shoes, cyber-limb or turn-around — even if they don't say "recipe" or "mockup". It encodes what 110 iteration steps on Juno, five replays on her mockup and one build of a second character (Nyx: symmetric hair, goggles and a mask, a long coat, a cyber-leg, boots, eight mockup views) taught: the order of work that pays, the instruments to read, the rule patterns per garment feature, and the mistakes not to repeat.
---

# Character from a pixel mockup

A character here is a recipe: colour ramps per body part, geometric trim rules keyed to body-part
labels, and per-facing head grids, skinned onto every frame of the labelled template. The mockup
is the reference: five views stacked vertically (down, down_side, side, up_side, up), or eight in
the turn-around's order (down, down_side, side, up_side, up, up_side_l, side_l, down_side_l).
`just compare NAME` counts the views, snaps them to their pixel grid and scores each against its
facing's render. With eight views the three left-facing views are scored and drafted from the
mockup like the others; nothing is mirrored and `--mirror-swap` does nothing.

Read `references/playbook.md` for the phases in detail, `references/rule-library.md` for every
rule that held on the two finished characters, grouped by garment feature, `references/instruments.md`
for what each `compare` flag shows, `references/pitfalls.md` before touching grids, `[parts]`,
grow or shrink rules or a fit table. The skeleton (`assets/recipe-skeleton.toml`) is the structure
of a recipe with no design in it; do not start from another character's finished recipe.

## What makes this fast

1. **The structure is given, the design is not.** The skeleton has the palette in the shape of a
   real one, the parts, the outline, the head classes and legend, and no rules. Refit every ramp
   from the mockup, map the parts the design has (a one-sided limb is a `[parts]` line: labels
   follow the mirror), then add rules feature by feature from the library. Measured: with no
   body rules the drafted heads alone give 0.84 on a coat-and-boots design; the rules for the
   coat, sleeves, boots and shin took it to 0.90 in eleven more steps.
2. **Head grids are drafted, not drawn.** `just compare NAME --draft-grid all --all-slots --clean
   --apply` quantizes each mockup view's head to the palette (every slot, adding legend letters
   for the ones the legend lacks: a collar, a mask, a tee reach into the head's rows), cleans
   what cleaning does not cost, and writes the grids twice (the placement moves once the head is
   covered). One command: ~0.6 → ~0.84–0.91 depending on how much of the design is body.
3. **Read text, not just pictures.** `--text VIEW` (palette letters), `--hex VIEW y0,y1,x0,x1`
   (raw colours), `--digits`, `--widths`: structural mistakes (a jacket-coloured neck, a shading
   rule overpainting the collar, a stripe one column off) are only visible there.
4. **Score per view, then judge on crops.** One variant scored across all views gives per-facing
   answers in one call: a rule that gains in three views and loses in two wants `facings`.
   `--sweep` does this for ~1,400 simple rule shapes at once; `--ablate` for each rule you have.
   Every pick then goes through `just crops --diff` and `--hex`: the score rewards dithering and
   punished a corner outline that the picture needed.
5. **Know the ceiling and where the room is.** `--ceiling` moves when ramps are added, so run it
   at the end too; `--slack` names the part with room; `--split` says whether the silhouette is
   done (0.99+ means it is); `--oracle` says the most any rule could add per part.

## Workflow

Work in a branch. `just step NAME "what changed" --goal 3` after every change: it scores, appends
the row to `history/NOTES.md`, snapshots every fifth step, and reports the goal. The goal is not
a fixed number: it is a distance below the palette ceiling (the mockup quantized to the recipe's
palette, scored against itself). Palette moves lift the ceiling as much as the score, so only
structure closes the gap. Measured: **3%** took one command on Juno's mockup and 14 steps on Nyx's;
**2.4%** is the most anyone reached with rules that hold in every frame; **1%** is where a pixel
copy of the mockup's own body lands, reachable only by tracing, which breaks the other frames.
Leave 0.001 of margin over the line: a generator fix took a +0.0001 pass back. `just review NAME`
after every visible change; `just lint NAME` before any scoring; commit per phase; `just smoke` at
the end. Human complaints outrank the score.

### Step 0 — set up, palette, parts

- `characters/NAME/concept/NAME-pixel-mockup.png` and `NAME-concept.png`. Copy the skeleton to
  `characters/NAME/recipe.toml`, set `name`. `just step NAME "skeleton" --goal 3`: the number is
  the palette's distance from the design (0.64 on a palette that fits, 0.41 on one that does not).
- Palette: `--hex` over a whole view (`--hex down 4,32,7,25` covers the whole figure in any
  view; front, back and profile give every slot in three calls; the box is end-exclusive), then `--init-palette` once `[parts]` names this design's parts — on a
  trimmed design it prints `~` on every row and is no help; on a one-material part it is. Every
  slot refit; ramps the design lacks deleted; materials it has added. Parts: groups first, specific
  parts after; a one-sided limb as a part line.
- `just lint NAME`.

### Step 1 — all head grids in one command

`just compare NAME --draft-grid all --all-slots --clean --apply --quiet` (`--mirror-swap` only
for a five-view mockup of a one-sided haircut), then `just compare NAME --fit-grid all --apply
--quiet` (two minutes, the views in parallel): the draft leaves `.` cells inside the head where
the mockup's head is a pixel off (the template's bald skin shows through) and the trace fills
them, +0.003 mean on both runs that measured it. Then `just review NAME`: the heads row at 24×.
Fix what you see by editing grid rows; `just heads NAME` shows the template alignment. `just
step` says when a view's placement moved (after a grow, a shrink, a new head): re-draft THAT
view then (`--draft-grid VIEW --all-slots --clean --apply`), not all — the others come back
equal or worse, and a re-draft left for later cost run 2 seven steps of a +0.007 it had earned
at step 5.

### Step 2 — silhouette and the garment, feature by feature (3–10 steps)

`--widths` per view; grow or shrink only for 2+, each with a name, in both 3/4 views when the
feature is symmetric. Then one feature at a time from the rule library (collar, opening, hem,
sleeves, shoes, limb details), each as a variant scored across the views (`--recipe`), each
kept where it has a reading and looks right on `just crops NAME --box 17,31 --diff`. `--split`
should show silhouettes at 0.99+ when this is done.

### Step 3 — the last thousandths (1–4 steps)

`--oracle` (where the gap lives), `--slack`, `--sweep 20` (forward search; every pick confirmed
on crops and `--hex`), `--ablate` (a rule that scores better removed is a detail this mockup
lacks; confirm before deleting), `--optimize --min-gain 0.0004` last (moves with a reading only).
`--hot 20`: scattered singles at cost ~1 mean nothing big is left.

### Done when

`just step ... --goal 3` says REACHED with margin, `--split` shows silhouettes at 0.99+, `just
lint` is clean, and `just review NAME` shows nothing a person would complain about from any of
the eight sides or in the attack, jump and run (a rule may take `anims` to stay out of the
attack's spin). Then `just smoke`, `just turntable NAME`, `just media`, and update README/notes.

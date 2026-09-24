---
name: mockup-character
description: Turn a character's concept art and pixel mockup into a finished recipe for this repo's semantic sprite skinning generator (characters/NAME/recipe.toml), then iterate it against the mockup with `just compare` until it matches as closely as the rule system allows (0.90 similarity in about a dozen steps; the palette ceiling is 0.91–0.94). Use this whenever the user adds a new character, has a mockup or concept image to turn into a sprite, wants to "iterate on" or "improve" a character against its mockup, asks to raise the similarity score, or reports a visual problem with a character's hair, visor, collar, jacket, sleeves, shoes or turn-around — even if they don't say "recipe" or "mockup". It encodes what 110 iteration steps on Juno and a 12-step replay by a fresh agent taught: the order of work that pays, the instruments to read, the rule patterns per facing, and the mistakes not to repeat.
---

# Character from a pixel mockup

A character here is a recipe: colour ramps per body part, geometric trim rules keyed to body-part
labels, and per-facing head grids, skinned onto every frame of the labelled template. The mockup
(five views: down, down_side, side, up_side, up, stacked vertically) is the reference; `just compare
NAME` snaps it to its pixel grid and scores it against the render. Measured path: the skeleton
recipe plus five drafted head grids reaches 0.90 in about eight steps; the rest is checking that
it looks right from all eight angles and in every animation.

Read `references/playbook.md` for the phases in detail (rule snippets per facing, the near-side
table for the left-facing grids), `references/instruments.md` for what each `compare` flag shows,
`references/pitfalls.md` before touching grids, `[parts]`, grow rules or a fit table. The worked
example is `characters/juno/recipe.toml`; its log is `characters/juno/history/NOTES.md`, and
`characters/replica/history/AGENT-LOG.md` is a fresh agent's account of using this skill.

## What makes this fast

1. **The skeleton already contains the rule set** (`assets/recipe-skeleton.toml`): collar per
   facing, zipper per facing, hem before zipper, sleeves and fingertips, sneakers, cyber-arm,
   the 3/4 silhouette grows, `fx` mapped. Its palette is Juno's. On a design like hers most of
   phase 3 and 4 is verification; on a different design, delete what the design lacks and refit
   the colours — the structure still applies.
2. **Head grids are drafted, not drawn.** `just compare NAME --draft-grid VIEW` quantizes the
   mockup's head to the legend's colours at every grid cell and prints a ready grid. Each view
   went from ~0.6 to ~0.9 on its first draft in the replay. Hand transcription from the text
   view — Juno's method — is where the time went.
3. **Read text, not just pictures.** `--text VIEW` (palette letters), `--hex VIEW y0,y1,x0,x1`
   (raw colours), `--digits`, `--widths`: the structural mistakes (a jacket-coloured neck, a
   shading rule overpainting the collar, an arm flush against the torso) were only visible there.
4. **Know the ceiling and where the room is.** `--ceiling` moves when ramps are added, so run it
   at the end too; `--slack` names the part with room; `--split` says whether the silhouette is
   done (0.99+ means it is). Without these the loop chases the mockup's noise.

## Workflow

Work in a branch. Log every step in `characters/NAME/history/NOTES.md` (step, change, similarity
to four decimals — `compare` prints four) and snapshot the recipe every five steps as
`history/step-NN.toml`; the README figures are built from those. Commit per phase. Every five
steps render `just preview NAME` and look at every animation; every phase run `just smoke`.
Human complaints outrank the score: a bent collar, a low visor, small shoes and a jacket that
looked broken from 3/4 cost nothing on the metric and were the most visible faults.

### Phase 0 — set up (1 step)

- `characters/NAME/concept/NAME-pixel-mockup.png` (five views on a plain background) and
  `NAME-concept.png`. `chargen/mockup.py` measures the pixel pitch itself and keeps each view's
  main run of rows (neighbouring views' shoe rows are dropped).
- Copy `assets/recipe-skeleton.toml` to `characters/NAME/recipe.toml`, `assets/NOTES-template.md`
  to `history/NOTES.md`. Set `name`. `just compare NAME` → about 0.6 (no grids yet).
- Check the palette against the mockup before touching it: `--hex down 20,26,12,20` (jacket),
  `--hex down 8,12,14,20` (hair) and so on, or the `legend:` line against the mockup's main
  colours. If the skeleton's ramps already match, phase 1 is one step; if the design differs,
  refit the ramps that differ from these hex reads (large flat areas only).

### Phase 1 — palette (1–3 steps)

`--fit` and `--optimize` are unreliable **before the grids exist**: the bald template sits under
the mockup's hair, so the skin's median reads as hair and the optimizer proposes a red face. Use
`--hex` on flat body areas now; run `--fit`/`--optimize` after phase 2. A `~` in the fit table's
spread column marks a median that is not a colour the mockup uses much (two populations, e.g.
lit and dark columns on the joggers): look at `--hex` before moving. Sample the outline: mockups
from image generation use a warm dark brown, and the outline is the largest single colour.

### Phase 2 — head grids (6–7 steps)

`--draft-grid VIEW` for each of the five mockup views (one step each: paste, clean, score).
Cleaning: isolated speckles inside the hair, the lens row (rim `x`, lens `v`, rim `f`, dark caps
at both ends, no glint), the ear (`o S o`), and nothing drawn on the collar row. Decide the visor
row per angle: front keeps a brow row above the rim; 3/4 and profile sit at eye level. Then the
three left-facing grids by hand from the near-side table in the playbook (the mirrored fallback
puts a one-sided haircut on the wrong side; `compare` warns when they are missing). `--shift
--chars kbHDi` once: a consistent direction across views means the mane wants a column more on
that side — add hair there, never shift the whole grid (it moves the visor and ear).

### Phase 3 — trim per facing (2–4 steps)

`just crops NAME --box 17,31` (torso) and `--box 24,32` (feet), one row per `--recipe` variant;
test every change as a variant file, never in place. The skeleton's rules are the Juno answers;
check them against this design from all eight angles. The playbook lists what was wrong at first
on Juno and is worth checking on any character (collar as straight rows, zipper offsets per
facing, hem before zipper, cuff a shade darker, fingertips, flank region before the trim).
One-sided features (the cyber-arm, the far sleeve) must not carry `_l` twins in their facings:
mirroring moves the arm to the other edge.

### Phase 4 — silhouette (1–2 steps)

`--widths` per view. Differences of 1 are free under the metric; grow only where the mockup is 2
or more wider, with a name (far sleeve/shoulder in 3/4, far shoulder and arm in 3/4-back, near
arm with its shadow seam). The skeleton has these; verify them here rather than adding. `--split`
after: silhouettes at 0.99+.

### Phase 5 — the last thousandths (1–3 steps)

`--slack` (parts with room), `--fit-part CODES` (colours on that part), `--digits VIEW` (the
pixels), then `--optimize`. `--fit-grid VIEW` is a diagnostic: if it finds nothing the grids are
done; look at its cells before applying anything. Re-run `--ceiling` (it rose with every ramp
added) and record it.

### Done when

The score is within about 0.03 of the final `--ceiling`, `--split` shows silhouettes at 0.99+,
the turn-around (`just preview NAME rotate`) reads as one character from eight sides, and the
attack, jump and run at 6× show nothing a person would complain about. Then `just media` and
update README/notes.

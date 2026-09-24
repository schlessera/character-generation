# Playbook: phases in detail

Contents: 1 palette · 2 head grids · 3 trim per facing · 4 silhouette · 5 last thousandths ·
6 checks and hygiene. Rule syntax is in `chargen/character.py` (`_rule_mask`, `_grow`); the
recipe format is `characters/juno/recipe.toml`.

## 1 · Palette and outline

Order of colours by pixel count, which is the order of gain: outline, hair base, jacket base, skin,
pants, hair strands, stubble, shoes, chrome, trim. `compare NAME --fit` prints, per render colour,
the median mockup colour under it. Edge colours (the outline) are unreliable in that table because
of one-pixel drift; confirm them from the mockup's most common colours instead
(`python -c` over `mockup.extract`, or just read the `--text` view: `##` cells).

Semantics that held for the mockup's palette:
- outline: warm dark brown, one ramp (`outline = { base = ... }`) that both `[outline] color` and
  the legend's `o` reference, so colorways swap it in one place;
- the jacket's shade tone nearly equals its base (image-generated fabric is flat); the template's
  shading carries over through the ramp, so the shade slot decides how much the mannequin's
  shading shows;
- the shaved side's shade under magenta hair is plum (`#42222f`): reflected colour;
- the face is lit evenly: the template's cheek shade tone is far too deep for a skin ramp taken
  from a mockup (`#96603a` shade against `#ad7043` base);
- the lens colour is what the mockup paints, not the hex from the concept (`#44e4e8`, not
  `#3ff0ff`); it also drives the emissive glow, so keep it saturated enough to read as a light.

`--optimize` moves each slot within ±28 per channel (±20/step 4 at the end). It agrees with the
fit table when both are right; when it proposes a drift you cannot explain, leave it.

## 2 · Head grids

A grid is head-local: the head template padded by `HEAD_PAD = 3`, one character per pixel, `.` keeps
the template. `just heads NAME` prints each facing's template rows next to its grid. To draw from
the mockup:

1. `just compare NAME --text VIEW`. Rows are frame rows; columns are frame columns (the header
   prints the range).
2. Find the column offset for this facing: the grid's first row of `k` (hair outline) maps to the
   render's first outline row in the text view; `grid col = frame col − offset`. For Juno: down −6,
   down_side −7, side −7, up_side −7, up −6. It is not the same for every facing; deriving it once
   per facing and writing it in the notes saved a full redraw.
3. Rewrite the grid row by row from the mockup's letters, keeping the legend's meaning: `k` hair
   outline, `b/H/D/i` hair base/shade/deep/light, `u/U/w` stubble checker and its light pattern,
   `S/s` skin, `x` rim above the lens, `v` lens, `f` rim below, `o` outline (ear).
4. Where the mockup's head is wider than the template's (the 3/4 view was two columns wider on the
   shaved side), extend by one, not two: the grid may paint on `.` labels beside the head, but the
   body under it does not move.
5. Left-facing grids (`*_l`) are not in the mockup; mirror what the design says (Juno's undercut is
   on her right, so the left views show the mane). Use the same strand vocabulary as the redrawn
   right-facing grids so the turn-around does not change style.

Visor rows per angle: front keeps a skin brow row above the rim (rim, lens, grey rim, chin);
3/4 and profile put the lens one row higher, at eye level. The mockup itself does this. Lens ends
are dark frame caps (`x`), never a glint: `--fit-grid` and the cost maps both said so.

After the grids, `--shift` once per facing. A shift the same anatomical direction in several views
(Juno: one pixel toward her left in 3/4, back and 3/4-back) is hair volume, apply it; a lone shift
in one view is the mockup's own offset, ignore it.

## 3 · Trim per facing

Facing-aware anchors: `front`/`back` for stripes, regions and grow sides resolve to left/right by
facing and flip for `*_l`. Mirroring also swaps the anatomical labels, so a rule on `hand_l` hits
the near hand in one 3/4 view and the far hand in the other; name facings explicitly when the
inner/outer side matters.

**Collar** (a standing bomber collar):
```toml
[[rules]]  # front and 3/4: the torso's straight top row; the zipper rules notch it open
type = "rows"; part = "torso"; from = "top"; n = 1
facings = ["down", "down_side", "down_side_l"]; color = "orange"
[[rules]]  # from behind it hides the neck
type = "all"; part = "neck"; ink = true; facings = ["up", "up_side", "up_side_l"]; color = "orange"
[[rules]]  # profile: its back panel behind the neck
type = "region"; part = "neck"; anchor = "back"; n = 2; ink = true; facings = ["side", "side_l"]; color = "orange"
```
Not `edge torso touching neck`: the neck's boundary is a U and the band bends. Not corner tips
plus flaps in front: they read as a W.

**Zipper / opening.** Front: stripes at −1 (edge), 0 (shirt), +1 (edge), `straight = true`, plus a
one-row skin dip at the top (offset 0, `top = 1`, `skin.shade`). 3/4: 0 (edge), 1 (shirt, `ink =
true`), 2 (edge, `ink = true`) — the chest front projects toward the facing side and the far edge
lands on the template's interior ink column, which rules skip unless told to paint ink. Profile:
`anchor = "front"`, `offset = 0`, `ink = true`, `straight = true` — the front edge column is ink.

**Hem.** `edge torso touching legs, sides down, ink = true` (the template draws the jacket's bottom
line in ink). Place it *before* the zipper rules so the opening splits it, as on an open jacket; a
band running under the opening was tried and cost. Not a bottom-row `rows` rule: it drops pixels
wherever the torso ends diagonally.

**Sleeves.** Cuff = `edge arm_l touching hand_l`, one shade darker than the hem so they do not
merge where the hand hangs beside the torso. Long sleeves: `region hand_l` with the inner side
named per facing (`left` for down and the mirrored 3/4, `right` from behind, n=2 in the 3/4 where
the far hand shows) in the jacket colour, so only fingertips show. The chrome hand needs nothing:
same colour as its sleeve.

**Flank.** `region torso anchor back n=1 jacket.shade` for the 3/4 views, placed before the trim
so the collar and hem paint over it. Do not add an `edge torso touching arms` shading rule: the
template already shades the flank; the rule only adds dark columns beside every sleeve.

**Cyber-arm.** Joint seams in chrome shade, not ink rings; one glow pixel per joint (`band` with
`anchor = "center"` at 0.5 and 1.0); `only_if_ink` rules keep a far arm the template draws as a
silhouette readable as chrome.

**Shoes.** White high-tops: `rows legs from bottom n=1 shoes.base` (one row up the leg), `grow
feet left/right` from the front and behind, `grow feet front` in the 3/4 views, nothing in profile
(the template's foot is already as long as the mockup's), `band foot_* at 0.0 anchor left/right`
orange caps, `rows feet from bottom n=1 shoes.shade` pale sole. Not orange soles.

Judge every trim change on `just crops NAME --box 17,31 --recipe variant.toml`: one row per
recipe, all eight facings. A change that reads well from the front and breaks the 3/4 is the
normal failure.

## 4 · Silhouette

`compare NAME --widths`: per row, mockup vs render extents and the difference per side. The metric
forgives one pixel of drift, so a +1 is already matched; growing for it overshoots and loses (a
general jacket-bulk grow dropped the score 0.007). Grow only for ≥2, with a name:

- 3/4 front: `grow arm_l front n=2` and `hand_l front n=2` (the far sleeve beside the torso),
  `grow torso front n=2` (the far shoulder above it);
- 3/4 back: `grow arm_r front n=1` (the far cyber-arm) and the shoulder cap as `region torso
  anchor front n=2 skip=1 top=2 chrome.base` (the arm cannot grow into the torso, so the torso's
  edge takes the arm's colour);
- 3/4 front, near arm: `grow arm_r+hand_r back n=1` plus `region arm_r anchor front n=1
  jacket.shade` — the mockup's near arm stands out with a dark seam before the torso; growing
  without the seam makes a fat chrome arm and loses.

Grow rules go first in the rule list; later rules see the grown labels. `--split` after: the
silhouette number should be 0.99+ in every view; if colour loss dominates, the silhouette is done.

## 5 · Last thousandths

`--slack`: per part, loss now / loss of the mockup quantized to this palette. The difference is
the room. Typical after phases 1–4: torso 0.01, cyber-arm 0.01, head < 0.01 (the head's loss is
quantization noise once the grids are drawn from the text view; `--fit-grid` confirms it by
finding nothing). `--fit-part T` or `Rr` lists colours on that part with their mockup medians and
mean cost; `--digits VIEW` shows the cost per pixel (9 = nothing similar within one pixel) so a
hot spot can be read against the `--text` rows. Then the finer optimizer pass.

## 6 · Checks and hygiene

- Snapshots `history/step-NN.toml` every five steps, `NOTES.md` one row per step with the score.
- Every five steps `just preview NAME` (all animations) and zoomed crops of walk, run, jump and
  attack in the angled views; the template's squash, spin and swing frames are where a rule that
  holds in idle misplaces.
- `just smoke` per phase (the playground reads the sheets; emissive colours come from the ramps).
- `just media` at the end regenerates every README figure, including the iteration figure and the
  similarity curve from the snapshots; `props-sheet.png` and `cars.png` regenerate byte-different
  but pixel-identical, revert them.
- Keep the recipe's comments saying *why* (the collar is a row because the neck is a U): the next
  person reading it is an agent with the text view open.

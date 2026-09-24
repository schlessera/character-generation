# Playbook: phases in detail

Contents: 1 palette · 2 head grids · 3 trim per facing · 4 silhouette · 5 last thousandths ·
6 checks and hygiene. Rule syntax is in `chargen/character.py` (`_rule_mask`, `_grow`); the
recipe format is `characters/juno/recipe.toml`.

## 1 · Palette and outline

Order of colours by pixel count, which is the order of gain: outline, hair base, jacket base, skin,
pants, hair strands, stubble, shoes, chrome, trim. Before any grid exists, read colours with
`--hex` on body boxes (the bald template under the mockup's hair corrupts the head's medians and the
optimizer). After the grids, `compare NAME --fit` prints, per render colour, the median mockup
colour under it. Edge colours (the outline) are unreliable in that table because
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
the template. Frame = 32×32 (rows 0..31); frame row = grid row + head_y − 3, frame col = grid col +
head_x − 3, and `just heads NAME` prints each facing's template rows next to its grid. For Juno the
column offsets were −6 (down, up) and −7 (the side views), rows −4; they differ per facing.

**Draft, then clean.** `just compare NAME --draft-grid VIEW --quiet` prints a grid where every cell
on the head (or beside it, down to one row below the jaw) takes the legend character nearest in
colour to the mockup pixel under it. Paste it under `[head.grids]`, then clean:

- stray `f` or `x` inside the hair or stubble: a dark plum pixel is nearest to the visor greys;
  every draft has a few, they are the first thing to remove;
- isolated speckles inside the hair (a lone `D` in a field of `b`): keep the strand *lines*, drop
  single pixels;
- the lens rows: `x` rim above, `v` lens, `f` rim below, and the lens ends are `x` (dark caps),
  never a glint — the mockup has none;
- the ear: `o S o` beside the head, `S` and `s` are in `[outline] keep` so they survive the edge;
- the last row: the draft stops one row below the jaw; keep hair characters there (hanging tips),
  clear everything else — in text you cannot tell a tip from the collar, the rule can;
- the hair outline: `k` on the silhouette (it is in `keep`); the draft may choose `o` where the
  mockup's outline is a hair's breadth closer to the outline colour — both read the same.

Legend entries must be fixed slots (`hair.base`), never a tone-relative ramp name: the draft picks
by colour, and a tone-relative entry has no single colour.

**Visor rows per angle.** The draft follows the mockup, which puts a skin brow row above the rim
in the front view (rim, lens, grey rim, chin) and the lens at eye level in 3/4 and profile. Check
that the drafts kept it; do not move rows by hand (a replay read this as an instruction and nearly
shifted a correct draft).

**Left-facing grids** are not in the mockup. `--draft-grid down_side_l --mirror-swap` (and
`side_l`, `up_side_l`) mirrors the right-facing grid about the head template's padded width — a
drafted grid is 20 columns wide while the side templates are 18–19, so reversing the rows as
strings misaligns by one or two — and, because a mirror image swaps her left and right, puts a
one-sided cut back on her own side: the shaved patch stays where it was on screen, its mirror
image becomes hair (drop `--mirror-swap` for a symmetric cut). Then clean and, above all, look: the mirrored fringe of the
profile becomes a forward overhang on the other side. Which side is nearest:

| facing | she faces | nearest side | for Juno's undercut (shaved right, mane left) |
|---|---|---|---|
| down_side_l | down-left | her left | mane toward the viewer, fringe over the near cheek |
| side_l | left | her left | mane covers the near side; visor at the front-left |
| up_side_l | up-left | her right | shaved side nearest, visor tip on the far side |

Without them `render_frame` mirrors the right grid and `compare` prints a warning; a one-sided
haircut then lands on the wrong side in three of eight facings.

**Volume (hand-drawn grids only).** `--shift --chars kbHDi` probes a one-pixel move of the hair
cells. A consistent direction across views (Juno: toward her left in 3/4, back and 3/4-back)
means the mane wants a column more on that side — add hair cells there. A lone shift in one view
is the mockup's own head/body offset; ignore it. Never shift a whole grid: the visor and ear go
with it. Drafted grids come out aligned; the probe finds nothing on them.

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
- 3/4 back: the same `grow torso front n=2` (without it the cap below lands inside the mockup's
  shoulder), `grow arm_r front n=1` (the far cyber-arm) and the shoulder cap as `region torso
  anchor front n=2 skip=1 top=2 chrome.base` (the arm cannot grow into the torso, so the torso's
  edge takes the arm's colour). No `_l` twins on any of these: mirroring puts the arm on the
  other edge;
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
- `just preview NAME attack` writes `build/preview/NAME_attack.png` (the filtered sheet) besides
  the facings image; the unfiltered `NAME.png` is not refreshed by a filtered call.
- `--ceiling` rises with every ramp added (0.912 → 0.936 on the replica run); record it at the end,
  not only in phase 1.
- Keep the recipe's comments saying *why* (the collar is a row because the neck is a U): the next
  person reading it is an agent with the text view open.

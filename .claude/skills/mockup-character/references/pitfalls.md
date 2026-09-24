# Pitfalls: everything that bit during Juno's 110 steps

Each one cost at least a step, some cost ten. Read before editing `[parts]`, grids, or grow rules.

## Recipe semantics

- **`[parts]`: later lines win.** `neck = "skin"` listed before `body = "jacket"` painted the neck as
  jacket for 96 steps; nobody saw it because the neck row is mostly ink and shade tones. Put the
  group lines (`body`) first and the specific parts after them.
- **Rules run in order.** A `region` flank shade placed after the collar overpaints it; a hem placed
  between the front and 3/4 zipper rules is continuous in one view and split in the other. Order:
  grow → region (shading) → collar → hem → zipper → cuffs → shoes → cyber-arm details.
- **Rules skip ink tones unless `ink = true`.** The template draws the jacket's bottom line, the
  torso's far edge in 3/4 and the front edge in profile as ink; a stripe or edge on those columns
  silently does nothing. Pass `ink = true` where the mockup paints there.
- **`only_if_ink`** exists for frames where the template draws a far limb entirely as a silhouette.
- **`[outline] color`** may name a ramp; give the legend's `o` the same ramp so colorways swap both.
- Variants: always as a copy (`compare NAME --recipe tmp.toml`); a tone-relative colour like
  `"orange"` shades with the template, `"orange.base"` does not — both were needed in places.

## Grids

- The column offset between grid and frame differs per facing (−6 for down and up, −7 for the
  side views on Juno). The first redraw of the front grid landed one column left and had to be
  redone; derive the offset from the hair outline row before drawing.
- A string replace over the grids section that includes the `[head.grids]` header renames the
  table (`g` → `x` turned it into `[head.xrids]`, score 0.64). Replace inside the triple-quoted
  strings only.
- `s.index('side_l = """')` matches inside `down_side_l = """`. Search with the leading newline.
- Grids paint on labels `H`, `N` and `.` only; they can extend the head's silhouette but never
  move the body. Chars in `[outline] keep` keep their colour on the silhouette edge (the ear, the
  hair outline); anything else on the edge becomes the outline colour.
- `--fit-grid` unrestricted paints visor grey on the neck rows (the grid reaches below the head)
  and erases the lens glint/tip. With `--chars` limited to hair and stubble tones it is honest,
  and by the end it found nothing: the text-view redraw is already the optimum.

## Found by the replay (a fresh agent using this skill)

- The skeleton shipped without the cyber-arm (ramp, part line, joint rules), without `fx` mapped
  (attack smears rendered as dark blobs), without the stubble legend, and with `_l` twins in the
  facings of one-sided rules (a chrome square on the bare jacket in 3/4-back-left). All fixed in
  the skeleton; when adding a one-sided rule, name its facings without the mirror.
- Palette work before grids: `--fit` put hair under the skin's median, `--optimize` proposed a red
  face. Grids first, or `--hex` on body areas only.
- A fit median on a part where the mockup alternates two colours (lit and dark jogger columns) is
  neither colour; the `~` spread mark flags it, `--hex` shows it. This is general, not only the
  cyber-arm's teal.
- A whole-grid `--shift` moves the visor and ear with the hair; use `--chars kbHDi` and add hair.
- The 3/4-back shoulder cap needs the torso's far-shoulder grow first (the playbook had assigned
  that grow to the 3/4-front only); without it the cap lands inside the mockup's shoulder.
- `--ceiling` moves with the palette; "done when within X of the ceiling" must use the final one.
- Three decimals hide a 0.8997 as 0.900; `compare` prints four now.
- The mockup extractor used to keep a neighbouring view's shoe row at the top of a view; it keeps
  the main run of rows now.

## Score reading

- The metric tolerates one pixel of drift in any direction. A width difference of +1 is already
  matched; growing for it loses. Only ≥2 is worth a silhouette change.
- Each view's mockup is re-centred on the render (best ±1 shift). Widening the render moves the
  mockup, so read `--widths` after a change, not before.
- The mockup's head and body are offset differently per view (its back view's head sits a pixel
  left of its body). A whole-grid `--shift` gain in one view alone is that offset, not hair.
- Colour medians under a colour (`--fit`) mislead where the structure is off by a pixel: the
  cyber-arm's medians read teal because the mockup's glow bleeds; painting the arm teal lost. Use
  the medians for large flat areas, the `--digits` and `--text` views for structure.
- The optimizer's plum stubble shade was refused twice as drift and accepted the third time with
  a reading (shadow under magenta hair). The rule: accept a move when you can say what it depicts.
- The palette ceiling (`--ceiling`, ~0.92) already includes the mockup's noise. The room is the
  slack table, and it lives in the body, not the head.
- Score dips are fine with a reason (the far-sleeve grow before its seam, the hem order) and the
  human said so; a change that only moves the number is not a reason.

## Generator

- `grow` copies the edge pixel outward and fills behind it; the outline pass must take its ink
  mask *after* the rules or the moved outline keeps its pre-outline colour (it showed as chrome
  grey on the cyber-arm). Fixed in `render_frame`; keep it that way if you touch the pipeline.
- `grow` only into transparent pixels: an arm cannot grow into the torso. Use `region` on the
  torso with the arm's colour when the mockup shows the arm over the body (the shoulder cap).
- `region` takes `skip` rows from the top and `top` rows to keep; `anchor` front/back is
  facing-aware; `n` is in pixels per row.

## Human feedback that no score measured

- The collar bent (it followed the neck's curve). The visor sat too low on the side views (it had
  been unified to the front's row; the angles need their own). The shoes were too small (no rule
  could change the silhouette until `grow`). Light marks on the jacket (concept details the mockup
  did not have). The jacket looked broken from 3/4 (zipper on the centre column next to the
  template's shade column, cuff and hem merging, a side-shading rule adding dark columns).
- Each took one to five steps once named. Before declaring a run done, look at the eight facings
  at 14× and the torso and feet crops, and ask what a person would complain about.

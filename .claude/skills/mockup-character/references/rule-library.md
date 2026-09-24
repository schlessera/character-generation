# Rule library: what each garment feature was, on two characters

## Rule types and their keys

Common to all: `part` (a part, a group, or `a+b`), `color` (`ramp` tone-relative, `ramp.slot`
fixed, `#hex`, `clear`), `facings`, `anims`, `per_facing`, `each`, `ink` (also paint the
template's ink pixels), `only_if_ink` (only in frames where the part is all ink).

| type | keys | what it paints |
|---|---|---|
| `all` | | every pixel of the part |
| `rows` | `from` (`top`/`bottom`), `n` | the part's first/last n rows |
| `edge` | `touching` (a part or `none`), `sides` (up/down/left/right) | part pixels next to `touching` on those sides |
| `stripe` | `anchor` (center/left/right/front/back), `offset` or `offsets` (list, or a table per facing), `straight`, `skip`, `top`, `bottom` | a vertical line through the part, one column per offset |
| `band` | `at` (0..1 of the part's height), `n` rows, and with `anchor`: `w` columns, `offset` | horizontal rows at that height, or a w-wide dot on them |
| `region` | `anchor` (left/right/front/back), `n` columns, `skip` rows from the top, `top` rows to keep | the first n columns of the part from that side |
| `grow` | `sides`, `n` | the silhouette pushed out into transparent pixels |
| `shrink` | `sides`, `n` | the silhouette pulled in, the new edge inked |
| `shift` | `dy`, `dx`, `over` | the part moved, landing on transparent pixels or `over` parts |

Snippets here put a rule's keys on one line separated by `; `; the recipe loader and `--try`
accept that shorthand as it is (each `; ` becomes a line), so a line can be pasted under its
own `[[rules]]` header unchanged. Every rule here held in all 248 frames of a finished
character, and its `facings` list is the
answer one run found on one mockup: on the same mockup the next run's answer differed for a
third of them (a forearm band gained in `up_side_l`, not `down_side_l`; the pocket rule lost
in `down_side_l`). Take each rule as a candidate, score it as a variant across the views, and
keep the facings where it gains and the picture agrees. Pick by the design's features, not by
character: Juno (cropped bomber with an orange zipper, joggers, white high-tops, chrome
RIGHT arm, magenta undercut, LED visor) and Nyx (open indigo coat to mid-thigh with lime piping,
grey tee, olive cargos, black boots, chrome LEFT shin, platinum crop, goggles and a mask). Rule
syntax: `chargen/character.py` (`_rule_mask`, `_grow`, `_shrink`). Rules run in order; later
rules paint over earlier ones; `grow`/`shrink` change the labels later rules see. Every rule may
list `facings` and `anims`.

A `stripe` or `band` on a group part (`feet`, `hands`) is ONE stripe through the group's centre
unless the rule says `each = true`, which runs it once per single part (a lace column on each
boot). Any parameter may differ per facing through `per_facing = { side_l = { at = 0.3 },
down_side_l = { n = 1 } }` (overrides merged into the rule for that facing), so a band's height
or a grow's depth need not be a second rule. Facings are the eight template views. `front`/`back` anchors and sides resolve by facing and flip
for `*_l`; mirroring also swaps the anatomical labels, so a rule on `arm_l` hits the near arm in
one 3/4 view and the far arm in the other. Name facings explicitly whenever near/far matters.
With an eight-view mockup every view is scored, so a feature that is symmetric on the body (the
far shoulder, the far sleeve) needs its rule in BOTH 3/4 views, with the part name each frame's
labels give it (the far arm is `arm_l` in `down_side` and `arm_r` in `down_side_l`).

## Silhouette (first in the list)

`--widths` per view; grow or shrink only for a difference of 2 or more, with a name.

```toml
[[rules]]  # 3/4 front: the far sleeve and hand stand beside the torso (Juno: arm_l in down_side)
type = "grow"; part = "arm_l"; sides = ["front"]; n = 2; facings = ["down_side"]; color = "jacket.base"
[[rules]]  # 3/4 front: the far shoulder / upper coat stands out (both characters: n=3 in down_side)
type = "grow"; part = "torso"; sides = ["front"]; n = 3; facings = ["down_side", "down_side_l"]; color = "jacket.base"
[[rules]]  # 3/4 back: the far shoulder (Juno n=2), then the cyber-arm's cap over the jacket edge
type = "grow"; part = "torso"; sides = ["front"]; n = 2; facings = ["up_side"]; color = "jacket.base"
type = "region"; part = "torso"; anchor = "front"; n = 2; skip = 1; top = 2; facings = ["up_side"]; color = "chrome.base"
[[rules]]  # a standing collar / square shoulders: the torso's top row one above the mannequin's
type = "grow"; part = "torso"; sides = ["up"]; facings = ["down", "up"]; color = "jacket.base"   # sideways too in `down` on Nyx; sideways from behind drew shoulder boards
[[rules]]  # sneakers a pixel wider than the mannequin's feet (Juno); nothing in profile
type = "grow"; part = "feet"; sides = ["left", "right"]; facings = ["down", "up"]; color = "shoes.base"
[[rules]]  # 3/4: the far boot's toe row (the template draws only the near foot on the last row; Nyx)
type = "grow"; part = "feet"; sides = ["down"]; facings = ["down_side", "down_side_l", "up_side", "up_side_l"]; color = "shoes.base"
[[rules]]  # a coat skirt hanging over the far leg, 3/4 front (Nyx)
type = "grow"; part = "legs"; sides = ["front"]; n = 2; facings = ["down_side_l"]; color = "jacket.base"
[[rules]]  # a mockup NARROWER than the mannequin: sleeves a column in from behind (Nyx, --widths -2)
type = "shrink"; part = "arms+hands"; sides = ["left"]; facings = ["up", "up_side"]
type = "shrink"; part = "arms+hands"; sides = ["right"]; facings = ["up", "up_side_l"]
[[rules]]  # ...which narrows the two-pixel hands to one inked pixel from straight behind: put the hands back
type = "rows"; part = "arms"; from = "bottom"; n = 1; facings = ["up"]; color = "skin.base"   # (+0.005 in up on run 3)
```

A grow placed before a straight stripe moves the stripe: the median column is taken over the
widened part (Nyx's opening strip shifted by one column in 3/4 front with the far-shoulder grow
first: -0.004; the picture was right with the grow first, and per-facing `offsets` settle it).
`shift` moves a part (`type = "shift"`, `part`, `dy`, `dx`; `dx` flips on left facings): the
template's hands hang a row lower than both mockups' (`shift hands dy = -1, over = ["arms"]` in
front: the hand takes the sleeve's last row); pixels land only on transparent pixels, the part
itself or the parts in `over`, the vacated ones go transparent, the new silhouette is inked. Shrink erases the part's edge pixels on that side and inks the new silhouette. It cannot tell a
one-sided feature from the body: shrinking the legs' front edge in profile erased Nyx's cyber-shin.
Judge every silhouette change on `just crops NAME --box 17,31 --diff`.

## Shading before trim

```toml
[[rules]]  # 3/4: the flank turned away, one column one shade darker (Juno; scored worse on Nyx's coat)
type = "region"; part = "torso"; anchor = "back"; n = 1; facings = ["down_side", "down_side_l"]; color = "jacket.shade"
[[rules]]  # the waistband's shadow above a hem (Juno)
type = "rows"; part = "torso"; from = "bottom"; n = 2; color = "jacket.shade"
[[rules]]  # profile: a coat's back fold, a dark line inside the back edge (Nyx)
type = "region"; part = "torso"; anchor = "left"; n = 1; facings = ["side"]; color = "outline.base"
```

## Collar

```toml
[[rules]]  # a standing bomber collar, front and 3/4: the torso's straight top row (Juno)
type = "rows"; part = "torso"; from = "top"; n = 1; facings = ["down", "down_side", "down_side_l"]; color = "trim"
[[rules]]  # from behind the collar hides the neck (Juno trim; Nyx's coat collar in `jacket` from the side and behind).
type = "all"; part = "neck"; ink = true; facings = ["up", "up_side", "up_side_l"]; color = "trim.base"   # redundant when the drafted grids already paint the neck rows
[[rules]]  # profile: the collar's back panel behind the neck (Juno)
type = "region"; part = "neck"; anchor = "back"; n = 2; ink = true; facings = ["side", "side_l"]; color = "trim.base"
[[rules]]  # profile: a coat's collar row plus piping down the front edge (Nyx; one pixel inside the edge).
# Profile trim ALWAYS stacks into hooks in the attack's spin: keep `anims` without attack on it from the start
type = "rows"; part = "torso"; from = "top"; n = 1; facings = ["side", "side_l"]; anims = ["idle", "walk", "run", "jump", "rotate", "interact"]; color = "trim.base"
type = "stripe"; part = "torso"; anchor = "front"; offset = -1; facings = ["side_l"]; anims = ["idle", "walk", "run", "jump", "rotate", "interact"]; color = "trim.base"
```
Not `edge torso touching neck`: the neck's boundary is a U and the band bends. A neck shown as
skin in the coat's V is `neck = "skin"` in `[parts]` (after `body`).

## Opening

```toml
[[rules]]  # a zipper, front (Juno): edges at -1 and +1, the shirt at 0, straight on twisted poses
type = "stripe"; straight = true; part = "torso"; offset = -1; facings = ["down"]; color = "trim.base"
type = "stripe"; straight = true; part = "torso"; offset = 0; facings = ["down"]; color = "shirt"
type = "stripe"; straight = true; part = "torso"; offset = 1; facings = ["down"]; color = "trim.base"
[[rules]]  # the collar's inner edges in shadow for two rows, so the neck shows in a V (Juno)
type = "stripe"; straight = true; part = "torso"; offset = -1; top = 2; facings = ["down"]; color = "outline.base"
[[rules]]  # 3/4 zipper: the chest projects toward the facing side; the far edge is on the template's
type = "stripe"; straight = true; part = "torso"; offset = 0; facings = ["down_side", "down_side_l"]; color = "trim.base"   # ink column, so paint ink
type = "stripe"; straight = true; part = "torso"; offset = 1; ink = true; facings = ["down_side", "down_side_l"]; color = "shirt.base"
type = "stripe"; straight = true; part = "torso"; offset = 2; ink = true; facings = ["down_side", "down_side_l"]; color = "trim.base"
[[rules]]  # profile zipper, one pixel inside the front edge (on the edge the outline pass repaints it)
type = "stripe"; part = "torso"; anchor = "front"; offset = -1; facings = ["side", "side_l"]; color = "trim.base"
[[rules]]  # an OPEN COAT to mid-thigh (Nyx): a four-column strip showing the tee (first 4 rows), a
# belt (row 5) and the pants below, in front and 3/4 front. `skip`/`top`/`bottom` pick the rows:
type = "stripe"; straight = true; part = "torso"; offsets = [-2, -1, 0, 1]; top = 4; facings = ["down", "down_side", "down_side_l"]; color = "shirt"
type = "stripe"; straight = true; part = "torso"; offsets = [-2, -1, 0, 1]; skip = 4; top = 1; facings = ["down", "down_side", "down_side_l"]; color = "outline.base"
type = "stripe"; straight = true; part = "torso"; offsets = [-2, -1, 0, 1]; skip = 5; facings = ["down", "down_side", "down_side_l"]; color = "pants.base"
type = "stripe"; straight = true; part = "torso"; offsets = [-2, 1]; top = 4; facings = ["down"]; color = "outline.base"   # the lapels' dark inner edges, front only (+0.003; lost in 3/4)
```
A straight stripe's column is the median over the whole part, so stacked stripes stay one strip.
`offset` and `offsets` may be a table keyed by facing with `"*"` as the default (Nyx's strip sits
one column further toward the far side in 3/4 front left: `offsets = { "*" = [-2, -1, 0, 1],
down_side_l = [-3, -2, -1, 0] }`), so one rule set serves every facing. The numbers read as in
the right-facing frame; the mirror is applied after them, so "one column toward the far side"
in an `_l` facing is each offset minus one.

## Hem

```toml
[[rules]]  # a cropped jacket's hem on the torso's bottom line (Juno): before the zipper rules, so
type = "edge"; part = "torso"; touching = "legs"; sides = ["down"]; ink = true; color = "trim.base"   # the opening splits it
[[rules]]  # a coat that falls over the thighs (Nyx, from behind): two leg rows of coat, the hem band on the first
type = "rows"; part = "legs"; from = "top"; n = 2; ink = true; facings = ["up", "up_side", "up_side_l"]; color = "jacket"
type = "rows"; part = "legs"; from = "top"; n = 1; ink = true; facings = ["up", "up_side", "up_side_l"]; color = "trim.base"
[[rules]]  # the hem crosses the hands resting in the pockets: a lime row on the hands' last row (Nyx, +0.007 in profile; `anims` without run/attack)
type = "rows"; part = "hands"; from = "bottom"; n = 1; facings = ["side", "side_l", "down_side", "down_side_l"]; anims = ["idle", "walk", "rotate", "interact"]; color = "trim.base"
[[rules]]  # 3/4 front: piping down the skirt's front edge over the far leg (Nyx)
type = "region"; part = "leg_r"; anchor = "left"; n = 1; facings = ["down_side_l"]; color = "trim.base"
```
Not a bottom-row `rows` rule for a torso hem: it drops pixels wherever the torso ends diagonally.

## Sleeves and hands

```toml
[[rules]]  # cuff at the wrist, a shade darker than the hem so they do not merge (Juno)
type = "edge"; part = "arm_l"; touching = "hand_l"; color = "trim.shade"
[[rules]]  # long sleeves, fingertips only: the hand's inner side per facing (Juno)
type = "region"; part = "hand_l"; anchor = "left"; n = 1; facings = ["down", "down_side_l"]; color = "jacket.base"
type = "region"; part = "hand_l"; anchor = "right"; n = 1; facings = ["up", "up_side", "up_side_l"]; color = "jacket.base"
[[rules]]  # hands in the pockets (Nyx's pose): the sleeve over the hand where the mockup shows none.
# ORDER: this goes BEFORE the hem's "hem across the pocketed hands" row, or it overpaints it (run 5 lost the hem that way)
type = "all"; part = "hands"; facings = ["down_side", "side_l"]; color = "jacket"
type = "rows"; part = "hands"; from = "top"; n = 1; facings = ["side", "up_side", "up_side_l", "down_side_l"]; color = "jacket"
[[rules]]  # a band round the forearm (Nyx): per facing, the height differs (0.5 in front, 0.3 in profile-left)
type = "band"; part = "arms"; at = 0.5; facings = ["down", "down_side_l", "side"]; color = "trim.base"
[[rules]]  # 3/4 back: on one sleeve only, the screen-right arm (arm_r in up_side, arm_l in up_side_l)
type = "band"; part = "arm_r"; at = 0.3; facings = ["up_side"]; color = "trim.base"
[[rules]]  # a sleeve's dark open end over the hand from behind and in profile (Nyx)
type = "rows"; part = "hands"; from = "bottom"; n = 1; facings = ["side", "up_side", "up_side_l"]; color = "outline.base"
[[rules]]  # the shoulder seam in front (Nyx)
type = "rows"; part = "arms"; from = "top"; n = 1; facings = ["down"]; color = "outline.base"
```

## Back detail

```toml
[[rules]]  # an emblem between the shoulders: two centred pixels, `straight` or they slant in 3/4 (Nyx)
type = "band"; part = "torso"; at = 0.25; anchor = "center"; straight = true; facings = ["up", "up_side", "up_side_l"]; color = "trim.base"
type = "band"; part = "torso"; at = 0.375; anchor = "center"; straight = true; facings = ["up", "up_side", "up_side_l"]; color = "trim.base"
```

## Cyber-limb

A one-sided limb is a `[parts]` line, never a rule: `"arm_r+hand_r" = "chrome"` (Juno) or
`leg_l = "chrome"` (Nyx) follows the anatomical labels through the mirror. Details:

```toml
[[rules]]  # joint seams in chrome shade, one glow pixel per joint (Juno's arm)
type = "band"; part = "arm_r"; at = 0.5; color = "chrome.shade"
type = "band"; part = "arm_r"; at = 0.5; anchor = "center"; color = "glow.base"
type = "edge"; part = "arm_r"; touching = "hand_r"; color = "chrome.shade"
type = "band"; part = "arm_r"; at = 1.0; anchor = "center"; color = "glow.base"
[[rules]]  # a far arm the template draws entirely in ink still reads as chrome
type = "all"; part = "arm_r+hand_r"; ink = true; only_if_ink = true; color = "chrome.shade"
[[rules]]  # a knee seam at the top of the visible shin (Nyx)
type = "band"; part = "leg_l"; at = 0.0; facings = ["down", "down_side", "down_side_l", "side", "side_l"]; color = "glow.base"
[[rules]]  # the shin's polished back edge in 3/4 front; chrome down the foot where the mockup shows no boot
type = "stripe"; part = "leg_l"; anchor = "back"; facings = ["down_side", "down_side_l"]; color = "chrome.light"
type = "region"; part = "foot_l"; anchor = "left"; facings = ["up_side", "up"]; color = "chrome"
```

## Shoes

```toml
[[rules]]  # white high-tops (Juno): one row up the leg, pale sole, orange caps at both ends of the upper row
type = "rows"; part = "legs"; from = "bottom"; n = 1; color = "shoes.base"
type = "rows"; part = "feet"; from = "bottom"; n = 1; color = "shoes.shade"
type = "band"; part = "foot_r"; at = 0.0; anchor = "left"; color = "trim.base"   # and right, and foot_l
[[rules]]  # black boots (Nyx): laced one row up the leg only where the mockup shows it, one lime lace pixel
type = "rows"; part = "legs"; from = "bottom"; n = 1; facings = ["side_l", "down_side_l"]; color = "shoes.base"
type = "band"; part = "foot_r"; at = 0.0; anchor = "center"; facings = ["down", "down_side", "side_l"]; color = "trim.base"
type = "rows"; part = "feet"; from = "bottom"; n = 1; facings = ["up_side_l"]; color = "shirt"   # grey soles from 3/4 back
```

## Animation-only fixes

`anims = ["idle", "walk", ...]` limits a rule to those animations (per facing through
`per_facing = { side_l = { anims = [...] } }`). The general case: any rule whose part is a
HAND, an ARM or a LEG but which depicts the coat (pockets, a hem along the hand's bottom row or
the legs' top row, a skirt over the hand) is wrong wherever that limb swings — the run and the
jump as much as the attack — lime bars ran along the
arm in the run and the attack on Nyx until the rule got `anims = ["idle", "walk", "rotate",
"interact"]`. Profile trim (a cuff, piping, a hem) also stacked into a hook in the attack's
spinning frames: exclude `attack` there too. Only idle is scored, so the score never sees it;
`just preview NAME walk run jump attack` (file `NAME_walk_run_jump_attack.png`) does.

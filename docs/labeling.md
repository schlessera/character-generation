# Template part labeling guide

Each unique template frame has a label file `assets/template/16x32/labels/NNN.txt`.
Every row is `YY |<tones>|<labels>|`. The tones column is the read-only pixel data:

| tone char | meaning |
|---|---|
| (space) | transparent |
| `.` | base (lit fill) |
| `s` | shade (shaded fill, far side, back limbs) |
| `l` | light shade (face contour, mouth, ear) |
| `b` | blush |
| `#` | ink (outline, eyes, darkest fill of far limbs) |

The labels column assigns every opaque pixel a body part. Transparent pixels must be `.`
and every opaque pixel must get a non-`.` label.

| label | part |
|---|---|
| `H` | head: skull, face, ears, the head's own outline down to the chin |
| `N` | neck (the short narrow row(s) between chin and shoulders) |
| `T` | torso: chest, belly, hips/pelvis/crotch |
| `R` / `r` | the character's RIGHT arm / right hand (hand = last ~2 px of the arm, the fist) |
| `L` / `l` | the character's LEFT arm / left hand |
| `P` / `p` | RIGHT leg / right foot (foot = bottom ~2 rows of the leg, the shoe) |
| `Q` / `q` | LEFT leg / left foot |
| `X` | effects: attack smears / motion arcs that are not part of the body |

Sides are anatomical, not screen sides:
- down (facing viewer): character's right = screen LEFT.
- down_side / side / up_side face screen-right. The character's right side is toward the
  viewer (near side, usually lit `.`), the left side is away (far side, usually `s` or `#` fill).
- up (back to viewer): character's right = screen RIGHT.
- Rotate frames 5, 6, 7 face screen-left (mirrors): there the near/lit side is the LEFT side.

Outline (`#`) pixels belong to the part they enclose. Where two parts touch, split the
shared outline sensibly. Consistency across the frames of one animation matters more
than perfection on a single ambiguous pixel. Use the far-limb shading (darker `s`/`#` fill)
to tell far limbs from near limbs.

The zoomed reference image of each frame is `build/frames_zoom/NNN.png` (generate with `just label-zoom`)
(16x zoom, grid lines every pixel, bright lines every 4 px, axis numbers every 2 px).
Frame 000 is the hand-made reference example (idle, facing down).

Tools (run from the repo root):
- `uv run python -m chargen.labeltool check 12 13` validates files.
- `uv run python -m chargen.labeltool render 12 13 -o build/mine.png` renders
  original | label colors | overlay, so you can look at your result and fix it.

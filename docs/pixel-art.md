# Prop and tile pixel art guide

Sprites are hand-drawn text files in `assets/props/pixel/NAME.txt`: first line `# NAME WxH`,
then H rows of exactly W characters. Each character is one pixel, a color from
`assets/props/palette.toml`; `.` is transparent. Sizes are fixed by `assets/props/props.toml`
(the `w`/`h` of each item) and must not change.

The generated images in `assets/props/source/` are the design reference only (what the object
is, its parts, its colors). They are painterly and much too detailed. Redraw the object at the
target size as real pixel art: decide what each pixel is.

## Style (match the character sprites in `web/data/characters/juno/sheet.png`)

- Camera: top-down 3/4. Standing props show a top face and a front face; boxy objects may show
  a side face on the right. The bottom row of a standing prop is where it touches the ground.
- Light from the top-left: top faces lightest, front faces mid, right side faces and undersides
  darkest. 2-4 shades per material, taken in order from one palette ramp.
- `#` outline, 1 px, around the whole silhouette. Inside the object use the darkest shade of
  the material (or `k`/`K`) for internal lines, not `#` everywhere.
- Clean shapes: no single-pixel noise, no random speckles, no dither fields. Every pixel has a
  reason; texture and wear are added on top of the clean shape (see below).
- Silhouette first: at 1x the object must be recognizable from its shape and 2-3 color masses.
- Neon/emissive parts: dark ramp color around, neon color for the tube, hot color for the
  brightest core pixels (magenta `m M n`, cyan `z Z x`, fire `O y Y`).
- Floor decals (puddle, stain, stripe, cables, litter) are flat on the ground: no front face,
  no outline where a soft edge reads better (puddles, stains).
- Tiles (16x16, opaque, no `.`): must tile seamlessly with themselves and with the other floor
  tiles. Keep floor tiles low contrast (floor ramp `a A s S p`) so props and characters read on top.

## Texture and wear

Clean shapes are the base, not the finish. A finished prop looks used: it has the same kind of
deliberate texture the character has (hair strands drawn as darker lines, a buzzed side drawn as
a two-shade checker, plate seams on the cyber-arm, jagged tips instead of a smooth outline).
Texture is placed, not sprinkled:

- **Material first.** Each material gets its own texture, in its own ramp: metal gets panel
  seams, rivets (one light pixel over one dark), scratches (a short light diagonal) and dents;
  rust runs *down* from bolts, seams and edges in 1 px streaks; wood gets grain as broken darker
  dashes along the plank and the odd knot; cardboard gets tape, creases and a stamp; fabric and
  plastic get fold lines and scuffs; concrete gets hairline cracks (a 1 px zigzag one shade
  darker) and chipped edges.
- **Wear follows physics.** Grime (`C`, `F`) gathers where the object meets the roof, in corners
  and under overhangs. Top-left edges catch the light: a 1 px highlight line, broken where the
  edge is chipped. Moss (`P`) only where water sits.
- **Break the symmetry a little.** A dented corner, a lid slightly ajar, a sticker half peeled,
  a bent rung, one pixel missing from a silhouette edge. Nothing mirrored pixel for pixel.
- **Clusters, not noise.** Texture comes in short lines and 2-3 px clusters that follow the
  form. No uniform speckle and no dither fields. Roughly 10-25% of an object's interior pixels
  carry texture; the object must still read at 1x from its silhouette and 2-3 color masses.
- **Light from the scene.** Metal faces toward the upper-left may take cool steel (`U`); edges
  next to neon may catch a few neon-spill pixels (`V`, or `z` for cyan). Sparingly.
- **Animated props:** texture frame 0, then `pixeltool rebase NAME` rebuilds the other frames
  from it, carrying over only the pixels each frame moves. Check the result with `pixeltool anim`.

## Tools (from the repo root)

- `uv run python -m chargen.pixeltool render NAME... -o build/pixel/NAME.png`
  reference | your sprite at 12x | your sprite at 4x next to the character (tiles: 3x3 repeat)
- `uv run python -m chargen.pixeltool check NAME...` size and palette validation
- `uv run python -m chargen.pixeltool floor TILE... -o build/pixel/floor.png` random floor patch

## Animated props

An item with `anim = [ms, ms, ...]` in `props.toml` has one file per frame: frame 0 is
`NAME.txt`, frame k is `NAME@k.txt` (same size). `pixeltool frames NAME` seeds the extra
frames as copies of frame 0. Animate by changing only the pixels that move; the silhouette,
outline and body stay identical so the prop does not wobble. Loops must be seamless (last
frame flows into frame 0). Small, readable motion beats big motion at this scale:
- fire: flame tongues shift shape and height by 1-2 px, hot core (`Y`) moves, a spark pixel
  may appear above; never the same flame twice in a row.
- lights/neon: on/off or bright/dim by swapping ramp colors (`Z`<->`z`, `M`<->`m`, `Q`<->`q`).
- rotation (fan blades): blade pixels step around the hub.
- `glow_anim` (optional) sets the engine's glow strength per frame; keep it consistent with
  how bright the frame is.

Review with `uv run python -m chargen.pixeltool anim NAME -o build/pixel/NAME_anim.png`:
all frames at 10x with changed pixels marked (yellow dots) and the per-frame change count,
plus `build/pixel/NAME.gif` for the loop.

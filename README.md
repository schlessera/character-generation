<div align="center">

# Character Generation

**A faceless pixel-art mannequin becomes an animated cyberpunk courier, in a lit rooftop scene, with an AI agent
directing (and drawing) every pixel.**

<a href="https://schlessera.github.io/character-generation/">
  <img src="https://img.shields.io/badge/%E2%96%B6%20%20PLAY%20THE%20LIVE%20DEMO-schlessera.github.io%2Fcharacter--generation-ff3fa4?style=for-the-badge&labelColor=1d1c26" alt="Play the live demo" height="42">
</a>

<br><br>

<a href="https://schlessera.github.io/character-generation/"><img src="docs/images/hero.gif" alt="Juno walking across the rooftop while flying cars pass overhead" width="800"></a>

<sub>Runs in the browser, nothing to install.<br>
<kbd>WASD</kbd> / arrows move · <kbd>Shift</kbd> run · <kbd>Space</kbd> jump · <kbd>J</kbd> attack · <kbd>E</kbd> interact<br>
<kbd>C</kbd> switch character · <kbd>V</kbd> animation gallery · <kbd>L</kbd> lighting on/off · <kbd>F</kbd> call a flying car</sub>

</div>

---

## The idea

Pixel-art character templates are a gift to game developers. Someone has already done the hard part, the animation,
and you "only" have to dress the mannequin. This project starts from
[Eris Esra's Character Templates Pack](https://erisesra.itch.io/character-templates-pack): a bald, featureless figure
with 158 hand-animated frames of idle, walk, run, jump, a punch-and-kick combo, interact and a turn-around, drawn in
five directions.

Dressing it is still a lot of work. Every frame has to become a specific character, the hair has to sit on a head that
squashes and stretches, and a cyber-arm has to stay on the same arm through a spinning kick. So the question behind
this repository was:

> *Can an AI agent figure out, largely by itself, how to go from generic template shapes to the specifics of a
> character design, and then build a small world around that character?*

The answer is **Juno "Static" Okafor**, a rooftop data courier with a magenta undercut, an LED visor and a chrome
cyber-arm, animated in every frame of the template and in eight directions. Around her is a rooftop full of
hand-drawn props, lit by neon, fire and passing flying cars.

The finished demo is fun, but the more interesting part is how the problem got broken down:

```mermaid
flowchart LR
    T["Animated template<br/>158 frames"] --> C["Catalog<br/>frames · tones · head tracking"]
    C --> L["Body-part labels<br/>one text file per frame"]
    CA["Concept art<br/>image generation"] -. reference .-> R["Character recipe<br/>recipe.toml"]
    L --> G(("Generator"))
    R --> G
    G --> S["Sprite sheet<br/>7 animations × 8 facings"]
    PA["Prop concept art"] -. reference .-> P["Hand-placed pixel props<br/>one text file per sprite"]
    P --> A["Props atlas"]
    S --> E["Browser playground<br/>lighting · shadows · flying cars"]
    A --> E
```

| | Chapter | In one sentence |
|---|---|---|
| 1 | [Meet the mannequin](#1--meet-the-mannequin) | Turning an `.aseprite` file into data an LLM can reason about |
| 2 | [Teaching the AI anatomy](#2--teaching-the-ai-anatomy) | Labeling every pixel of every frame with the body part it belongs to |
| 3 | [Pixels as text](#3--pixels-as-text) | Why every image here is also a text file |
| 4 | [Dressing the mannequin](#4--dressing-the-mannequin) | A character is a recipe that renders onto all frames at once |
| 5 | [Variations for free](#5--variations-for-free) | A new colorway is a ten-line file |
| 6 | [The AI picks up the pencil](#6--the-ai-picks-up-the-pencil) | Why concept art can't just be shrunk into pixel art |
| 7 | [From sources to sprites](#7--from-sources-to-sprites) | The build that assembles everything |
| 8 | [Mood lighting](#8--mood-lighting) | How atmospheric can basic pixel graphics get? |

---

## 1 · Meet the mannequin

<p align="center"><img src="docs/images/template-sheet.png" alt="The template's animations" width="720"></p>

The pack ships Aseprite files, so the first step was a small reader (`chargen/aseprite.py`) that pulls out frames and
animation tags. Getting the data out was easy. Understanding it took more work, and a few details shaped everything
that followed.

The template has **no colors in the usual sense**. Every pixel is one of exactly five tones: lit fill, shade, light
shade, blush and ink. That shading is the most valuable thing in the template: it is the artist's understanding of
light and form. So the catalog stores tones, not colors. Recoloring then becomes "map each tone to a new material",
and Juno's jacket inherits the original folds and shadows for free.

The **head gets tracked** in every frame. It squashes during jumps and whips around during the attack, so each frame's
head is matched against per-direction head templates. That gives anything that has to sit on the head, like hair,
visors and hats, a reliable anchor.

And **left isn't simply a mirror image.** The template only draws the right-facing side views. Mirroring them for
the left side is fine for a symmetric mannequin, but it would move a one-sided cyber-arm to the wrong arm. How that gets
solved is the subject of the next chapter.

## 2 · Teaching the AI anatomy

<p align="center"><img src="docs/images/labels-frame.png" alt="A template frame, its part labels, and the overlay" width="760"></p>

Recoloring by tone alone gives you a mannequin in one color. To say "black bomber jacket, orange cuffs, chrome right
arm", the generator needs to know which pixels *are* the jacket, the cuffs and the right arm, in every frame and in
every pose. So every opaque pixel of all 129 unique frames carries a body-part label: head, neck, torso, left and
right arm, hand, leg and foot, plus an effects label for the white smears of the attack.

The labels are anatomical, not screen-based. When the mannequin faces you, its right arm is on your left. That rule
fixes the mirroring problem: a left-facing frame is the right-facing frame mirrored *with its left and right labels
swapped*, so the cyber-arm stays on Juno's right arm whichever way she turns.

This is by far the most expensive step, and it only has to happen once. After that, a character is a handful of rules
over labels, and those rules hold in all 158 frames, including the awkward mid-air and mid-kick poses.

The labeling itself was a small AI production line. Simple heuristics made a rough first guess: the head from
tracking, a hip line, screen sides. One carefully hand-labeled reference frame pinned down the conventions. Then
eight subagents took one group of animations each and worked in a tight loop: edit the label file, validate it,
render it, *look* at the render, fix what's wrong. Each agent came back with a list of the pixels it wasn't sure
about, for example whether a lit blob in a mid-air jump frame is a tucked thigh or a forearm.

<p align="center"><img src="docs/images/labels-sheet.png" alt="Labels stay consistent through walk, run, jump and attack" width="760"></p>

## 3 · Pixels as text

Every image an agent reads or edits here is also a **plain text file with one character per pixel**, where a row of
the file is a row of the image. A label file shows the template's tones and the labels side by side:

```text
# frame 0 rotate/all[0] 100ms head=down@9,7
   tones: . lit  s shade  # ink        labels: T torso  R/L arms  r/l hands  P/Q legs  p/q feet
25 |        #...s......s...#        |........RRRRTTTTTTTTLLLL........|
26 |        #..##ssssss##..#        |........rrrrTTTTTTTTllll........|
27 |         ## #ss##ss# ##         |.........rr.PPPPQQQQ.ll.........|
28 |            #ss##ss#            |............PPPPQQQQ............|
30 |            #ss##ss#            |............ppppqqqq............|
31 |           #..s##s..#           |...........pppppqqqqq...........|
```

The hand-drawn props use the same idea, with a shared palette in which every character is a named color:

```text
# fire_barrel 13x24          O orange  y fire yellow  Y fire hot  R/r rust  # outline  . transparent
...#.#O#.....
..#O##OO#....
..#O##OyO##..
...#OOyyOOO#.
..#OyYYYYyO#.
```

That turned out to matter more than any single algorithm. An LLM can *see* the shapes in text like this, talk about
"columns 9 to 11 of rows 21 to 25", and change exactly those pixels. Every edit is a readable diff, so review is just
git. And because every format comes with a checker (sizes, palette, "every opaque pixel is labeled") and a renderer
that shows the result at 12× next to the character, the agents never had to trust their own text. They looked at the
picture.

## 4 · Dressing the mannequin

<table>
<tr>
<td width="62%"><img src="docs/images/juno-concept.jpg" alt="Juno concept art"></td>
<td><img src="docs/images/juno-pixel-mockup.jpg" alt="Pixel mockup at template proportions"></td>
</tr>
<tr>
<td><sub>The concept turnaround (image generation) settles who Juno is.</sub></td>
<td><sub>A pixel mockup at the template's proportions shows what still reads at 32 pixels.</sub></td>
</tr>
</table>

The concept art is a reference, not an ingredient. Juno herself is a **recipe**, `characters/juno/recipe.toml`, that
the generator paints onto every labeled frame:

```toml
[palette]           # color ramps; the template's tone picks the slot (base / shade / light / blush / ink)
skin   = { base = "#b07148", shade = "#7f4a2d", light = "#95593a", blush = "#b8624f" }
jacket = { base = "#34323d", shade = "#23222a", light = "#2b2a33", ink = "#141318" }
chrome = { base = "#d9e1ea", shade = "#8894a3", light = "#f4f8fb", ink = "#3a4250" }

[parts]             # body part (or group) -> material; later lines win
head = "skin"
body = "jacket"
"arm_r+hand_r" = "chrome"     # the cyber-arm, on the anatomical right in every frame

[[rules]]           # details computed from label geometry, per frame
type = "edge"       # torso pixels that touch the legs become the jacket's orange hem
part = "torso"
touching = "legs"
sides = ["down"]
color = "orange"
```

A recipe works in layers. First every body part gets a material, and the template's tone picks the shade, so the
original lighting carries over. Then small **rules** add details derived from the labels' geometry: a collar where the
torso meets the neck, a hem where it meets the legs, a zipper down the middle of the torso, cuffs, soles, a glowing
wrist joint on the cyber-arm. Because the rules are geometric, they adapt to each pose by themselves.

Hair and the visor can't be derived from the body, so they are drawn as small **head grids**, one per facing, which
get placed on the tracked head in every frame. A grid character can mean "keep the template pixel" or "use this
material, shaded like the pixel underneath", which lets a single grid survive squash-and-stretch. The anatomical
sides pay off again here: the undercut is on Juno's right, so the right-facing views show the shaved side and the
left-facing views show the magenta fringe.

<p align="center"><img src="docs/images/juno-facings.png" alt="Template and Juno in all eight facings" width="820"></p>

<table>
<tr>
<td><img src="docs/images/walk.gif" alt="Template and Juno walking in 8 directions" width="520"></td>
<td><img src="docs/images/juno-anims.gif" alt="Juno's animations" width="180"></td>
</tr>
</table>

## 5 · Variations for free

Once one character exists, the next one is cheap. Recipes can extend each other, so a new colorway only lists what
changes:

```toml
# characters/juno-glitch/recipe.toml
extends = "juno"
name = "Juno (Glitch)"

[palette]
hair   = { base = "#9dff3a", shade = "#4fb21c", light = "#e2ff9e", ink = "#153a0a" }
jacket = { base = "#3a2a55", shade = "#271c3b", light = "#312447", ink = "#150e22" }
orange = { base = "#ff3fd2", shade = "#b8209a" }   # trim turns hot pink
```

<p align="center"><img src="docs/images/variants.png" alt="Template, Juno, and the Glitch variant" width="620"></p>

The same trick works for props. The flying car is painted with three placeholder paint colors, and every variant in
`assets/props/props.toml` is just three new hex values:

```toml
flycar_parked = { w = 80, h = 38, kind = "solid", base = 14, variants = {
  red  = { "1" = "#4a0c16", "2" = "#a01c2c", "3" = "#e8484c" },
  taxi = { "1" = "#6e4a08", "2" = "#c89414", "3" = "#f6d23a" } } }
```

<p align="center"><img src="docs/images/cars.png" alt="Car variants next to Juno" width="620"></p>

## 6 · The AI picks up the pencil

<p align="center"><img src="docs/images/rooftop-concept.jpg" alt="Rooftop concept art" width="820"></p>

A character needs a world, and this is where it would be tempting to let image generation do the work. It's excellent
at concept art like the rooftop above. It is not good at *pixel art at a planned size*. Its "pixel art" is painted at
roughly four or five screen pixels per art pixel, with no consistent grid, soft glows, and far more detail than a
20×40 sprite can hold. Shrinking it to game size produces mush:

<p align="center"><img src="docs/images/props-resample-vs-drawn.png" alt="Generated reference, resampled version, hand-placed pixels" width="660"></p>

Forcing the model onto a grid didn't help either. Given a guide image with one grid cell per art pixel and a slot per
object at its exact size, it respected the slots, ignored the grid, and painted in high resolution again:

<p align="center"><img src="docs/images/grid-attempt.png" alt="Grid-locked generation attempt" width="760"></p>

So the roles got split. The concept art decides *what* an object is: its parts, colors and mood. The manifest,
`props.toml`, decides *how big* it is next to the character, along with its collision footprint, glow, animation
timing and paint variants. And the pixels themselves are placed deliberately, by agents working in the palette text
format.

```mermaid
flowchart LR
    C["Concept art<br/>scene · per-object sheets"] --> D["Automatic draft<br/>downscale + palette snap"]
    M["props.toml<br/>size · collision · glow · frames · variants"] --> D
    D --> H["Hand-placed pixels<br/>render → look → fix"]
    H --> A["atlas.png + atlas.json<br/>+ emissive layer"]
```

A rough automatic draft (the middle column above) served only as a starting hint. Parallel agents then redrew all 34
props and 24 floor and wall tiles following a written style guide ([`docs/pixel-art.md`](docs/pixel-art.md): a 3/4
top-down view, light from the top left, two to four shades per material, a one-pixel outline, no noise). Every agent
checked its sprites at 12× and next to Juno at game scale, and checked the floor tiles in a random mix to catch seams.

<p align="center"><img src="docs/images/props-sheet.png" alt="All props and tiles" width="820"></p>

Animations use the same format: each extra frame is a copy of the sprite that changes only the pixels that move, so
the outline never wobbles.

<p align="center"><img src="docs/images/prop-anims.gif" alt="Animated props" width="420"></p>

## 7 · From sources to sprites

Everything above is source material: template, labels, recipes, pixel files and manifests. One command turns it into
what the browser loads.

```mermaid
flowchart TB
    subgraph Sources
      V["template .aseprite"]
      LB["labels/*.txt"]
      RC["characters/*/recipe.toml"]
      PX["pixel/*.txt · palette.toml · props.toml"]
    end
    V --> CAT["catalog + head tracking"] --> GEN["render recipe onto every frame<br/>+ mirrored left facings"]
    LB --> GEN
    RC --> GEN
    GEN --> SH["characters/NAME/sheet.png + sheet.json"]
    PX --> PK["check · variants · frames · pack"] --> AT["props atlas + emissive layer"]
    SH --> WEB["web/ = the whole site"]
    AT --> WEB
```

| Command | What it does |
|---|---|
| `just play` | Builds everything and serves the demo at <http://localhost:8000> |
| `just build` | Packs the props atlas and renders every character sheet into `web/data/` |
| `just preview juno` | Contact sheet of every animation in every facing |
| `just heads juno` | Shows a character's head grids next to the template's head outlines |
| `just labels run` | Template frames colored by body part, for review |
| `just pixel vending_machine` | A sprite at 12× and at game scale next to the character |
| `just smoke` | Headless Chromium plays the demo with the keyboard and checks the results |
| `just media` | Regenerates every image in this README |

Every push to `main` runs the same build and the smoke test on GitHub Actions and publishes the demo to GitHub Pages.

## 8 · Mood lighting

With a character and a world in place, the last question was a fun one: how atmospheric can plain pixel graphics get
with a few technical tricks?

<p align="center"><img src="docs/images/lighting-compare.png" alt="Flat pixel art versus lit scene" width="880"></p>

Quite a lot, it turns out. Every glowing prop became a colored light source: the vending machine, the neon sign, the
fire barrel, the antenna beacon, the glowing mushrooms. The neon floor strips, the wall lights and a cool moon join
them. All that light is added up in one buffer that then colors the scene, so shadows come out tinted: a spot in the
fire's shadow is still bathed in the sign's pink.

The shadows are computed from the sprites themselves. Each pixel of an object gets a height above its ground line, and
the object's columns are projected onto the floor away from every light, so a chair casts a chair-shaped shadow and a
mast casts a long, thin one. Shadows soften at the edges and fade as they stretch away from their object. Juno's shadow
is recomputed every frame from her current pose.

A few rules keep it looking like pixel art rather than a filter. Light falls off in flat, clean bands instead of
smooth gradients or dithering. Neon and fire pixels are drawn at full brightness on top of the lit scene, so they
really glow. And shadows only ever remove direct light, so no pile-up of overlapping shadows can get darker than the
night itself.

<table>
<tr>
<td><img src="docs/images/shadows-closeup.png" alt="Computed shadows near the fire barrel" width="400"></td>
<td><img src="docs/images/flyover.png" alt="A flying taxi's headlight sweeping the roof" width="400"></td>
</tr>
<tr>
<td><sub>Every prop and the character cast their own shadows, away from every light.</sub></td>
<td><sub>Flying cars pass overhead, and their headlights sweep the roof with live shadows.</sub></td>
</tr>
</table>

```mermaid
flowchart LR
    MO["moon"] --> D["direct light"]
    PL["neon, fire & lamps<br/>shadows baked in"] --> D
    CAR["flying car lights<br/>live shadows"] --> D
    D --> O["× Juno's shadow<br/>× contact shadows"]
    O --> A["+ ambient"]
    A --> F["scene × light"]
    F --> E["+ glowing pixels"]
```

The full model is described in [`docs/lighting.md`](docs/lighting.md).

---

## Behind the scenes: how the AI organized the work

All of this came out of a conversation with an AI coding agent (Claude), with image generation for the concept art.
A few patterns did most of the work:

- **First make the problem text-shaped.** The Aseprite reader, the tone and label files and the pixel palette format
  all came before any drawing.
- **Invest once, reuse everywhere.** Labeling the template was the biggest single effort, and it made every
  character and variant after that almost free.
- **Parallel agents, each with its own eyes.** Label groups, prop groups and tile sets went to separate subagents. Each
  one validated and *looked at* its own renders, and reported what it wasn't sure about.
- **Image generation where it shines.** Generated images supplied the ideas and the references, never the shipped
  pixels.
- **Everything reproducible.** Every artifact, including the images in this README, is rebuilt from source with a
  `just` command.

## Try it yourself

You'll need [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/).

```sh
just setup    # Python dependencies + headless Chromium for the tests
just play     # build everything and serve the demo at http://localhost:8000
```

<details>
<summary><b>Repository layout</b></summary>

```text
characters/          character recipes (recipe.toml) and their concept art
assets/template/     per-frame body-part labels for the 16x32 template
assets/props/        palette.toml, props.toml, hand-drawn pixel files, concept + reference art
chargen/             Python pipeline: aseprite reader, catalog, labels, recipes, props, review tools
web/                 the demo (a static site); the build writes its data to web/data/
tools/               smoke test, benchmark, README media generator
docs/                labeling guide, pixel-art style guide, lighting notes, README images
vendor/              the Eris Esra character template (unmodified, with its license)
```

</details>

---

## Credits

<div align="center">

Original character template created by **Eris Esra**<br>
<https://erisesra.itch.io/character-templates-pack>

<a href="https://erisesra.itch.io/character-templates-pack"><img src="docs/images/badges/itchio-badge-color.svg" alt="Character Templates Pack on itch.io" height="54"></a>

</div>

The template (v4.1) is included unmodified in [`vendor/eris-esra-character-templates/`](vendor/eris-esra-character-templates/)
so the demo builds out of the box. It is pay-what-you-want: if this project is useful to you, please get the pack
from itch.io and support the author.

The template, and everything in this repository derived from it (the label files in `assets/template/` and the
generated character sprite sheets), stays under Eris Esra's terms rather than this repository's license. Those terms
allow use in commercial and non-commercial projects and ask free projects for exactly the credit above. They do not
allow character commissions, asset packs, or reselling the template with add-ons or modifications.

Concept art and design references were generated with an image model (gpt-image-2). Every in-game prop and tile was
drawn as a pixel file in this repository. The "Available on itch.io" badge is from the
[official itch.io press kit](https://itch.io/press-kit).

## License

The source code and documentation are released under the [MIT License](LICENSE). The template and the artwork
derived from it follow Eris Esra's terms, described above.

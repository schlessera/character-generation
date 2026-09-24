# Nyx: concept and mockup generation log

Second character for the semantic sprite skinning generator, made to test how much of the
`mockup-character` skill is Juno-specific. Every generated image is kept under `attempts/`
(prompt, verdict and what changed here), the accepted ones are copied to `nyx-concept.png` and
`nyx-pixel-mockup.png`.

## Design brief (decided before any generation)

Nyx "Halo" Ferreira, 24, rooftop drone mechanic. Chosen to differ from Juno on every axis the
skill might have hard-coded:

| axis | Juno | Nyx | what it tests |
|---|---|---|---|
| skin | dark brown | light olive | palette refit |
| hair | magenta undercut, one-sided | short platinum-white crop, symmetric | `--mirror-swap` must be off; no stubble legend |
| eyes | cyan LED visor across the eyes | round lime goggles pushed up on the forehead, eyes visible | the "visor rows" logic in draft/clean |
| face | bare | charcoal respirator half-mask with one lime LED | a second head-grid material below the eyes |
| torso | cropped bomber, orange zipper | open indigo work coat to mid-thigh, lime piping, over a grey tee | the hem is on the legs, not at the torso/legs edge |
| legs | charcoal joggers | olive cargo pants | nothing special |
| one-sided feature | chrome right arm | chrome LEFT shin with a lime knee seam | one-sidedness on the legs (labels P/Q), not the arms |
| shoes | white high-tops with orange caps | black combat boots with lime laces | shoe rules refit (taller, dark) |
| emissive | visor lens + arm joints | goggles, mask LED, knee seam | emissive parts on a different part |

Mockup format: eight views (all template facings), not five, so the left-facing views are
scored instead of mirrored.

## Attempts

### concept-01 — accepted

`attempts/image-20260924-182822-44dd59-concept-01.png`, `generate_image`, 1536×1024, high. Prompt: the
design brief as a reference-sheet description in Juno's sheet format (front, 3/4, side, back, two
callouts, info box, palette). Verdict: everything in the brief is there and readable; the cyber-leg
is her left in the front view (screen-right) and the back view (screen-left). Copied to
`nyx-concept.png`.

### mockup-01 — rejected: wrong pixel resolution

`attempts/edit-20260924-182937-*-mockup-01-{1,2}.png`, `edit_image` over [concept, Juno's mockup,
`docs/images/juno-facings.png`], 1024×3072, high, n=2. Prompt: Juno's sheet format with eight views
in turn-around order, "about 27 art pixels tall, ~9 screen pixels per art pixel".
Measured: pitch 5.36 screen px (the spectrum's top eight peaks all sit at 5.3–5.5, no 9–11 peak at
all), figures 58–61 art px tall, 27–30 wide — twice the template's 25×16. The model kept the
figure's *screen* size close to the reference (~320 px vs 240) and halved the pixel size to fit
the extra detail (eyes, mask seams, a belt buckle). Both candidates have all eight views in the
right order and the cyber-leg on the correct side in every view, so the turn-around instruction
itself works. Fix to try: a mannequin guide at exactly 12 px per art pixel (the template's idle
frames), and a re-prompt that states the pitch in screen pixels.

### mockup-02 — rejected: the mannequin guide is ignored for scale

`attempts/edit-20260924-183227-*-mockup-02-guide-{1,2}.png`, `edit_image` over
[`attempts/mannequin-guide-12px.png` (the template's eight idle frames at exactly 12 px per art
pixel on Juno's background), concept, Juno's mockup], 1024×3072, high, n=2. Prompt: "paint the
character onto each mannequin, keep the 12 px grid". Measured: pitch 7.9–8.1, figures 41 tall
× 18–20 wide. The model kept the poses and the eight positions but repainted at its own pixel
size, the same failure the README reports for the grid-locked prop attempt. One candidate lost
the left profile (a 22-row fragment). Dead end: a pixel guide does not transfer its grid.

### mockup-03 — one hit: 03-1 accepted as fallback

`attempts/edit-20260924-183319-*-mockup-03-pitch-{1,2}.png`, `edit_image` over [concept, Juno's
mockup], 1024×3072, high, n=2. Prompt: the pitch stated in screen pixels ("11 by 11", "27 art
pixels tall, about 300 screen pixels", "no eyes, no belt buckle; if you draw them the pixels are
too small"). Measured: 03-1 pitch 11.1, figures 26–28 tall × 11–14 wide — the template's scale
(25 × 12–16); 03-2 pitch 7.75, 41 tall. 03-1: all eight views in order, cyber-leg on the correct
side everywhere, reads as the character at art resolution; 2 px narrower than the mannequin
from the front (14 vs 16). Noise: 205–256 distinct colours per ~250-pixel view, the same ratio
as Juno's mockup (324 of 348), so the palette quantization handles it as before.

### mockup-04 — rejected: same prompt as 03, no hit in three

`attempts/edit-20260924-183500-*-mockup-04-pitch-{1,2,3}.png`, same call as 03 with n=3.
Measured: pitch 7.4–8.3, figures 38–45 tall. Hit rate for the 03 prompt: 1 in 5.

### mockup-05 — rejected: a pixel reference at the right scale does not anchor the scale either

`attempts/edit-20260924-183643-*-mockup-05-refine-{1,2,3}.png`, `edit_image` over [03-1,
`docs/images/juno-facings.png`, concept], 1024×3072, high, n=3. Prompt: "redraw at exactly the
same pixel size, 2–3 px wider like the mannequin". Measured: pitch 7.9–8.1, 38–44 tall. The
model anchors on the figure's screen height (~300–320 px in every attempt so far) and chooses
the detail level itself; neither a stated pitch, a mannequin grid nor a same-scale reference
moves it reliably. Next: make the figure physically smaller on the canvas (216 px, a 1024×2048
canvas) so the model's preferred ~8 px pitch yields 27 art pixels.

### mockup-06 — rejected: a smaller figure gets smaller pixels, not fewer

`attempts/edit-20260924-183855-*-mockup-06-small-{1,2,3}.png`, `edit_image` over [concept, Juno's
mockup], 1024×2048, high, n=3. Prompt: "8 by 8 screen pixels, each figure 27 art pixels = about
216 screen pixels tall, small on the canvas". Measured: figures ~210 screen px tall as asked, but
pitch 4.4–4.7 → 42–50 art px. So the anchor is neither the pitch nor the screen size: the model
wants ~40–60 art pixels of detail for this design and scales the pixels to fit. (Juno's five-view
sheet came out at 27 art px; her design has fewer parts.)

### mockup-07 — rejected: five more of the 03 prompt, no hit

`attempts/edit-20260924-184038-*-mockup-07-pitch-{1..5}.png`, the 03 call with n=5. Measured:
pitch 7.0–8.3, 36–47 tall; one has nine segments (a figure split by a light row). Hit rate of
the 03 prompt over 12 draws: 1.

### Decision: 03-1 is `nyx-pixel-mockup.png`

Pitch 11.1, 26–28 art px tall, eight views in turn-around order, cyber-leg on the correct side in
every view, the character reads. Known deviation from the template: 2 px narrower than the
mannequin from the front and back (14 vs 16), 1 px narrower in profile; Juno's mockup was 2 px
wider, so the fixed silhouette loss is comparable, only with the opposite sign (rules can grow a
part outward but nothing can shrink the mannequin).

Finding for the process: gpt-image-2 does not take a pixel scale from a stated pitch, a stated
figure height, a same-scale pixel reference or a mannequin grid. Requests at 1024 px wide land
at ~8 px per art pixel most of the time; the only reliable lever seen so far is how much detail
the design carries. Twelve draws for one usable sheet is acceptable for a one-off, not for a
pipeline; a downscale step from a 2× sheet (the 01 candidates are at a clean 2:1 ratio to the
template) is the alternative to test if a third character needs one.

# Lighting and shadows

Implementation: `web/lighting.js` (algorithm notes at the top), wired in `web/engine.js`
(`buildLighting`, `draw`). Scene settings: `LIGHTING` in `web/rooftop.js`. `L` toggles it in game.

## Model
- Light buffer: direct light (moon + every point light) is summed, then all occlusion
  (contact shadows, moving shadows) multiplies the direct part only, then ambient is added.
  The darkest any shadow, or any overlap of shadows, can get is "no direct light" = ambient;
  baked shadows obey the same rule because each only removes its own light. The buffer is
  then multiplied over the scene. Colored shadows come for free: a spot shadowed from one light is still lit by the others.
- Point lights: every prop with `glow` in `assets/props/props.toml` (color = glow, height =
  55% of the sprite, flicker = `glow_anim`), plus neon floor strips and cyan wall neon tiles.
- Shadows: each opaque sprite pixel has a height above the object's ground line
  (`base / 2` above the sprite's bottom). Columns of pixels are projected onto the floor away
  from the light (`P + (P - L) * h / (Lh - h)`, capped at `maxShadow`) and rasterized into that
  light's mask with a pixel-center test, so edges stay on the pixel grid. Walls are extruded boxes.
- Rasterization intersects edge half-planes per scanline, keeping the pixel-center tolerance
  and projected-corner coverage for thin quads. Point-light occluders are skipped only when
  their ground footprint, extended away from the light by `maxShadow`, cannot reach the mask.
- Baked: lights and props are static, so each light's falloff, posterized into flat bands, with its
  shadows cut out is computed once at load. The moon and non-flickering lights are combined
  into one canvas per light buffer; flickering lights are added individually each frame.
- Per frame: the hero's shadow from its current animation frame, for the moon and every light
  in range, and contact shadows (AO) under props, both applied to the direct light only; objects lit
  without shadows (no self-shadowing); emissive pixels (`web/data/props/atlas_emissive.png`,
  chosen by palette chars in `props.toml`) drawn unlit on top; soft additive bloom halos last.

## Knobs
`fadeTo` (shadow strength left at the tip), `blur` (penumbra radius),
`ambient`, `moon.color/dir/length/shadow`, `shadow` (strength inside a shadow), `levels`
(flat bands for falloff and shadow edges), `maxShadow`. Per light: `radius`, `intensity`, `h`, `shadow`
(strength scale), `maxShadow` (floor strips use short, weak shadows).

## Sources
- mattdesl, 2D Pixel Perfect Shadows: https://github.com/mattdesl/lwjgl-basics/wiki/2D-Pixel-Perfect-Shadows
- Scott Lembcke, 2D Lighting Techniques / Hard Shadows: https://www.slembcke.net/blog/2DLightingTechniques/ , https://www.slembcke.net/blog/SuperFastHardShadows/
- Frank Force, 2D Dynamic Light Mapping: https://frankforce.com/2d-light-mapping/
- Matt Greer, Dynamic Lighting and Shadows (height-based shadow casting): https://www.mattgreer.dev/blog/dynamic-lighting-and-shadows/
- Catlike Coding, Light and Shadow (pixel-art filtering): https://catlikecoding.com/godot/true-top-down-2d/4-light-and-shadow/

## Moving lights (flyover)
Flying cars cross above the roof, a new one every 2.5-8 s; each finishes its own pass, so several can be on screen at once (`FLYOVER` in `web/rooftop.js`,
`F` forces a pass). Only its lights exist: a headlight spot 44 px up, aimed ahead of the craft
(smoothstep cone, attenuation reaching exactly zero at 2.2x its range, so it never clips),
two red tail lights and a faint blue underglow. `Lighting.dynamicLights` computes them every
frame for the visible area only, with live shadows from props, walls and the hero, into the
same flat bands; they join both light buffers, so the ambient clamp still holds. The path
starts and ends `margin` px outside the view (larger than the light's reach), so the light
glides in and out. `bloom` adds part of that light on top of the final image, because a
multiply-only light can never look brighter than the unlit texture.

Moving light work is limited to scanline spans inside the attenuation circle/ellipse and
spot cone. Shadow masks cover those spans plus a `2 * blur` halo for the two blur passes;
clipping at the original view/light bounds preserves the blur's edge clamping. Scratch
masks, blur buffers, hero shadow image data, and the band-to-byte table are reused.
Accumulation clearing and band conversion visit the union of lit scanline spans. Canvas
uploads cover the bounding union of the previous and current light areas (clearing departed
lights), while additive draws and bloom use only the current bounds. Wall tops bypass
headlight shadows when sampling the light, rather than clearing a separate wall-mask pass.
The hero's masks are blurred only within their nonzero bounds plus the same blur halo.
Light positions and shadow projections are recomputed every frame without position
quantization or cached static shadows; moving cars and the hero retain live shadows.

Car sprites (moon/ambient tint and emissive pixels) and their blurred moon silhouettes are
prepared at load for each model, animation frame, and direction, including unlit sprites
for the lighting toggle. Per-frame draws reuse these canvases at the current position;
headlight shadows still respond to the scene every frame.

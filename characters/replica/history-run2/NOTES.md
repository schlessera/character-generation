# replica iteration log

Each step: `just compare replica` (mockup above the render), read the text view, change the recipe
(or the generator), re-render, look again. `step-NN.toml` is the recipe after step NN, saved every
five steps. Similarity: mean over the five mockup views. Palette ceiling (`--ceiling`): 0.934 (final).

| step | change | similarity |
|---|---|---|
| 0 | skeleton recipe (Juno's palette), name set, no grids | 0.6382 |
| 1 | front (down) head grid drafted with --draft-grid, cleaned (lens cap, ear o S o, collar row cleared, one f speckle) | 0.6830 |
| 2 | down_side head grid drafted, cleaned (lens caps, ear, f speckle, collar row cleared) | 0.7293 |
| 3 | side head grid drafted, cleaned (ear o S o, lens caps, f speckle; neck row cleared except hair tip) | 0.7802 |
| 4 | up_side head grid drafted, cleaned (f speckles, neck row cleared but for a hair tip) | 0.8389 |
| 5 | up (back) head grid drafted, cleaned (f speckles, ears o S o, neck row cleared) | 0.9045 |
| 6 | down_side_l grid by hand: mirrored down_side with the mane on the near (back) side hanging over the near cheek, stubble at the far temple (no mockup view: score unchanged) | 0.9045 |
| 7 | side_l grid by hand: face and visor at the front-left, mane covering the near (left) side of the head down to the jaw (score unchanged) | 0.9045 |
| 8 | up_side_l grid by hand: shaved side nearest (her right), mane on the far side over the top, visor tip poking out at the face edge (score unchanged) | 0.9045 |
| 9 | hem colour trim -> trim.base: the tone-relative 'trim' left the template's ink bottom line dark (trim has no ink slot), so the hem was missing in 3/4, profile and back | 0.9050 |
| 10 | side_l grid: trimmed the mane's forward overhang in front of the face (read as a pompadour at 12x; the right profile has none) | 0.9050 |

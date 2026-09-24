# replica iteration log

Each step: `just compare replica` (mockup above the render), read the text view, change the recipe
(or the generator), re-render, look again. `step-NN.toml` is the recipe after step NN, saved every
five steps. Similarity: mean over the five mockup views. Palette ceiling (`--ceiling`): 0.9__.

| step | change | similarity |
|---|---|---|
| 0 | skeleton recipe, placeholder colours | |
| 1 | skeleton | 0.6387 |
| 2 | draft-grid all --clean --apply --mirror-swap | 0.9025 |
| 3 | left grids by hand: down_side_l shaved strip at the far (screen-left) edge, side_l all mane with the face, up_side_l shaved near side with ear; filled clean's template-skin holes in the right grids | 0.9041 |
| 4 | 3/4-back collar solid: drop the drafted hair-outline cells on the last grid row of up_side/up_side_l (they punched dark gaps into the orange collar) | 0.9034 |
| 5 | cyber-arm joint and wrist glows on the arm's outer (back) edge in the turned views, centre kept in front/back | 0.9046 |
| 6 | final check after lint fix (glow twins for _l facings centred; unscored views) | 0.9046 |

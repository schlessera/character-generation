# replica iteration log

Each step: `just compare replica` (mockup above the render), read the text view, change the recipe
(or the generator), re-render, look again. `step-NN.toml` is the recipe after step NN, saved every
five steps. Similarity: mean over the five mockup views. Palette ceiling (`--ceiling`): 0.912 (down 0.925, down_side 0.921, side 0.900, up_side 0.902, up 0.913).

| step | change | similarity |
|---|---|---|
| 0 | skeleton recipe (its palette is Juno's), chrome ramp + `arm_r+hand_r` part added, no grids | 0.630 |
| 1 | chrome ramp read off the mockup's arm pixels: neutral grey #a9a9a9/#878788/#bebebe (placeholder was bluish) | 0.632 |
| 2 | pants.shade -> #252629 (fit median); lost 0.002, reverted | 0.630 |
| 3 | stubble ramp (#523d30/#7d5a46, plum shade #42222f) + legend t/w/p; front head grid drafted from the placed mockup quantized to the legend (offset -6 cols, -4 rows), down 0.683 -> 0.905 | 0.676 |
| 4 | 3/4 front head grid from the mockup (offset -7), down_side 0.655 -> 0.890 | 0.723 |
| 5 | profile head grid from the mockup (offset -7), side 0.637 -> 0.891 | 0.774 |
| 6 | 3/4 back head grid from the mockup (offset -7), up_side 0.602 -> 0.897 | 0.833 |
| 7 | back head grid from the mockup (offset -6), up 0.582 -> 0.907 | 0.898 |
| 8 | left-facing grids by hand: down_side_l/side_l mane toward the viewer (mirrored right grids, stubble -> strands), up_side_l shaved side near, visor tip far (not scored) | 0.898 |
| 9 | --shift: down +1, up_side -1 (both toward her left); front shift tried (+0.002 down) but it moves visor and ear off the face; reverted | 0.898 |
| 10 | cyber-arm joint glows: band arm_r at 0.5 and 1.0, anchor center, glow.base (elbow, wrist); arm_r loss 0.020 -> 0.018 (unrounded mean 0.89975) | 0.900 |
| 11 | 3/4 back, up_side only: grow torso front n=2 (the far shoulder), grow arm_r front n=1, chrome shoulder cap (region torso front n=2 skip=1 top=2); up_side 0.8945 -> 0.8982, unrounded mean 0.90049 | 0.900 |
| 12 | fx label mapped to a pale smear ramp: the attack's swing smears rendered as dark-brown blobs (not in the mockup, score unchanged; final) | 0.900 |

Final: 0.90049 (down 0.9078, down_side 0.8913, side 0.8963, up_side 0.8982, up 0.9089) at step 11; step 12 is visual only.
Ceiling re-run at the end: 0.936 (rose from 0.912 as the stubble and chrome ramps were added). Silhouettes 0.997-1.000 (`--split`). `just smoke` passes.
Grid offsets (grid col = frame col + offset, grid row = frame row - 4): down -6, down_side -7, side -7, up_side -7, up -6.

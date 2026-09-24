# replica iteration log

`just step replica "what changed" --goal 4` writes a row here after every change and snapshots the
recipe every fifth step as `step-NN.toml`. Similarity: mean over the five mockup views; the goal
is a percentage below the palette ceiling (`--goal` prints both).

| step | change | similarity |
|---|---|---|
| 0 | skeleton | 0.6443 |
| 1 | drafted all head grids (--draft-grid all --clean --apply --mirror-swap); glint facings fixed (lint) | 0.9084 |
| 2 | left grids rebuilt by facing: down_side_l far strip only at the screen-left edge, side_l lens cap + mane over ear, up_side_l near side = her left (mane), shaved strip far right, without the near-black plum column | 0.9084 |
| 3 | waistband shadow: the jacket row above the hem in jacket.shade (mockup back: uniform #242528 row over the hem) | 0.9108 |
| 4 | sleeve elbow crease removed: the mockup's sleeve is flat (#34-#38, no dark row at the elbow in down) | 0.9115 |
| 5 | 3/4 front far shoulder grow n=3 (widths +2..+3 on rows 18-23); n=4 scored +0.002 more but blocks the shoulder out | 0.9120 |
| 6 | visor tip from 3/4 behind: strap + cyan tip in up_side grid row 10 (mockup: J# t# C- v past the face edge), mirrored tip at up_side_l's face edge | 0.9121 |

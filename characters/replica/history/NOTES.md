# replica iteration log

`just step replica "what changed" --goal 4` writes a row here after every change and snapshots the
recipe every fifth step as `step-NN.toml`. Similarity: mean over the five mockup views; the goal
is a percentage below the palette ceiling (`--goal` prints both).

| step | change | similarity |
|---|---|---|
| 0 | skeleton | 0.6387 |
| 1 | draft-grid all --clean --apply --mirror-swap | 0.9028 |
| 2 | redraft the five scored grids at the post-grid alignment (back views one row up); up_side_l = up_side (ear and shaved patch at screen-right) | 0.9058 |
| 3 | grid texture fit within families (hair tones, stubble tones, outline) on the scored views, head rows only | 0.9078 |
| 4 | down_side far cuff only at the sleeve's outer end (it met the zipper edge as a bar) | 0.9079 |
| 5 | mechanism: [outline] parts — the joggers' silhouette edge in pants.ink (cool black), as the mockup draws it | 0.9088 |
| 6 | square bomber shoulders: grow torso up one row in every facing (collar now ends on the shoulders) | 0.9100 |
| 7 | profile zipper one pixel inside the front edge, following the chest (was only an L at the hem: the median column and the outline pass hid it) | 0.9099 |
| 8 | forearm highlight only in the 3/4-front view with the near cyber-arm (the mockup's arm has none from front, profile or behind) | 0.9107 |
| 9 | front: open collar, its inner edges in shadow for two rows (the neck shows in a V, zipper edges start below) | 0.9109 |
| 10 | 3/4 front: the near arm's shadow seam continues past the hand (it hangs off the hip) | 0.9119 |

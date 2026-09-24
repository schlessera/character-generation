# Juno iteration log

Each step: `just compare juno` (pixel mockup above the render), list what differs most,
change the recipe (or the generator), re-render, look again. `step-NN.toml` is the recipe
after step NN. Similarity: mean over the five mockup views (see `chargen/mockup.py`).

| step | change | similarity |
|---|---|---|
| 0 | first recipe: colors, rule-based trim, simple hair cap | 0.614 |
| 1 | hair grids redrawn from the snapped mockup: part line, sweep, stubble checker | |
| 2 | deep-pink strand lines, visor strap removed from back views | |
| 3 | open jacket over black shirt, high collar, side shading, near-black pants | |
| 4 | cyber-arm: darker chrome, plate seams, single-pixel joint glows | |
| 5 | jagged strand tips, left-facing grids redrawn, all animations checked | 0.706 |
| 6 | hair palette pulled toward the mockup's darker magenta, softer highlight | 0.735 |
| 7 | visor as a framed lens (dark end caps), no longer sticking out of the face | 0.735 |
| 8 | ear on the shaved side; new `[outline] keep` so drawn silhouette pixels survive the outline pass | 0.735 |
| 9 | materials sampled from the mockup: neutral jacket greys, neutral chrome, warmer orange, off-white shoes | 0.753 |
| 10 | concept details: chest logo mark, grey chevron print on the back | 0.752 |
| 11 | near-black hair outline and a much softer highlight, like the mockup | 0.765 |
| 12 | cargo-pocket marks on the thighs, darker jogger cuffs above the sneakers | 0.765 |
| 13 | new `rule_facing = "head"`: trim turns with the body in the spinning attack (no zipper on her back) | 0.765 |
| 14 | cyber-hand finger gap, polished highlight on the forearm plate | 0.766 |
| 15 | circuit pattern shaved into the undercut (concept detail) | 0.768 |
| 16 | back views: strands redrawn to run with the sweep, away from the part (they ran against it; flagged by the human watching) | 0.767 |
| 17 | left-facing front and profile grids get the jagged strand tips of the right-facing ones | 0.767 |
| 18 | collar standing up behind the neck in profile and from behind | 0.767 |
| 19 | orange heel tab on the high-tops (an all-orange back of the shoe was tried and reverted: the metric dropped and the mockup disagrees) | 0.767 |
| 20 | glint on the visor lens | 0.766 |
| 21 | cheek blush toned down to skin (the mockup has none) | 0.766 |
| 22 | stripe `straight = true`: the zipper stays one straight column on twisted run and attack poses | 0.766 |
| 23 | visor narrowed to the mockup's lens widths (front 7 px, 3/4 6 px, profile 5 px); it spanned the whole face (flagged by the human watching) | 0.767 |
| 24 | the lens runs under the hair with a dark end cap instead of stopping short | 0.768 |
| 25 | stubble continues down the temple beside the visor to the ear; the 3/4-left lens re-anchored to the front of the face (step 23 had trimmed the wrong end there; flagged by the human watching); from behind, the visor tip no longer pokes out past the head, just one dim lens pixel on the cheek edge (flagged too) | 0.767 |

## Second run (steps 26–40)

Same loop, with new instruments in `just compare`: per-body-part loss, heat maps of where
the score leaks, `--text VIEW` (mockup | render as palette letters, editable like a head
grid) and `--fit` (the median mockup color under every render color).

| step | change | similarity |
|---|---|---|
| 26 | outline and hair outline in the mockup's warm dark brown (`#241a17`, `#261b19`) instead of near-black; the single biggest leak the fit table showed | 0.800 |
| 27 | pants in the jacket's grey (the mockup draws them the same) | 0.803 |
| 28 | palette refit from `--fit`: hair base/shade/light/deep, lighter shoe shade, skin and stubble nudged | 0.828 |
| 29 | the collar is open from the front: flaps and zipper edges only, neck skin between (was a solid orange band) | 0.828 |
| 30 | grey rim under the visor lens (was skin shade); high-tops one row taller, pale soles, orange toe and heel caps instead of orange soles; all animations checked | 0.836 |
| 31 | profile grid redrawn from the mockup's text view: the whole back of the head is shaved down to the jaw, the hair sweeps from the crown forward, an outlined ear, the tip ends one row higher | 0.841 |
| 32 | front grid redrawn the same way: a row of brow above the visor (the mockup's lens sits one row lower, the head is the same height), an 8-px dark rim, the stubble wider, the hair starts two columns later with deep pink along the part | 0.845 |
| 33 | 3/4 grid redrawn the same way; the mockup's head is two columns wider on the shaved side there, the grid extends it by one | 0.848 |
| 34 | the visor sits on the same head row in every facing (the mockup has it a row higher in profile than from the front; consistency wins in the turn-around); brow row over the eyes in profile and the left-facing grids | 0.848 |
| 35 | all animations checked; snapshot | 0.848 |
| 36 | back and 3/4-back grids redrawn from the text view: the hair a row shorter with a dark bottom edge over the neck, the shaved side wider, an ear from behind, strands as shade rather than deep | 0.862 |
| 37 | jacket hem paints over the template's ink edge (it was patchy where the template draws the jacket's bottom line in ink); the 3/4 collar open like the front (a far zipper edge was tried: the 3/4 torso is five pixels wide, the far edge is its outline) | 0.863 |
| 38 | second `--fit` pass: pants shade, orange shade and shoe shade nudged toward the mockup (chrome and cyan variants tried, no gain, kept) | 0.867 |
| 39 | orange collar tips at the jacket's top corners, where the mockup has them, instead of only beside the neck | 0.867 |
| 40 | all animations checked, README figures regenerated; snapshot | 0.867 |

## Third run (steps 41–55)

| step | change | similarity |
|---|---|---|
| 41 | lens cyan darkened to the mockup's (`#3ce4ec`; the cost map showed every lens pixel half-matched), orange shade lighter | 0.870 |
| 42 | new `compare --optimize`: bounded coordinate descent over the ramp slots (±28 per channel), prints moves, applies nothing. It found the same cyan move and one plum drift of the stubble shade toward the hair shadow, rejected: an advisory tool, not an autopilot | 0.872 |
| 43 | new `compare --ceiling`: the mockup quantized to the recipe's own palette, scored against itself. 0.926 for this palette, so the remaining gap (0.054, worst in the 3/4 view) is shape: the mockup's body is wider than the template's | 0.872 |
| 44 | zoomed frame review of walk, run, jump and attack: the back collar tab drew a three-row "T" down the spine in the jump, now one pixel below the band as in the mockup; the back print is a small chevron (three band rules) instead of two stacked pixels | 0.872 |
| 45 | snapshot | 0.872 |
| 46 | heel-tab rule dropped: with the toe and heel caps it made a third orange spot on the profile shoe (neutral on the score, cleaner) | 0.872 |
| 47 | Glitch colorway: its own purple-black outline and a visible circuit pattern (its stubble `light` equalled its `shade`) | 0.872 |
| 48 | outline and visor rims are ramps (`outline`, `visor`) that the legend and `[outline]` reference, so a colorway swaps them with the palette; `[outline] color` may name a ramp | 0.872 |
| 49 | the 3/4 view's cost map: every remaining hot spot is the mockup's wider torso edge and far arm, none on the head; the optimizer's second pass only repeats the rejected plum move. Converged on the mockup | 0.872 |
| 50 | snapshot; playground smoke test | 0.872 |
| 51 | left-facing grids (not in the mockup) in the same strand vocabulary as the redrawn right-facing ones: shade strands instead of deep, a single highlight; checked on the turn-around | 0.872 |
| 52 | README: the third run, its two instruments and where the loop converged | 0.872 |
| 53 | all README media regenerated, including the hero loop and the browser captures | 0.872 |
| 54 | final pass over every animation at contact-sheet scale: nothing to fix | 0.872 |
| 55 | snapshot. Three runs: 0.614 → 0.767 (25 steps) → 0.867 (15) → 0.872 (15); ceiling for this palette 0.926, the rest is the mockup's wider body | 0.872 |

## Fourth run (steps 56–70): three complaints from the human

"The visor is too low on the side views and needs different heights for different angles. The
collar bends. The shoes are too small."

| step | change | similarity |
|---|---|---|
| 56 | visor heights per angle: profile lens back up to the eye's middle row (as in the mockup, which has it a row higher in profile than from the front); the 3/4-back tip with it | 0.872 |
| 57 | collar: the `edge` against the neck followed the neck's U-shaped boundary (a curved band from behind, a W in front with the flaps and tips); now one straight `rows` band across the torso's top row, and the zipper rules notch it open at the front. Neck flaps and corner tips dropped | 0.873 |
| 58 | new rule type `grow`: pushes a part's outline outward into transparent pixels on given sides, moving the edge and filling behind it, and grows the frame's labels so later rules see the bigger part. The sneakers are one pixel wider on both sides (three instead of two in the front view) | 0.873 |
| 59 | 3/4 lens one row up as well (front 11, 3/4 10, profile 10 in grid rows): the front keeps its brow row, the angled views sit at eye level | 0.872 |
| 60 | snapshot; walk, run, jump, attack and interact at 6× with the grown feet: no artifacts | 0.872 |
| 61 | side view text check after the visor move: the 0.005 slip is the eye rows, not a misplacement | 0.872 |
| 62 | profile zipper `straight = true`: one vertical line from the collar instead of following the torso's contour | 0.872 |
| 63 | feet at 28×: each shoe is white with orange caps flanking a white middle pixel, as in the mockup | 0.872 |
| 64 | a straight bottom-row hem was tried and rejected: it drops pixels wherever the torso ends diagonally (3/4, walk) | 0.872 |
| 65 | snapshot | 0.872 |
| 66 | README and notes | 0.872 |
| 67 | playground smoke test with the wider feet | 0.872 |
| 68 | all README media regenerated | 0.872 |
| 69 | final animation pass | 0.872 |
| 70 | snapshot | 0.872 |


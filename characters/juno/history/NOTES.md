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
| 25 | stubble continues down the temple beside the visor to the ear; the 3/4-left lens re-anchored to the front of the face (step 23 had trimmed the wrong end there; flagged by the human watching) | 0.768 |

# nyx iteration log

| step | change | similarity |
|---|---|---|
| 0 | skeleton | 0.4552 |
| 1 | palette refit from --hex, parts: leg_l chrome, mask ramp | 0.6394 |
| 2 | all head grids drafted: --draft-grid all --all-slots --clean --apply, mask legend m/M | 0.8603 |
| 3 | hair.dark (d) and skin.dark (z) slots for the cells the draft could not reach; re-draft all | 0.8628 |
| 4 | library rules scored per view with --try: open-coat strip, lapels, coat skirt and hem from behind, pockets, sleeve ends, cuffs, shoulder seam, back emblem, profile piping and back fold, knee seam | 0.8948 |
| 5 | chrome ramp: shade is the shin's colour (legs carry shade+ink only), ink the outline; re-draft down_side_l after the placement moved | 0.8991 |
| 6 | silhouette from --widths via --try: far-shoulder grow n=3 in 3/4 front, sleeves shrunk from behind, far toe row up_side_l | 0.9032 |
| 7 | boots: grey upper column (each), lime lace on the right boot, chrome into foot_l's top row; knee seam in down_side; skin hands back from behind | 0.9079 |
| 8 | lime hem across the pocketed hands' last row (3/4 front, profile; anims limited) and the legs' first row in profile; shoulder seam front only (--ablate) | 0.9102 |
| 9 | profile piping and hem excluded from the attack (hook in the spin); --optimize: jacket.shade +4 toward base (flat fabric), jacket.ink a step lighter than the outline | 0.9114 |
| 10 | revert --optimize (ceiling rose more than score); sweep picks judged on crops: sleeve-end shadow, pocket slit column, right hand's tucked edge (anims limited), shin's dark back seam in profile | 0.9124 |
| 11 | --fit-grid on seven views (--apply, run in the background, ~1 min per view): fills '.' cells the draft left inside the heads | 0.9151 |
| 12 | profile hems on the legs limited to idle/walk/rotate/interact (lime bars along the thighs in run and jump); side_l hem split into its own rule for that | 0.9151 |

# Agent log: what worked, what did not (run 3, goal 3% below the ceiling, 30 steps at most)

One line per observation, prefixed with the step number. Written by the agent as it goes:
every place the skill, the skeleton, the rule library, a tool or a rule was right, wrong,
missing, misleading or still specific to one character.


## Phase 0: setup and palette (steps 0-1)

- 0: skeleton copied, `name` set; score 0.4589, ceiling on the skeleton palette 0.7314. SKILL.md says "0.64 on a palette that fits, 0.41 on one that does not": consistent (Juno's placeholders do not fit).
- 0: the tool numbers the first `just step` as step 0; the brief's budget counts calls. Minor, but "30 steps" vs step numbers 0..29 is ambiguous; I count calls.
- 1: `--init-palette` before any grid: EVERY row was marked `~` (wide) on this mockup (coat + open tee + piping on `body`, boots near the outline colour, chrome + lime seam on leg_l). It gave nothing usable; `--hex` over a whole view (front, back, profile) was what worked, in three calls. The skill's order "`--hex` on flat areas, then `--init-palette`" undersells how often `--init-palette` is useless on a trimmed design.
- 1: `--hex VIEW y0,y1,x0,x1` ranges are end-exclusive (asked 5,31,8,23 got rows 5..30, cols 8..22); the doc does not say so.
- 1: skeleton's `visor` ramp comment "eyewear rims; delete if the design has none" and the commented `mask` example were right for this design; I added `mask` and legend letters m/M (mask), c (coat collar), t (lime). lint's info on "in no class" is clear and correct.
- 1: palette refit alone: 0.4573 -> 0.6380; ceiling 0.9385 (goal line 0.9103, my target 0.9113 with margin).

## Phase 1: head grids (steps 2-3)

- 2: `--draft-grid all --all-slots --clean --apply` in one command: 0.6380 -> 0.8610 (compare's own print); `just step` right after scored 0.8634. The compare print and the step differ by 0.0024 for the same recipe (side 0.8771 vs 0.8853): the print after `--apply` seems to be taken before the second pass or with the old placement. Misleading when judging the command.
- 2: `--clean` skipped its speckle and last-row pass in EVERY view (-0.006 to -0.018 each): on this platinum hair the passes never pay. Consistent with run 1's finding; the SKILL's "cleans what cleaning does not cost" is accurate, but `--clean` is effectively a no-op on textured light hair and the print is 16 lines of "skipped".
- 2: `--all-slots` added seven hex literals: three chrome slots (C, I, a) for the hair's cool grey shadows, pants.base (p) for a brown skin shadow at the ear/nape, visor.shade, glow.shade, jacket.shade. The chrome/pants names in the comments are misleading to a reader ("chrome.base at draft time" inside platinum hair); they are just the nearest greys/browns. Works as documented (no coupling), but the legend now has "chrome" in the hair.
- 2: the "N cells have no legend colour within reach (median #d6c8b7): a slot the palette lacks (a shadowed nape, a strap)" hint was right and useful: it was the platinum mid-tone. `hair.light` in the skeleton was ~= base on this design, so I repurposed it as the mid-tone (#d7cab9): +0.0010 score and +0.0011 ceiling (gap unchanged, palette truer). The hint's examples ("a shadowed nape, a strap") are Juno/Nyx-specific wording but harmless.
- 2: `just step` after the first draft said "placement moved since the last step in down_side, side, side_l" - compared against step 1 which had NO grids. A re-draft of those three gave +0.0003: the warning is technically true but trivially so right after the first draft (the tool should not compare against a grid-less step).
- 3: ceiling 0.9396, goal line 0.9114; my target 0.9124.
- 3: heads at 24x in `just review` look right from all eight sides: goggles on the eye row, mask below, collar with lime piping in the last rows. No hand edits needed. Phase 1 = 2 steps.

## Phase 2: body (steps 4-)

- 4: `--init-palette` was useless, but `--labels` + `--text` + `--hex` read the design in three calls: tee rows/belt row/pants strip, lime sleeve bands, back hem on the first leg row, emblem. The library's open-coat strip (offsets [-2,-1,0,1], top 4 / skip 4 top 1 / skip 5) transferred UNCHANGED from runs 1-2 and gained +0.0145 (down +0.047). Back hem rows +0.0078, sleeve shrink from behind +0.0037, 3/4 front torso grows +0.0023, back emblem +0.0013. All five per-view scored in one call with a variant script (`--recipe`); total step 4: 0.8644 -> 0.8954.
- 4: I wrote a 20-line helper (insert rules into a copy, score, print per-view deltas vs the recipe). Every run re-writes this; `compare --try 'TOML rules'` (or `--recipe` accepting a rules-only snippet appended to the current recipe) would save each run the script. The playbook's "per-view scoring" method has no tool of its own.
- 4: `just step` said down_side_l's placement moved (after the torso grow); the single-view re-draft gave +0.0080 there. The warning was right.
- 4: `just crops NAME --box 17,31` shows the render and variants but NOT the mockup: judging "looks right" means opening `NAME_compare.png` separately and matching scales by eye. A mockup row in `crops` is the missing half of the judge.
- 5: `--sweep 30` (10 s) put one feature in all 30 slots: the hands (coat skirt over the hand in 3/4 and profile). Same-colour collapsing does not merge near-identical colours (outline.base, shoes.base, near-black) nor sub-parts (hands, hand_l, hand_r) nor rule shapes that do the same thing (region back n=1 vs shrink back), so the top 30 held ~3 ideas. Grouping by (part group, feature) and showing the best colour per group would make 30 lines say 30 things.
- 5: hand hem (lime on the hand's bottom row) in down_side/side/side_l/down_side_l, coat hand in side, knee seam row on leg_l: 0.8964 -> 0.9015.
- 5: `just step` then said "placement moved in side: re-draft". I did (single view, as the SKILL says): side 0.9043 -> 0.8986 (-0.0057). The re-draft shifted the whole side grid down one row and dropped the collar row. Restored from step-05.toml. So the warning's advice is right after a grow (step 4) and wrong here; the SKILL states it as a rule ("re-draft THAT view then"). It should say: re-draft on a copy and keep only if it scores.
- 6: `--fit` medians suggested four slot moves with readings (boots lighter, coat shade lighter, pants darker, coat ink lighter): individually -0.0005, +0.0005, -0.0003, -0.0024. Boots only gained once the grey had STRUCTURE (a lacing column per boot), with the grey put in the unused `shoes.light` slot. The pitfall "medians mislead where structure is off" held exactly.
- 6: a `stripe` on a GROUP part (`feet`) takes one median column for the whole group: it painted between the two feet (+0.0005 vs +0.0026 for one rule per foot). Neither the library nor the rule docs say that a stripe on a group is one stripe; the sweep's candidate list includes `stripe part=feet` shapes that can never mean "each foot".
- 6: far sleeve + hand grow in down_side_l (`grow arm_r front 2`, `grow hand_r front 2`): +0.0081 there; its twin `arm_l` in down_side only +0.0014 (the far-shoulder torso grow already covers it). The library's "far sleeve" entry (Juno, arm_l in down_side) was right for the OTHER 3/4 view on this mockup - consistent with the library's own caveat.
- 6: step 6: 0.9069.
- 7: in front, every treatment of the template's hands (coat + hem, clear, arm row as hand) lost 0.003-0.006, though the mockup's hands are one row higher and one pixel wide. The score keeps the template's hands; I did too.
- 7: front lapel edges: strip offsets [-2, 1] top 4 dark: +0.0030 in down, lost in both 3/4 fronts. The library's open-coat strip could note "the outer strip columns are the lapels' dark inner edge in front".
- 7: `--fit-grid` on all eight drafted grids found +0.0033 mean (side_l +0.010): holes left as `.` (template skin showing through the hair/mask) and outline cells closing the mask's edge. The SKILL/playbook say fit-grid "finds nothing" on a drafted grid; it does when `--clean` skipped every pass. `--fit-grid all` prints NOTHING (silently; `--draft-grid all` works); I named the views. No `--apply`: I wrote a script to merge the grids, skipping the last row (body cells).
- 7: lint false positive: "rule 17 (region hands): a one-sided part with a front/back side lists both a facing and its mirror" - `hands` is both hands, not one-sided. Reported to team-lead.
- 7: step 7: 0.9101, goal line 0.9116 (target with margin 0.9126). Phase 2 so far = steps 4-7 (4 steps).
- 8: sweep 3 (current recipe) had nothing above +0.0013 "if limited"; three picks with a reading (chrome into the cyber-leg's boot top, dark shin back edge in profile, the sleeve's dark end on arm_r) gave +0.0030 together, confirmed on `crops --diff`. REACHED +0.0016. Tool fixes landed during the run (lint group check, `--fit-grid all`/`--apply`, score-gated re-draft, `--try FILE`); step 8 was scored on the fixed code and lint's false positive was gone.
- 9: review found the grown far hand in down_side_l as a 4-pixel tan bar (the mockup's is 2): grow n=1 costs 0.0002, and a lime band at 0.3 on the far sleeve pays +0.0023 there. `--try` only appends rules; changing an existing rule's parameter still needs a copied file.
- 9: a single off-palette pixel (#2f2522, `?` in the fit table) was the template's hand ink: the skeleton's skin ramp has no `ink` slot. `skin.ink` = outline colour: score-neutral, one less stray colour. The skeleton could ship `ink` on skin.
- 10: review found NO hands from straight behind: `shrink arms+hands` (library, Nyx) narrows the two-pixel hands to one pixel, which the shrink then inks. Skin on the arm's last row in `up`: +0.0047 there. The library's shrink entry should warn that it erases the hands in that view.
- 10: REACHED +0.0024 (0.9140 vs 0.9116), `--split` 0.998-1.000, `--hot 20` scattered singles at ~1.1, lint clean (one info), smoke PASS, turntable built.

## Final (step 10 of 30; 11 `just step` calls)

| view | down | down_side | side | up_side | up | up_side_l | side_l | down_side_l | mean |
|---|---|---|---|---|---|---|---|---|---|
| score | 0.9296 | 0.9131 | 0.9131 | 0.9093 | 0.9202 | 0.9219 | 0.8992 | 0.9053 | 0.9140 |
| ceiling | 0.9509 | 0.9461 | 0.9433 | 0.9328 | 0.9341 | 0.9401 | 0.9291 | 0.9415 | 0.9397 |

Gap 2.73% below the ceiling (goal 3%, margin +0.0024). Steps per phase: palette 2 (0-1), grids 2 (2-3), body 4 (4-7), last thousandths + review fixes 3 (8-10).

What still looks off to a person, accepted: in front the template's hands are 2-pixel tan blocks at the hips (the mockup's are 1 pixel and a row higher; every treatment lost 0.003-0.006 and there is no rule to move a hand up a row); the right profile's head has the mockup's own grey strap patch; the back emblem is a 2-pixel bar where the concept has a winged mark.

What the recipe format could not express: moving a part (the front hands one row up); a stripe per member of a group (one per foot needed two rules); a rule that differs in one parameter per facing other than `offset(s)` (the sleeve band's `at`, the grow's `n`); "the hands inside the coat" as one concept (it took hand rules with `anims` in four facings).

## After the run: the fixes that landed, checked on copies (no step taken)

- `stripe part="feet" each=true` in place of the two per-foot rules: identical in six views; up_side -0.0009 and up -0.0010 only because my foot_l rule had a facings list that `each` does not have (mean 0.9137 vs 0.9140). The fix does what it says. The recipe keeps the two rules.
- `--fit-grid all` now traces every view: on the finished grids it finds down_side +0.0008, side +0.0013, down_side_l +0.0009 (mean +0.0004). Not applied: the run is done and the goal is met with margin.
- `--try FILE` would have replaced my private helper for steps 4-10; it still cannot change an existing rule's parameter (the step-9 grow n=2 -> 1 needed a copied file).

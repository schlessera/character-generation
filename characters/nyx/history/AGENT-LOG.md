# Agent log: what worked, what did not (run 1, goal 3% below the ceiling, 30 steps at most)

One line per observation, prefixed with the step number. Written by the agent as it goes:
every place the skill, the skeleton, a tool or a rule was right, wrong, missing or Juno-specific.


## Run log

- 0: the task says to message "main" about blockers; the team config has only "team-lead" and this agent. Messages go to team-lead.
- 0: skeleton copied, name set. `just step` numbers the first call "step 0" (snapshot step-00.toml); the budget counts calls, so step N here is budget call N+1.
- 0: skeleton score 0.4084, ceiling 0.7401 (Juno's palette quantizes this mockup badly). The skill's "about 0.64" for the skeleton is Juno's palette on Juno's mockup; on another design the skeleton starts at 0.41.
- 0: `lint` with no grids prints the fix as `--draft-grid all --clean --apply --mirror-swap`: `--mirror-swap` is Juno's one-sided undercut; for a symmetric cut (and with an eight-view mockup, where the SKILL says it does nothing) it should not be in the suggested command. chargen lint message.
- 0: the brief says goggles pushed up on the forehead; the mockup paints the lime lenses at eye level over the eyes (front, 3/4, profile). The mockup is the reference; the grids follow it.
- 0: BUG (reported to team-lead): `similarity()`/`cost_maps()` in chargen/mockup.py shift the placed mockup with `np.roll`; with the render's feet on row 31 and a best shift of dy=+1 the mockup's sole row wraps to row 0 (`--text down` shows the boots at row 0, rows 1-4 empty). Every view pays for an unmatched sole row. Fix: a zero-filled shift.
- 0: `--text` legend shows `f` for two colours: fx ramp `f=#8ff8ff` and the legend's `f=visor.shade`. The ramp-letter assignment does not avoid the legend's `f`.
- 0: `--init-palette` groups by the skeleton's `[parts]` (Juno's `arm_r+hand_r` chrome arm, `hand_l` skin) and its medians are nearly all `~`: the mockup is 2 px narrower than the template from the front, so the edge rows are mostly outline/background drift. Useful only after `[parts]` is refit; a raw most-common-colour count over `mockup.extract` was the faster read.
- 0: `clean_grid`/`mirror_grid` (chargen/mockup.py) hard-code the legend: hair = `kbHDi` (HAIR), stubble = `uUw`, lens = `v`, rim = any legend entry whose ramp starts with `visor`, lens caps = `x`. A new design must reuse exactly these characters for its hair and its eyewear, and must NOT put a second dark material (Nyx's respirator mask) on the `visor` ramp, or `--clean` rewrites it as hair outside the lens rows. Nothing in the skill or skeleton says the characters are load-bearing; the skeleton's legend comment should say so.
- 1: `--draft-grid all --clean --apply` (no --mirror-swap: eight views, symmetric cut) took the mean from 0.4084 (Juno palette) / ~0.41 to 0.8402 in one command, with no trim rules at all. The drafted heads read as Nyx from all eight sides, the three left views included (they are drafted from their own mockup views, not mirrored). The one-command claim holds; the "past the 3% goal" claim does not (the body has nothing).
- 2: the open-coat front (stripes tee/belt/pants), sleeve bands, back collar, coat over the thighs from behind: 0.8402 -> 0.8687. Front view alone 0.846 -> 0.916.
- 2: while I worked the main session fixed the np.roll wrap (zero-filled `_shift`) and added `[head.classes]` (hair/texture/lens/rim/caps characters per recipe). Declared Nyx's: texture = "" (no shaved side), rim = "x".
- 3: `--clean` COSTS 0.0075 on Nyx: raw drafts 0.8770, cleaned 0.8695. Measured apart: the speckle pass costs 0.0070 (it flattens the platinum hair's grey strand pixels H/i/D into b: on spiky light hair the "speckles" are the texture the mockup paints), the last-row pass 0.0003. Looked at the raw heads at 24x: they read as spiky hair, not noise. The skill says `--clean` always; for a textured light hair it should be tried both ways (or the speckle pass limited to characters that are not hair shades).
- 3: the last-row pass drops the mask's bottom row (M/m/n) and the lime collar dots: on Nyx the respirator reaches below the template's jaw. Negligible for the score, so kept.
- 3: re-drafting after the body rules (the "draft twice" advice): +0.0008 with clean, so placement barely moved; the raw-vs-clean difference was the real finding.
- 4: `--widths` found what the skeleton's 3/4 grows are for, but with an EIGHT-view mockup the left 3/4 views need their own grows: down_side_l is +3 on its front side just like down_side (the far shoulder is not one-sided). The skeleton and playbook say "no `_l` twins on any of these" (true for Juno's five views, where the left views were mirrored and unscored); for eight views the rule is "grow what `--widths` shows per view", and in the mirrored frame the far arm is labelled arm_r. Grows: +0.0044 (down_side +0.019, down_side_l +0.014).
- 4: the skeleton's `grow arm_l front n=2` for the far sleeve in down_side scores worse (+0.0002 when removed) on Nyx; its twin on arm_r in down_side_l gains 0.0014.
- 4: new need: a grow for the far boot's toe row (`grow feet down` in the 3/4 views): the template draws only the near foot on row 31 in the 3/4 views, the mockup has both boots there (+3/+4).
- 5: the skeleton's single `band arms at 0.5` sleeve trim is wrong from behind on Nyx (the mockup has no band in `up`) and one-armed in the 3/4 back views: arm_r in up_side, arm_l in up_side_l (the same screen arm, mirrored labels). Scoring one variant across all eight views gives per-facing answers in one call, because each view only sees its own facing's rules: that trick found the right facings for five rules at once (step 6). Worth a line in the playbook.
- 5: a back emblem as two `band torso anchor=center` pixels: without `straight = true` it is a diagonal slash in 3/4 back (each row takes its own centre); with it a vertical bar. Same score, better picture.
- 6: per-facing choices by that method: coat collar over the neck from the side and behind (+3 per view), sleeves over the hands where the mockup shows none (the concept's hands-in-pockets), lime hem row in side_l/up, boots one row up in side_l/down_side_l: +0.0038.
- 7: RULE PITFALL (reported): `stripe` with `straight = true` and `top = N` takes the median centre of the first N rows only (`rows = ...[:top]` before the median in `_rule_mask`), so stripes that are meant to form one strip (the tee over 4 rows, the belt over 5, the pants over all) land in different columns as soon as a grow widens the top rows. On Nyx the 3/4 far-shoulder grow put the tee one column beside the pants strip, with an olive column running up to the collar. Worked around by ordering that grow after the stripes (+0.006 on down_side_l); the playbook's "grow rules go first" is not always right. Fix in the tool: compute the straight column over all the part's rows and apply `top` afterwards (or an explicit `column_from = "part"`).
- 8: second harvest (one pertest pass, 25 candidates): profile collar row + front piping (the skeleton's profile zipper rule is right for a coat too), dark sleeve end in 3/4 back, chrome foot column where the mockup paints the cyber-leg to the ground (no boot on that side), shin highlight, lime laces: +0.0043. Most skeleton-style candidates (flank shade, arm seam, collar row in front, cuff bands at other heights) scored worse on Nyx.
- 9: `[outline] keep` = every legend character (+0.0005): the drafted grid already contains the mockup's own outline cells, so repainting its edge cells with the outline colour only loses. The skeleton's `keep = "kSs"` is a hand-drawn-grid setting.
- 9: the legend needs every material the mockup draws inside the grid's rows, not only the head's: Nyx's coat collar reaches into the head's last two rows and, with no coat colour in the legend, the draft painted it mask-grey. Adding `c/C = jacket` and re-drafting: +0.0014, and the collar now reads (indigo with lime lapels). The skill says nothing about this; the draft only knows legend colours.
- 9: with the coat in the legend the last-row clean now costs in 7 of 8 views (the last row IS the collar); kept only for `up`.
- 10: extending the legend with every palette slot the mockup paints on or beside the head (skin light/blush, coat light, tee, lime, lens highlight) and re-drafting: +0.0019. The draft picks legend colours only while `--ceiling` quantizes to every slot, so a short legend is a built-in gap to the ceiling. `--draft-grid` could offer all palette slots (auto-adding legend chars), or the skill should say "legend = every slot that appears in the head rows".
- 11: MISSING MECHANISM, worked around: the recipe format has `grow` but no shrink, and the skill says "rules can grow a part outward but nothing can shrink the mannequin". Nyx's mockup is 2 px narrower at the arms from behind. `color = "clear"` (a legend value that also works in rules, undocumented) erases pixels, so a shrink is two rules: `region part anchor SIDE n=2 ink=true color=outline.base`, then `edge part touching="none" sides=[SIDE] ink=true color="clear"`. The edge form only clears silhouette pixels, so an arm crossing the torso in an animation never gets a hole (a `region n=1 clear` would punch one). Per-side choices by score, mirror-consistent: up both, up_side left, up_side_l right: +0.0033. Walk/run/jump/attack checked in review: clean. A `shrink` rule type (the inverse of grow, re-outlining the new edge) would make this one rule and discoverable.
- 11: the 3/4 front far-sleeve grow (skeleton) re-tested after the other changes: still negative on down/side; `grow legs front n=2` (coat skirt over the far leg) +0.004 in down_side_l only, not taken yet.
- 12: second shrink pass (edge-safe form, every part x side scored per view): the profile coat's back edge (+8 thousandths on side), the hands' left edge in three views. REJECTED a score gain: shrinking the legs' front edge in `side` scored +3.8 thousandths and erased the chrome shin and its knee seam from the profile, the one-sided feature this character is about. Also rejected: a head shrink (the grids paint on '.'-labelled cells, so an edge test on labels would treat drafted hair as empty and clear head pixels next to it).
- 13: re-draft after the shrinks improved only the profile grid (+3 thousandths there, the others equal or worse): take grids per view, not all. Optimizer: two moves with a reading (coat fold lines lighter than the outline, tee shade darker under the coat): mean +0.0014, ceiling +0.0015, gap -0.0004. As the skill says, palette moves mostly lift the ceiling too.
- 14: a sweep of 700 simple rule shapes (14 parts x 5 shapes x 10 colours, each scored across the eight views in two minutes on 12 threads) found five per-facing trims with a reading (lime cuffs at the sleeve ends in profile, grey soles from 3/4 back, lime piping on the far skirt edge, a shoulder seam in front): +0.0031, goal REACHED at step 14 (0.9074, ceiling 0.9352, line 0.9071). The skill has `--ablate` (remove each rule) but no forward search; with eight views the per-view deltas make a forward sweep cheap and each pick checkable. Every pick was looked at in the crops before stepping; a score-only pick without a reading would have been refused.
- 15: GENERATOR DEFECT (reported): `_grow` moves an edge ink pixel outward and fills the vacated pixel with `color` at base tone. At a CORNER the vacated pixel is still on the silhouette in the other direction, so it ends up a coloured, unoutlined edge pixel (the outline pass only repaints ink-tone pixels). `grow torso sides=["up"]` (the skeleton's "square bomber shoulders", in every facing) produces exactly this at both shoulder corners; on Nyx it showed from behind as indigo pixels outside the outline, next to the narrowed sleeves. Found only in the 12x back view, not by any number. Removed the two shoulder grows (worth 0.0002); goal still REACHED at 0.9072. Fix: in `_grow`, keep the vacated pixel ink if it still touches transparency after the move, or have the outline pass take the silhouette from the final alpha.
- 16: the main session's live fixes (grow keeps a vacated corner as outline, a `shrink` rule type, the straight-stripe median over all rows) changed the render under the recipe: step 15's 0.9072 re-scored 0.9067, short by 0.0004. A goal met by +0.0001 is not robust to a generator fix; this is worth a line in the skill ("leave margin, re-score after tool changes"). Re-based: my two-rule shrinks became `shrink` rules, the collar grows came back (now clean at the corners), the profile coat-back shrink was dropped on sight (it turned the coat's back into a black column; it was part of the 0.9072), and a second sweep (924 candidates incl. grow/shrink per part and side) gave four picks with a reading. 0.9081, REACHED (+0.0010).
- 16: NEW `shrink` DEFECT (reported): it inks only the pixel behind in the shrink direction. (a) `shrink arms sides=["up"]` after sideways shrinks cascades down the sleeve's stair-step edge and exposes pixels sideways with no outline (rows 23 and 25 of `up`, seen at 12x); dropped that rule (+0.0004). (b) shrinking a two-pixel-wide row from both sides deletes it and leaves the pixel above it as an unoutlined bottom edge (the hands' bottom row from behind: one skin pixel each, kept, it resembles the template's own hand edges). Fix: after erasing, ink every remaining part pixel that became a silhouette edge in any direction.
- 16: the grow-corner fix also means `grow torso sides=["left","right"]` in `up` scores exactly nothing now (to four decimals) and draws shoulder boards next to the narrowed sleeves: kept only `sides = ["up"]` from behind.
- 17: the shrink fix (outline the whole new silhouette) landed during the finish: `up` 0.9166 -> 0.9120 (the hands from behind are now dark sleeve ends, which suits the hands-in-pockets reading), mean 0.9075, still REACHED (+0.0004). The sleeve-top shrink I had dropped for its holes is now clean but scores 0.0001 worse: left out.

## Final (run 1)

Result: goal REACHED at step 17 (18 of 30 budget calls): mean 0.9075, ceiling 0.9352, line 0.9071, gap 2.96%.
Per view: down 0.9343, down_side 0.9050, side 0.9036, up_side 0.9016, up 0.9120, up_side_l 0.9139, side_l 0.8952,
down_side_l 0.8946. Silhouettes 0.998-1.000 in every view (`--split`). `just lint nyx`: one info line (the mask and
coat legend characters are in no head class, as intended). `just smoke`: 13 PASS, no page errors. Turntable:
build/preview/nyx_turntable.gif. First passed at step 14 (0.9074) and again at 15; the generator fixes that landed
during the run re-scored that recipe at 0.9067, so it was re-based (step 16) and re-scored once more after the shrink fix (step 17).

Where the steps went: 1 palette + one-command drafts (0.41 -> 0.84); 2-3 the open coat and the unclean drafts (0.877);
4-7 grows per view, per-facing rule choices, the stripe/grow order (0.889); 8-10 harvested trims, legend = every
slot on the head (0.897); 11-13 shrink via clear, re-draft per grid, two optimizer moves (0.904); 14 a 700-candidate
sweep (0.907); 15-17 visual fixes and re-basing on the generator fixes.

Known, accepted: in attack/down frames 2 and 4 the spinning body takes the profile-left facing and its lime cuff,
piping and hem stack into a hook and a Z (a rule cannot be limited to an animation); single dark strap pixels in the
back of the hair (copied from the mockup); one skin pixel at each hand's bottom edge from 3/4 back (the template's
own hand edge).

### Findings, grouped

(a) Juno-specific encodings in the skill and skeleton
- SKILL.md: "the skeleton plus one --draft-grid all reaches 0.90 / past the 3% goal". On a different design the
  one command gives 0.84 with no body rules; the skeleton's rules had to be rewritten, not verified.
- SKILL.md / playbook: "`--clean` always". Its speckle pass cost 0.007 on light spiky hair (the grey strands are
  the texture); its last-row pass deletes the collar once the coat is in the legend. Gate both, measure both.
- Skeleton legend: hair/texture/lens/rim characters were load-bearing for `--clean` (fixed live: [head.classes]),
  and the legend holds only head materials; the draft needs every slot the mockup paints in the grid's rows (coat
  collar, tee, lime, skin light/blush): +0.0033.
- Skeleton `[outline] keep = "kSs"`: right for hand-drawn grids; drafted grids carry the mockup's own outline, keep
  every legend char (+0.0005).
- Skeleton/playbook "no `_l` twins on grows": true for five-view mockups; with eight views the left 3/4 views need
  their own grows (the far shoulder is not one-sided), and the far arm is arm_r in the mirrored frame.
- Skeleton `band arms at 0.5` sleeve trim, collar row in front, flank shade, arm seam, far-sleeve grow in down_side,
  sneaker caps, high-top row: all scored worse on Nyx or needed per-facing lists; the per-view candidate scoring
  (one variant, eight deltas) found the right facings in one call each.
- Skeleton "square bomber shoulders" `grow torso up` in every facing: produced unoutlined corners (fixed live);
  sideways in `up` it scored nothing and drew shoulder boards.
- Playbook "grow rules go first": wrong with `straight` + `top` stripes (fixed live in the tool).
- SKILL.md "nothing can shrink the mannequin": `color = "clear"` could (now a `shrink` rule).

(b) Tool bugs and misleading output (all reported; most fixed during the run)
- `similarity`/`cost_maps` np.roll wrapped the sole row to row 0 (fixed).
- `--text` legend printed `f` for two colours (fx ramp and visor.shade).
- lint's no-grids message suggested `--mirror-swap` for any character (fixed).
- `stripe straight` + `top` took the median of the top rows only (fixed).
- `grow` left unoutlined corners (fixed); `shrink` v1 left unoutlined sideways exposures and deleted thin rows (fixed).
- `--init-palette` groups by the skeleton's [parts] (Juno's arm), so on a new design it reads the wrong parts.
- A goal met by +0.0001 flipped to short after a generator fix: the goal line needs margin.

(c) Mechanisms the recipe format lacks
- A coat hem that falls on the legs: expressed as `rows legs from top` in jacket + trim from behind, stripes in
  front; works, but the coat cannot hang BESIDE the legs (the template has no pixels there) except by `grow legs`.
- Stripes have `top` but no `bottom`/`skip`: the open coat's lower part needed "paint all, overpaint from the top".
- No rule filter by animation (the attack's spinning frames take profile trim).
- No forward rule search: `--ablate` removes rules; a sweep that adds shapes per part x facing found +0.006 of
  checkable picks. Worth a `--sweep` flag with per-view deltas.
- The one-sided cyber-shin needed nothing: `leg_l = "chrome"` in [parts] follows the labels through the mirror.

(d) What worked as documented
- The eight-view mockup: every view drafted from its own image, no mirroring, all scored.
- `--draft-grid all --apply` (twice): the heads read as the character from all eight sides on the first try.
- `--widths` (grow only for 2+), `--split`, `--slack`, `--oracle`, `--hot`, `--ablate`, `--recipe` variants,
  `just crops --diff`: all as described; the crops diff caught every visual regression the score missed.
- `--optimize`: moves with a reading, and as warned they lift the ceiling as much as the score.
- `just step` notes and snapshots, `just review`, `just turntable`, `just smoke`.

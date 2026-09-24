# Nyx: the round-trips

Each round: a fresh Opus 5.5 subagent builds `recipe.toml` from the skill alone (no access to
Juno's, replica's or the earlier runs' recipes), goal 3% below the palette ceiling or 30 steps;
the main session (Fable 5.1) watches its log, fixes tooling live, then revises the skill and
relaunches. Per round: `history-runN/` (NOTES.md, AGENT-LOG.md, snapshots, `final.toml`,
`turntable.gif`, `review.png`).

| run | skill | steps used | final mean | ceiling | gap | reached at | what it taught |
|---|---|---|---|---|---|---|---|
| 1 | v1 (Juno's skeleton, five-view assumptions) + eight-view compare | 18 of 30 | 0.9075 | 0.9352 | 2.96% | step 14 (re-based twice on generator fixes: 15, 17) | the skeleton's rules were Juno's design, not a structure ("verify" became "rewrite"); `--clean` cost on textured light hair; the legend must hold every material in the head's rows; six generator/metric defects (np.roll wrap, straight-stripe median, grow corners, no shrink, letter collision, lint's flag) found by one agent reading its own text views; a forward sweep of rule shapes found the last +0.006 |

| 2 | v2 (structure-only skeleton, rule library, --all-slots, --sweep, shrink) | 14 of 30 | 0.9138 | 0.9385 | 2.63% | step 8 (thin), step 10 with margin | `--all-slots` coupled grids to body ramps (twice poisoned a palette experiment); the library's facing lists are one mockup's answers; a coat rule on a hand swings with the arm (needs `anims`); the placement moves after a grow and the grid should be re-drafted then; no labels view for the body; the open-coat strip wanted per-facing offsets |

| 3 | v3 (hex-literal legend letters, --labels, per-facing offsets, placement warning) | 11 of 30 | 0.9140 | 0.9397 | 2.73% | step 8 (+0.0016) | the library's open-coat strip transferred unchanged (+0.0145); a re-draft after a hand rule cost 0.006 (the tool now keeps a re-draft only where it scores); lint misfired on symmetric groups; `--fit-grid all` was silent and paid +0.003 on uncleaned drafts; a stripe on a group is one stripe (`each`); parameters other than offset wanted per-facing values (`per_facing`); the back shrink erased the hands; no way to move a part (`shift`) |

| 4 | v4 (--try, per_facing, each, shift, gated re-draft, crops mockup row) | 13 of 30 | 0.9151 | 0.9380 | 2.44% | step 8 (+0.0004), step 10 with margin | `--try` on 21 library lines answered phase 2 in one call (+0.032); the library's `;` snippets were not TOML (the loader accepts them now); grows must be scored before the trim (--try does); the draft leaves `.` cells inside the head that `--fit-grid all` fills (+0.003, now in step 1, parallel); `--optimize` lifted the ceiling more than the score (it prints the net margin now); chrome on a leg lives in `shade`; leg rules that depict the coat swing in the run |

| 5 | v5 (--try limited columns and before, parallel fit-grid, optimize net margin, `just grid`) | 9 of 30 | 0.9084 | 0.9340 | 2.74% | step 5 (+0.0014) | one `--try` of 33 library lines written without facings did phase 2 in one call (+0.037 summed); the library's facing lists were wrong for a third of the rules again; the pocket rule must precede the hem-over-hands row; `--ablate` wanted per-view gains; `band` had no `n`/`w`; profile trim always needs `anims` without attack; `--optimize`'s net-margin column made the refusal a one-line decision |

## Revision after run 5 (skill v6, not yet replayed)

Tooling: `--try` candidates take `before = N`; `--ablate` per view; a refused re-draft silences
the placement warning; `band` takes `n` rows and `w` columns; lint warns on keys a rule type
ignores; `--all-slots` letters from a class's ramp join that class.
Skill: `assets/try-library.toml` (every library rule without facings) and step 2 built around
it; a rule-key table in the library; profile-trim snippets carry `anims` without attack; pocket
rule before the hem-over-hands row; the per-hand dark column; skeleton notes on neck, hands,
chrome on a leg, the dead `o` letter.

## Preliminary findings after five rounds (2026-09-24)

**F1. The skill was Juno's recipe in disguise.** Run 1 started at 0.41 with Juno's palette and
had to rewrite every rule; the skeleton's rules, its legend letters (hard-coded in the cleanup),
its `[outline] keep`, its "no `_l` twins" advice and its 0.90-in-one-command claim were all
five-view, one-character facts. The fix that held was structural: a skeleton with no rules, a
rule library per garment feature with both characters' answers, and every "answer" reframed as a
candidate to score per view.

**F2. Steps to the goal: 18 → 14 → 11 → 13 → 9.** Reached at step 14, then 8, 8, 8, 5. Final
gaps 2.96, 2.63, 2.73, 2.44, 2.74% below the ceiling (the ceiling itself moves with each run's
palette: 0.934–0.940). The curve flattened after run 2: what remains is the design's own
distance from the mannequin (the front hands, a 2-px narrower body), not the skill.

**F3. The instruments did the work, not the prose.** Each run's biggest single gains came from a
tool: the one-command draft (+0.22), `--all-slots` (+0.003), `--try` on the library (+0.03 in one
call from run 4), `--fit-grid all` (+0.003), `--sweep` (+0.002–0.006), `--widths` for every
silhouette rule. Nine generator or metric defects were found by agents reading their own text
views (np.roll wrap, straight-stripe median, grow corners, two shrink outline cases, letter
collision, the stale post-apply print, the optimizer leaving moves applied, the `each` mapping).

**F4. Recipe-format gaps closed on the way:** `shrink`, `shift` (with `over`), `each`,
`per_facing`, per-rule `anims`, stripe `offsets`/`skip`/`bottom`, band `n`/`w`, `[head.classes]`,
`keep = "*"`, hex-literal legend letters. Still open: a rule that differs per animation frame
group ("hands inside the coat" as one concept), and the metric's tolerance rewards dithering and
punished an outlined corner the picture needed.

**F5. Eight-view mockups pay.** Every left view scored and drafted from its own image removed the
whole mirror/near-side argument that cost three replica runs; the price is one more finding class
(symmetric features need a rule per 3/4 view, with the mirrored label name).

**F6. Image generation is the weak link.** gpt-image-2 hit the template's pixel scale once in
twelve draws; it anchors on detail, not on a stated pitch, a reference's pixel size or a
mannequin grid (concept/LOG.md). A 2:1 downscale path from a 60-px sheet is untested.

**F7. The goal definition works but is thin at the line.** Three runs first crossed by
+0.0004–0.0008 and were re-scored under the line by a generator fix; the 0.001 margin rule and
the `--optimize` net-margin column came from that. Palette moves are net losses more often than
not once the goal is relative to the ceiling.

## Revision after run 4 (skill v5)

Tooling: the recipe loader and `--try` accept the library's one-line shorthand, TOML errors name
the file; `--try` prints the limited gain, the gaining views and an all-limited row, and scores
grow/shrink/shift before the recipe's rules; `--fit-grid all` runs the views in parallel and
re-scores after `--apply`; `--optimize` prints each move's ceiling delta and net margin;
`just grid NAME VIEW ROW 'text'`; `per_facing` may override `anims`; `build` skips a scratch
recipe; `--all-slots` letters carry a "rename or move it" comment; `--quiet --apply` skips the
grid text.
Skill: step 1 ends with `--fit-grid all --apply`; the whole-view `--hex` box; chrome on a leg;
`--split` is necessary, not sufficient; the sweep's colour is not the depicting ramp; leg rules
that depict the coat need `anims`; a hem across pocketed hands in the library; free-form slot
names in the skeleton.

## Revision after run 3 (skill v4)

Tooling: `--try FILE` (candidate rules scored per view, alone and together); a re-draft over an
existing grid is written only where it scores; the post-apply score is re-read from the file;
the placement warning ignores views without a grid at the previous step; `--fit-grid all` and
`--fit-grid --apply` (last row kept); lint's one-sided check skips groups naming both sides;
`each = true` (a rule per single part of a group; the sweep uses it); `per_facing` parameter
overrides on any rule; a `shift` rule with `over`; `just crops` shows the mockup as its first
row; `--clean`'s print is one short line per skipped view; skin gets an `ink` slot.
Skill: `--hex` ranges end-exclusive and `--init-palette` limits stated; library notes on the
lapel columns, the back shrink and the hands, `each`, `per_facing`, `shift`.

## Revision after run 2 (skill v3)

Tooling: `--all-slots` writes hex literals into the legend (no coupling) and skips near-legend
colours; the draft reports cells with no palette colour within reach (a missing slot);
`stripe` `offsets` list and per-facing tables; `compare --labels VIEW`; `just step` reports
views whose placement moved; `--sweep` collapses same-colour candidates and flags whole-part
repaints; lint's hint has `--all-slots` and ignores literal letters.
Skill: library facing lists framed as candidates; collar-from-behind marked redundant with
drafted grids; grow-before-straight-stripe interaction; `anims` for hand rules that depict the
coat; the placement warning in the workflow; the preview file name; the skeleton's syntax
comment without a literal rules header, with a mask ramp example.

## Revision after run 1 (skill v2 for Nyx-era)

Tooling: zero-filled placement shift; `[head.classes]`; `--clean` passes score-gated per view;
straight-stripe median over all rows; `stripe` `skip`/`bottom`; `shrink` rule; `grow` corner
outline; per-rule `anims`; `[outline] keep = "*"`; `--draft-grid --all-slots`; `--sweep N`;
`--init-palette` grouped by the recipe's parts; thin-margin notice on `--goal`; lint checks rule
types and legend classes; `just turntable`.
Skill: the skeleton is structure only (no rules); `references/rule-library.md` has both
characters' rules per garment feature; SKILL.md's numbers are measured on both mockups; the
playbook has per-view scoring, eight-view grows, the stripe rows, `anims`, margin; pitfalls has
a Nyx section.

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

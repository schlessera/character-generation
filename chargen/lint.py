"""Static checks on a recipe, for the mistake classes that cost iteration steps.

Each finding names the rule or line and says why it matters; `error` means the recipe will
render wrong, `warn` means it very probably does, `info` is worth a look.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .character import FACINGS, HEAD_PAD, Recipe, build_frames
from .labels import GROUPS, PARTS

ONE_SIDED = {"R", "r", "L", "l"}  # arm and hand labels: a left-facing twin puts them on the other edge


def lint(path: Path, tpl) -> list[tuple[str, str]]:
    r = Recipe(path)
    out: list[tuple[str, str]] = []
    data = r.data

    # [parts]: later lines win, so a specific part before a group that contains it is overridden
    seen: list[tuple[str, str]] = []
    for name, ramp in r.parts.items():
        for prev, _ in seen:
            if prev in GROUPS:
                continue
            codes_prev = set(_codes(prev))
            if name in GROUPS and codes_prev <= set(GROUPS[name]):
                out.append(("error", f"[parts] `{prev}` is listed before `{name}`, which contains it: later lines win, "
                                     f"so `{prev}` renders as {ramp}. Move `{prev}` after `{name}`."))
        seen.append((name, ramp))
    if "X" not in "".join(_codes(n) for n in r.parts):
        out.append(("warn", "[parts] `fx` is not mapped: the attack's swing smears render as dark blobs. Add `fx = \"...\"`."))

    # rules
    known = {"edge", "rows", "stripe", "band", "all", "region", "grow", "shrink"}
    for i, rule in enumerate(r.rules):
        tag = f"rule {i + 1} ({rule.get('type')} {rule.get('part')})"
        if rule.get("type") not in known:
            out.append(("error", f"{tag}: unknown rule type; known: {', '.join(sorted(known))}."))
            continue
        col = rule.get("color", "")
        ramp = col.partition(".")[0]
        if col and not col.startswith("#") and col != "clear" and ramp not in r.ramps:
            out.append(("error", f"{tag}: colour `{col}` names no ramp in [palette]."))
        if rule.get("ink") and col and "." not in col and not col.startswith("#") and ramp in r.ramps and "ink" not in r.ramps[ramp]:
            out.append(("info", f"{tag}: `ink = true` with tone-relative `{col}` on a ramp without an ink slot: the "
                                f"generator paints the ramp's shade there. `{col}.base` says so explicitly."))
        codes = set(_codes(rule.get("part", "none")))
        facings = rule.get("facings", [])
        one_side = bool(codes & {"R", "r"}) != bool(codes & {"L", "l"})  # a group like `hands` names both sides
        sided = one_side and (rule.get("anchor") in ("front", "back") or
                              any(s in ("front", "back") for s in rule.get("sides", [])))
        twins = [f for f in facings if f.endswith("_l") and f[:-2] in facings]
        if sided and twins:
            out.append(("warn", f"{tag}: a one-sided part with a front/back side lists both a facing and its mirror "
                                f"({', '.join(twins)}); mirroring puts the arm on the other edge. Name one."))
        if rule.get("type") == "region" and codes == {"T"} and rule.get("anchor") == "back" and i > _first_trim(r.rules):
            out.append(("warn", f"{tag}: flank shading after the collar/hem/zipper rules overpaints them; move it before the trim."))

    # legend
    for ch, ref in r.legend.items():
        if ref != "clear" and not ref.startswith("#") and "." not in ref:
            out.append(("warn", f"[head.legend] `{ch} = \"{ref}\"` is tone-relative: `--draft-grid` picks by colour and cannot "
                                f"use it; make it a fixed slot like `{ref}.base`."))
    classed = set("".join(r.head_classes.values()))
    loose = [ch for ch in r.legend if ch not in classed and ch != "-" and r.legend[ch] != "clear"
             and not r.legend[ch].startswith(("skin", "outline", "#"))]  # (hex literals: --all-slots colours, not a surface)
    if loose:
        out.append(("info", f"[head.legend] {' '.join(loose)}: in no [head.classes] class (hair, texture, lens, rim, caps); "
                            f"--clean and --mirror-swap treat such cells as neither hair nor eyewear (fine for a mask or an ear; "
                            f"list a second hair material under `hair`)."))
    used = set("".join("".join(row) for g in r.grids.values() for row in g))
    unused = [ch for ch in r.legend if ch not in used and ch != "-"]
    if unused and r.grids:
        out.append(("info", f"[head.legend] unused characters: {' '.join(unused)}."))

    # grids
    if not r.grids:
        out.append(("error", "[head.grids] no grids at all: `just compare NAME --draft-grid all --all-slots --clean --apply` "
                             "(add `--mirror-swap` only for a five-view mockup of a one-sided haircut)."))
    missing = [f for f in ("down_side_l", "side_l", "up_side_l") if f[:-2] in r.grids and f not in r.grids]
    if missing:
        out.append(("warn", f"[head.grids] no grid for {', '.join(missing)}: the right-facing grid is mirrored, wrong for a "
                            f"one-sided haircut or visor. `--draft-grid {missing[0]} --mirror-swap` drafts one."))
    frames = build_frames(tpl)
    for facing, g in r.grids.items():
        fr = frames["idle"][facing][0]
        _, hx, hy, _ = fr.head
        H, W = fr.tones.shape
        on_body = 0
        for gy, gx in zip(*np.where(g != ".")):
            y, x = hy + gy - HEAD_PAD, hx + gx - HEAD_PAD
            if 0 <= y < H and 0 <= x < W and fr.labels[y, x] not in ("H", "N", "."):
                on_body += 1
        if on_body:
            out.append(("info", f"[head.grids] {facing}: {on_body} cells land on the body and are ignored (collar row in the draft?)."))
        if not any(ch in r.legend for ch in set("".join("".join(row) for row in g)) - {"."}):
            out.append(("error", f"[head.grids] {facing}: no legend character in the grid."))
        bad = sorted(set("".join("".join(row) for row in g)) - set(r.legend) - {"."})
        if bad:
            out.append(("error", f"[head.grids] {facing}: characters not in the legend: {' '.join(bad)}."))
    return out


def _codes(name: str) -> str:
    from .character import part_codes
    try:
        return part_codes(name)
    except KeyError:
        return ""


def _first_trim(rules) -> int:
    for i, rule in enumerate(rules):
        if rule.get("type") in ("rows", "edge", "stripe", "band", "all"):
            return i
    return len(rules)

"""chargen CLI.

  python -m chargen build [NAME...]      render characters/<name>/recipe.toml -> web/data/characters/<name>/
  python -m chargen preview NAME         contact sheet (all anims x facings) + head-grid sheet in build/preview/
  python -m chargen heads NAME           print head grids aligned with the head templates
  python -m chargen labels               label contact sheet for review in build/preview/labels.png
  python -m chargen compare NAME         pixel mockup vs render, per view, in build/preview/
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .catalog import ROOT
from .character import FACINGS, HEAD_PAD, Recipe, build_frames, export, render_frame
from .labeltool import label_rgba, template
from .review import contact_sheet

CHARS = ROOT / "characters"
BUILD = ROOT / "build"
DATA = ROOT / "web/data"


def recipes(names: list[str]) -> list[Path]:
    if names:
        return [CHARS / n / "recipe.toml" for n in names]
    return sorted(CHARS.glob("*/recipe.toml"))


def cmd_build(names):
    tpl = template()
    export(tpl, None, DATA / "characters/template")
    print("built template")
    for p in recipes(names):
        export(tpl, Recipe(p), DATA / "characters" / p.parent.name)
        print("built", p.parent.name)
    index = sorted(d.name for d in (DATA / "characters").iterdir() if (d / "sheet.json").exists())
    index.remove("template")
    (DATA / "characters/index.json").write_text(json.dumps(["template"] + index))


def cmd_preview(name, anims):
    tpl = template()
    r = Recipe(CHARS / name / "recipe.toml")
    frames = build_frames(tpl)
    imgs, rows, labels = [], [], []
    for anim, facings in frames.items():
        if anims and anim not in anims:
            continue
        for facing, fr in facings.items():
            rows.append(list(range(len(imgs), len(imgs) + len(fr))))
            labels.append(f"{anim}/{facing}")
            imgs += [render_frame(r, f) for f in fr]
    out = BUILD / "preview"
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{name}{'_' + '_'.join(anims) if anims else ''}.png"
    contact_sheet(imgs, rows, labels, scale=4).save(p)
    print(p)
    # head check: idle frame 0 of every facing, big
    idle = [frames["idle"][f][0] for f in FACINGS]
    s = 12
    sheet = Image.new("RGBA", (len(idle) * 32 * s, 32 * s), (60, 62, 80, 255))
    for i, f in enumerate(idle):
        sheet.alpha_composite(Image.fromarray(render_frame(r, f)).resize((32 * s, 32 * s), Image.NEAREST), (i * 32 * s, 0))
    sheet.save(out / f"{name}_facings.png")
    print(out / f"{name}_facings.png")


def cmd_crops(name, recipes_, box, diff=False):
    """Rows of the eight idle facings cropped to `box` (y0,y1 in frame rows) at 16x, one row
    per recipe: the current one first, then any --recipe variants. For judging a change
    to the jacket or the shoes across every angle at once."""
    tpl = template()
    frames = build_frames(tpl)
    y0, y1 = box
    paths = [CHARS / name / "recipe.toml"] + [Path(p) for p in recipes_]
    s, w, h = 16, 20, y1 - y0
    cw, ch = w * s + 6, h * s + 6
    from PIL import ImageDraw
    # the mockup's views, placed on the current render, as the first row (the reference to judge against)
    mock = {}
    src = CHARS / name / "concept" / f"{name}-pixel-mockup.png"
    if src.exists():
        from .mockup import extract, mockup_facings, place
        sprites = extract(src)
        r0 = Recipe(paths[0])
        for sp, f in zip(sprites, mockup_facings(len(sprites))):
            mock[f] = place(sp, render_frame(r0, frames["idle"][f][0]))
    rows_n = len(paths) + (1 if mock else 0)
    out = Image.new("RGBA", (len(FACINGS) * cw, rows_n * ch), (60, 62, 80, 255))
    d = ImageDraw.Draw(out)
    if mock:
        for i, f in enumerate(FACINGS):
            if f in mock:
                out.alpha_composite(Image.fromarray(mock[f]).crop((6, y0, 6 + w, y1)).resize((w * s, h * s), Image.NEAREST), (i * cw, 0))
        d.text((4, 2), "mockup", fill=(255, 255, 255, 255))
    base = {}
    for j, p in enumerate(paths):
        r = Recipe(p)
        jj = j + (1 if mock else 0)
        for i, f in enumerate(FACINGS):
            px = render_frame(r, frames["idle"][f][0])
            im = Image.fromarray(px).crop((6, y0, 6 + w, y1)).resize((w * s, h * s), Image.NEAREST)
            out.alpha_composite(im, (i * cw, jj * ch))
            if j == 0:
                base[f] = px
            elif diff:  # outline every pixel that differs from the current recipe
                dm = (px != base[f]).any(-1)
                for y, x in zip(*np.where(dm[y0:y1, 6:6 + w])):
                    d.rectangle([i * cw + x * s, jj * ch + y * s, i * cw + (x + 1) * s - 1, jj * ch + (y + 1) * s - 1],
                                outline=(255, 64, 200, 255), width=1)
        d.text((4, jj * ch + 2), p.stem if j else "current", fill=(255, 255, 255, 255))
    dest = BUILD / "preview" / f"{name}_crops.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    print(dest)


def cmd_lint(name):
    """Static checks for the mistakes that cost iteration steps (see chargen/lint.py)."""
    from .lint import lint
    findings = lint(CHARS / name / "recipe.toml", template())
    for level, msg in findings:
        print(f"{level:5} {msg}")
    print(f"{len(findings)} finding(s)" if findings else "clean")
    return 1 if any(l == "error" for l, _ in findings) else 0


def cmd_review(name):
    """One image to look at after a change: the eight idle facings at 12x, torso and feet crops,
    the turn-around, and walk, run, jump and attack in the angled views -> build/preview/NAME_review.png."""
    tpl = template()
    r = Recipe(CHARS / name / "recipe.toml")
    frames = build_frames(tpl)
    from PIL import ImageDraw
    rows = []
    s = 12
    row = Image.new("RGBA", (len(FACINGS) * (24 * s + 6), 28 * s + 14), (60, 62, 80, 255))
    dr = ImageDraw.Draw(row)
    for i, f in enumerate(FACINGS):
        row.alpha_composite(Image.fromarray(render_frame(r, frames["idle"][f][0])).crop((4, 4, 28, 32)).resize((24 * s, 28 * s), Image.NEAREST), (i * (24 * s + 6), 14))
        dr.text((i * (24 * s + 6) + 2, 1), f, fill=(230, 230, 230, 255))
    rows.append(("facings 12x", row))
    s = 24  # heads: the grids are the hand work, so they get the biggest view
    row = Image.new("RGBA", (len(FACINGS) * (20 * s + 6), 16 * s + 14), (60, 62, 80, 255))
    dr = ImageDraw.Draw(row)
    for i, f in enumerate(FACINGS):
        row.alpha_composite(Image.fromarray(render_frame(r, frames["idle"][f][0])).crop((6, 4, 26, 20)).resize((20 * s, 16 * s), Image.NEAREST), (i * (20 * s + 6), 14))
        dr.text((i * (20 * s + 6) + 2, 1), f, fill=(230, 230, 230, 255))
    rows.append(("heads 24x", row))
    for label, (y0, y1) in (("torso 16x", (17, 31)), ("feet 16x", (24, 32))):
        s = 16
        row = Image.new("RGBA", (len(FACINGS) * (20 * s + 6), (y1 - y0) * s), (60, 62, 80, 255))
        for i, f in enumerate(FACINGS):
            row.alpha_composite(Image.fromarray(render_frame(r, frames["idle"][f][0])).crop((6, y0, 26, y1)).resize((20 * s, (y1 - y0) * s), Image.NEAREST), (i * (20 * s + 6), 0))
        rows.append((label, row))
    s = 6
    for anim, facing in (("rotate", "all"), ("walk", "down_side"), ("run", "side"), ("jump", "up_side"), ("attack", "down"), ("walk", "side_l")):
        fr = frames[anim][facing]
        row = Image.new("RGBA", (len(fr) * (32 * s + 4), 32 * s), (60, 62, 80, 255))
        for i, f in enumerate(fr):
            row.alpha_composite(Image.fromarray(render_frame(r, f)).resize((32 * s, 32 * s), Image.NEAREST), (i * (32 * s + 4), 0))
        rows.append((f"{anim}/{facing} 6x", row))
    W = max(im.width for _, im in rows) + 8
    out = Image.new("RGBA", (W, sum(im.height + 22 for _, im in rows)), (60, 62, 80, 255))
    d = ImageDraw.Draw(out)
    y = 0
    for label, im in rows:
        d.text((4, y + 4), label, fill=(230, 230, 230, 255))
        out.alpha_composite(im, (4, y + 18))
        y += im.height + 22
    dest = BUILD / "preview" / f"{name}_review.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    print(dest, out.size)


def cmd_turntable(name, scale=8, ms=220, anims=("idle",)):
    """A GIF of the character turning: the idle frame of each facing in the turn-around's order
    (then any further animation given, all facings in the same order), for a quick visual
    check of a build -> build/preview/NAME_turntable.gif."""
    from .mockup import TURNAROUND_FACINGS
    tpl = template()
    r = Recipe(CHARS / name / "recipe.toml")
    frames = build_frames(tpl)
    imgs = []
    for anim in anims:
        for facing in TURNAROUND_FACINGS:
            fr = frames[anim][facing]
            for f in (fr[:1] if anim == "idle" else fr):
                im = Image.new("RGBA", (32 * scale, 32 * scale), (60, 62, 80, 255))
                im.alpha_composite(Image.fromarray(render_frame(r, f)).resize((32 * scale, 32 * scale), Image.NEAREST))
                imgs.append(im.convert("RGB"))
    pal = imgs[0].quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in imgs]
    dest = BUILD / "preview" / f"{name}_turntable.gif"
    dest.parent.mkdir(parents=True, exist_ok=True)
    q[0].save(dest, save_all=True, append_images=q[1:], duration=ms, loop=0, optimize=True)
    print(dest, len(q), "frames")


def cmd_grid(name, view, row=None, text=None):
    """Print a head grid with row numbers, or set one row of it: `grid NAME VIEW 7 '..kbbbk..'`.
    The setter replaces the whole block in the file, so no string search can land in the wrong
    view (a search for the side_l block's opening matches inside up_side_l's, a pitfall every run hit once)."""
    from .mockup import apply_grid, grid_text
    r = Recipe(CHARS / name / "recipe.toml")
    if view not in r.grids:
        raise SystemExit(f"no grid for {view}; grids: {', '.join(r.grids)}")
    g = r.grids[view]
    if row is None:
        for y, line in enumerate(grid_text(g).split("\n")):
            print(f"{y:2d} {line}")
        return
    if not (0 <= row < g.shape[0]):
        raise SystemExit(f"row {row} is outside the grid (0..{g.shape[0] - 1})")
    new = list(text.ljust(g.shape[1], ".")[:g.shape[1]])
    bad = sorted(set(new) - set(r.legend) - {"."})
    if bad:
        raise SystemExit(f"characters not in the legend: {' '.join(bad)}")
    print(f"{view} row {row}: {''.join(g[row])} -> {''.join(new)}")
    g[row] = new
    apply_grid(r.path, view, g)
    print(f"written to {r.path.name}")


def cmd_step(name, message, snapshot=False, goal=None, amend=False):
    """Score the recipe, append a row to history/NOTES.md, snapshot every fifth step."""
    from .mockup import extract, mockup_facings, placement, similarity
    tpl = template()
    r = Recipe(CHARS / name / "recipe.toml")
    frames = build_frames(tpl)
    sprites = extract(CHARS / name / "concept" / f"{name}-pixel-mockup.png")
    MOCKUP_FACINGS = mockup_facings(len(sprites))
    renders = [render_frame(r, frames["idle"][f][0]) for f in MOCKUP_FACINGS]
    scores = [similarity(sp, im) for sp, im in zip(sprites, renders)]
    mean = float(np.mean(scores))
    hist = CHARS / name / "history"
    hist.mkdir(exist_ok=True)
    # the mockup's placement per view: a grid drafted before it moved is a pixel off now
    pl_file = hist / "placement.json"
    pl_now = {f: list(placement(sp, im)) + [f in r.grids] for f, sp, im in zip(MOCKUP_FACINGS, sprites, renders)}
    pl_old = json.loads(pl_file.read_text()) if pl_file.exists() else {}
    moved = [f for f in pl_now if f in pl_old and pl_old[f][:2] != pl_now[f][:2] and pl_now[f][2]
             and len(pl_old[f]) > 2 and pl_old[f][2]]  # (a view drafted since the last step moved by design)
    pl_file.write_text(json.dumps(pl_now))
    notes = hist / "NOTES.md"
    text = notes.read_text() if notes.exists() else ""
    rows = [l for l in text.splitlines() if l.startswith("| ") and l.split("|")[1].strip().isdigit()]
    if amend and rows:  # replace the last row (a fix to an unscored view, a better message)
        text = text.replace(rows[-1] + "\n", "")
        n = int(rows[-1].split("|")[1])
    else:
        n = (int(rows[-1].split("|")[1]) + 1) if rows else 0
    if not text.strip():
        text = f"# {name} iteration log\n\n| step | change | similarity |\n|---|---|---|\n"
    notes.write_text(text.rstrip("\n") + f"\n| {n} | {message} | {mean:.4f} |\n")
    if snapshot or n % 5 == 0:
        (hist / f"step-{n:02d}.toml").write_text((CHARS / name / "recipe.toml").read_text())
        print(f"snapshot history/step-{n:02d}.toml")
    print(f"step {n}: {mean:.4f}  (" + "  ".join(f"{f}={v:.4f}" for f, v in zip(MOCKUP_FACINGS, scores)) + ")")
    if moved:
        print("placement moved since the last step in " + ", ".join(moved) + ": candidates for a re-draft "
              "(`--draft-grid VIEW --all-slots --clean --apply` keeps the new grid only where it scores)")
    if goal is not None:
        from .mockup import ceiling, palette_letters
        cs = float(np.mean([ceiling(sp, palette_letters(r)) for sp in sprites]))
        thr = cs * (1 - goal / 100)
        margin = mean - thr
        status = (f"REACHED (+{margin:.4f})" + (", a thin margin: a generator fix can take it back, leave 0.001 or more" if margin < 0.001 else "")
                  if margin >= 0 else f"short by {-margin:.4f}")
        print(f"goal: ceiling {cs:.4f}, within {goal:g}% = {thr:.4f}: " + status)


def cmd_heads(name):
    tpl = template()
    r = Recipe(CHARS / name / "recipe.toml")
    frames = build_frames(tpl)
    from .ascii import tone_ascii
    for facing in FACINGS:
        base = facing[:-2] if facing.endswith("_l") else facing
        t = np.pad(tpl.heads[base], HEAD_PAD)
        if facing.endswith("_l"):
            t = t[:, ::-1]
        ta = tone_ascii(t)
        g = r.grids.get(facing)
        fr = frames["idle"][facing][0]
        _, hx, hy, _ = fr.head
        print(f"[{facing}]  template | grid" + ("" if g is not None else "  (no grid)")
              + f"   grid col = frame col - {hx - HEAD_PAD}, grid row = frame row - {hy - HEAD_PAD}")
        for y in range(len(ta)):
            gr = "".join(g[y]) if g is not None and y < len(g) else ""
            print(f"{y:2d} {ta[y].replace(' ', '_')} | {gr}")


def cmd_labels(anims=()):
    tpl = template()
    from .labels import load_all
    from .review import anim_rows
    labs = load_all(tpl)
    imgs = []
    for i in range(len(labs)):
        lc = label_rgba(labs[i])
        mix = tpl.rgba[i].copy()
        m = labs[i] != "."
        mix[m, :3] = (tpl.rgba[i][m, :3] * 0.35 + lc[m, :3] * 0.65).astype(np.uint8)
        imgs.append(mix)
    rows, names = anim_rows({a: d for a, d in tpl.anims.items() if not anims or a in anims})
    out = BUILD / f"preview/labels{'_' + '_'.join(anims) if anims else ''}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    contact_sheet(imgs, rows, names, scale=5).save(out)
    print(out)


def cmd_compare(name, mockup=None, recipe=None, anim="idle", frame=0, text=(), fit=False, optimize=False, ceil=False, fit_grid=(), chars=None, widths_=False, digits_=(), slack_=False,
                split_=False, shift_=False, fit_part_=None, draft=(), hex_=None, quiet=False, mirror_swap=False, apply=False, clean=False, hot=0,
                init_pal=False, goal=None, oracle_=False, _pass=1, min_gain=0.0015, ablate_=False, all_slots=False, sweep_=0, sweep_parts=None, labels_=(), try_=None):
    """Mockup (snapped to its pixel grid) above the render: whole figures, head close-ups,
    then heat maps of where the score is lost. `text` prints the given views as text,
    mockup | render in the recipe's palette letters; `fit` suggests palette moves."""
    from .mockup import (breakdown, cost_maps, digits, draft_grid, extract, fit_part, grid_text, heat,
                         hex_box, mirror_grid, mockup_facings, palette_fit, palette_letters, place, shift_probe, similarity, slack,
                         split, text_view, widths, clean_grid, apply_grid, hot_spots, init_palette, unlisted_slots, apply_legend, labels_view)
    tpl = template()
    r = Recipe(Path(recipe) if recipe else CHARS / name / "recipe.toml")
    src = Path(mockup) if mockup else CHARS / name / "concept" / f"{name}-pixel-mockup.png"
    frames = build_frames(tpl)
    cell, gap = 32 * 12, 16
    sprites = extract(src)
    MOCKUP_FACINGS = mockup_facings(len(sprites))  # 5 views, or 8 with the left facings in the sheet
    scores = []
    sheet = Image.new("RGBA", (gap + len(sprites) * (cell + gap), gap + 6 * (cell + gap)), (60, 62, 80, 255))
    parts: dict[str, list] = {}
    pal = palette_letters(r)
    pairs: dict[tuple, list] = {}
    part_pairs: dict[str, list] = {}
    hot_views: list = []
    pal_views: list = []
    oracle_views: list = []
    from .mockup import quantize
    extra = unlisted_slots(r) if (draft and all_slots) else {}
    if extra:
        r.legend.update(extra)  # (the letters a drafted grid uses are written to the file after the loop)
    used_extra: set = set()
    for i, (sprite, facing) in enumerate(zip(sprites, MOCKUP_FACINGS)):
        fr = frames[anim][facing][frame]
        rend = render_frame(r, fr)
        scores.append(similarity(sprite, rend))
        placed, cr, cm = cost_maps(sprite, rend)
        for g, v in breakdown(cr, cm, fr.labels, rend, placed).items():
            parts.setdefault(g, []).append(v)
        if facing in text or "all" in text:
            print(f"== {facing}: mockup | render")
            print("\n".join(text_view(placed, rend, pal)))
        if facing in labels_ or "all" in labels_:
            print(f"== {facing}: mockup | labels | tones")
            print("\n".join(labels_view(placed, rend, fr, pal)))
        if widths_:
            print(f"== {facing}: widths (positive = mockup wider)")
            print("\n".join(widths(placed, rend, fr.labels)))
        if facing in digits_ or "all" in digits_:
            print(f"== {facing}: cost digits")
            print("\n".join(digits(placed, rend, cr, cm)))
        if slack_:
            sl = slack(placed, rend, fr.labels, pal)
            print(f"== {facing}: slack   " + "  ".join(f"{p}={n:.3f}/{c:.3f}" for p, (n, c) in sl.items()))
        if split_:
            si, co = split(placed, rend)
            print(f"== {facing}: silhouette={si:.3f} colour-loss={co:.3f}")
        if shift_ and facing in r.grids:
            dx, dy, gain = shift_probe(r, facing, sprite, fr, render_frame, chars)
            print(f"== {facing}: best grid shift{' of ' + chars if chars else ''} dx={dx:+d} dy={dy:+d} gain={gain:+.3f}")
        if facing in draft or "all" in draft:
            g = draft_grid(r, facing, placed, fr, chars=chars)  # (extra slots are in r.legend by now)
            note = ""
            if clean:  # each optional pass (speckles, last row) is kept per view only where it does not
                keep = r.grids.get(facing)  # cost: on spiky light hair the speckles are strand texture, and
                cands = []                  # a collar in the legend makes the last row worth keeping
                for despeckle in (True, False):
                    for last_row in (True, False):
                        r.grids[facing] = clean_grid(g, r.legend, r.head_classes, despeckle=despeckle, last_row=last_row)
                        cands.append((similarity(sprite, render_frame(r, fr)), despeckle, last_row, r.grids[facing]))
                if keep is None:
                    del r.grids[facing]
                else:
                    r.grids[facing] = keep
                full = cands[0][0]
                best = max(cands, key=lambda c: (round(c[0], 6), c[1], c[2]))  # ties go to the fuller cleanup
                g = best[3]
                skipped = [n for n, on in (("speckle", best[1]), ("last-row", best[2])) if not on]
                note = "cleaned; " if not skipped else f"rim pass only, {' and '.join(skipped)} skipped ({full - best[0]:+.4f}); "
            print(f"== {facing}: drafted grid ({note}nearest legend colour per cell)")
            if not (quiet and apply):  # written to the file anyway: --quiet skips the grid text
                print(grid_text(g))
            far = getattr(draft_grid, "far", [])
            if len(far) >= 3:  # the nearest colour is a poor one: the palette lacks a colour the mockup paints here
                med = np.median(np.array(far), 0).astype(int)
                print(f"   {len(far)} cells have no legend colour within reach (median #{med[0]:02x}{med[1]:02x}{med[2]:02x}): "
                      "a slot the palette lacks (a shadowed nape, a strap); add it and redraft this view")
            used_extra |= set("".join("".join(row) for row in g)) & set(extra)
            if apply and facing in r.grids:  # a re-draft over an existing grid: keep it only where it scores
                old_g = r.grids[facing]
                s_old = similarity(sprite, render_frame(r, fr))
                r.grids[facing] = g
                s_new = similarity(sprite, render_frame(r, fr))
                r.grids[facing] = old_g
                if s_new < s_old - 1e-9:
                    print(f"   kept the existing grid: the draft scores {s_new - s_old:+.4f} here (edit rows by hand, or --draft-grid without --apply to read it)")
                    continue
            if apply:
                apply_grid(r.path, facing, g)
                print(f"   written to {r.path.name}")
        if hex_ and hex_[0] == facing:
            print(f"== {facing}: mockup hex")
            print("\n".join(hex_box(placed, *hex_[1])))
        if fit_part_:
            codes = list(fit_part_)
            for y, x in zip(*np.where((rend[..., 3] > 0) & (placed[..., 3] > 0) & np.isin(fr.labels, codes))):
                part_pairs.setdefault(quantize(rend[y, x, :3], pal), []).append((placed[y, x, :3], cr[y, x]))
        for y, x in zip(*np.where((rend[..., 3] > 0) & (placed[..., 3] > 0))):
            pairs.setdefault(tuple(rend[y, x, :3]), []).append(placed[y, x, :3])
        heads = []
        for im in (sprite, rend):  # top 16 rows around the figure's center column
            ys = np.where(im[..., 3].any(1))[0]
            xs = np.where(im[..., 3].any(0))[0]
            cx = (xs[0] + xs[-1]) // 2
            heads.append(Image.fromarray(im).crop((cx - 8, ys[0], cx + 8, ys[0] + 16)))
        # rows 5/6: where the render loses score (red = unmatched), and the mockup pixels it never matches
        cells = [Image.fromarray(place(sprite, rend)), Image.fromarray(rend)] + heads
        cells += [Image.fromarray(heat(cr, rend)), Image.fromarray(heat(cm, placed))]
        for j, im in enumerate(cells):
            sheet.alpha_composite(im.resize((cell, cell), Image.NEAREST), (gap + i * (cell + gap), gap + j * (cell + gap)))
        hot_views.append((facing, placed, rend, cr, cm, pal))
        pal_views.append((facing, placed, fr.labels, fr.tones))
        oracle_views.append((facing, sprite, placed, rend, fr.labels))
    if extra and used_extra:
        print("== legend: slots the drafts used beyond the legend: " + " ".join(f"{c}={extra[c]}" for c in sorted(used_extra)))
        if apply:
            apply_legend(r.path, {c: extra[c] for c in sorted(used_extra)}, recipe=r)
    if draft and apply and _pass == 1 and any(f in MOCKUP_FACINGS or f == "all" for f in draft):
        # the mockup's best placement moves once the head is covered: draft again against it
        print("== second pass: the placement changed with the grids, redrafting")
        return cmd_compare(name, mockup, recipe, anim, frame, text, fit, optimize, ceil, fit_grid, chars, widths_, digits_,
                           slack_, split_, shift_, fit_part_, draft, hex_, quiet, mirror_swap, apply, clean, hot, init_pal,
                           goal, oracle_, _pass=2, min_gain=min_gain, ablate_=ablate_, all_slots=False)
    if draft and apply:  # the right twins may have just been written: reload them
        r = Recipe(r.path)
    lefts = [f for f in ("down_side_l", "side_l", "up_side_l") if f not in MOCKUP_FACINGS  # in the sheet: drafted above
             and (f in draft or ("all" in draft and f[:-2] in r.grids))]
    for facing in lefts:
        g, done = mirror_grid(r, facing, frames[anim][facing][frame], tpl.heads[facing[:-2]], swap=mirror_swap, classes=r.head_classes)
        if g is None:
            print(f"== {facing}: no {facing[:-2]} grid to mirror")
            continue
        print(f"== {facing}: {done} (look at the heads row of `just review`)")
        print(grid_text(g))
        if apply:
            apply_grid(r.path, facing, g)
            print(f"   written to {r.path.name}")
    if hot:
        print("legend: " + " ".join(f"{l.strip()}=#{c[0]:02x}{c[1]:02x}{c[2]:02x}" for c, l in pal))
        print(f"== {hot} costliest pixels (single scattered pixels at cost ~1 mean nothing big is left)")
        print("\n".join(hot_spots(hot_views, hot)))
    if try_:
        from .character import load_toml
        print(f"== try: rules from {try_} added to the recipe's (grow/shrink/shift before them, the rest after), per-view gain")
        extra_rules = load_toml(Path(try_)).get("rules", [])
        idle = [frames[anim][f][frame] for f in MOCKUP_FACINGS]
        base = [similarity(sp, render_frame(r, fr)) for sp, fr in zip(sprites, idle)]
        rules0 = r.rules
        rows, limited = [], []
        SIL = ("grow", "shrink", "shift")  # silhouette rules go first, so the recipe's trim sees their labels

        def with_(cands):
            return [c for c in cands if c.get("type") in SIL] + rules0 + [c for c in cands if c.get("type") not in SIL]
        for i, rule in enumerate(extra_rules):  # each rule alone, then all together
            r.rules = with_([rule])
            d = [similarity(sp, render_frame(r, fr)) - b for sp, fr, b in zip(sprites, idle, base)]
            pos = [f for f, v in zip(MOCKUP_FACINGS, d) if v > 0.0005]
            rows.append((f"rule {i + 1}: {rule.get('type')} {rule.get('part')} {rule.get('color', '')}", d, pos))
            if pos:
                limited.append({**rule, "facings": pos} if "facings" not in rule else rule)
        if len(extra_rules) > 1:
            r.rules = with_(extra_rules)
            rows.append(("all together", [similarity(sp, render_frame(r, fr)) - b for sp, fr, b in zip(sprites, idle, base)], []))
            r.rules = with_(limited)
            rows.append(("all, each limited to its gaining views", [similarity(sp, render_frame(r, fr)) - b for sp, fr, b in zip(sprites, idle, base)], []))
        r.rules = rules0
        print(f"{'':44}" + "".join(f"{f:>12}" for f in MOCKUP_FACINGS) + f"{'mean':>10}{'if limited':>12}  gains in")
        for label, d, pos in rows:
            lim = sum(max(v, 0) for v in d) / len(d)
            print(f"{label[:44]:44}" + "".join(f"{v:+12.4f}" for v in d) + f"{np.mean(d):+10.4f}"
                  + (f"{lim:+12.4f}  {','.join(pos) or '-'}" if pos or label.startswith("rule") else ""))
    if sweep_:
        from .mockup import sweep
        idle = [frames[anim][f][frame] for f in MOCKUP_FACINGS]
        print("== sweep: candidate rules appended after yours, per-view gains (confirm picks on crops --diff)")
        print("\n".join(sweep(r, sprites, idle, MOCKUP_FACINGS, n=sweep_, parts=sweep_parts.split(",") if sweep_parts else None)))
    if ablate_:
        from .mockup import ablate
        idle = [frames[anim][f][frame] for f in MOCKUP_FACINGS]
        print("== ablation: score gain when a rule is removed")
        print("\n".join(ablate(r, sprites, lambda rec: [render_frame(rec, fr) for fr in idle])))
    if oracle_:
        from .mockup import oracle
        print("== oracle: gain from a pixel copy of the mockup, per part")
        print("\n".join(oracle(oracle_views, pal)))
    if init_pal:
        from .catalog import TONE_IDS
        print("== palette from the mockup, per body part and template tone")
        print("\n".join(init_palette(pal_views, TONE_IDS, r.parts)))
    out = BUILD / "preview" / f"{name}_compare.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out)
    if text or fit or fit_part_:  # letters are assigned per recipe: always show what they mean
        print("legend: " + " ".join(f"{l.strip()}=#{c[0]:02x}{c[1]:02x}{c[2]:02x}" for c, l in pal))
    if fit:
        print("\n".join(palette_fit(pairs, pal)))
    if fit_part_:
        print(f"== fit on parts {fit_part_} (all views)")
        print("\n".join(fit_part(part_pairs, pal)))
    if ceil or goal is not None:  # what this palette could reach with the mockup's exact shapes
        from .mockup import ceiling
        cs = [ceiling(sp, pal) for sp in sprites]
        print("ceiling    " + "  ".join(f"{f}={v:.4f}" for f, v in zip(MOCKUP_FACINGS, cs)) + f"  mean={np.mean(cs):.4f}")
        if goal is not None:  # the goal is a distance below the ceiling, in percent of it
            thr = float(np.mean(cs)) * (1 - goal / 100)
            mean = float(np.mean(scores))
            print(f"goal       within {goal:g}% of the ceiling = {thr:.4f}; mean {mean:.4f} "
                  + (f"REACHED (+{mean - thr:.4f})" if mean >= thr else f"short by {thr - mean:.4f}"))
    if fit_grid:  # trace the mockup with the head grids; prints the grids; --apply writes those that gained
        from .mockup import fit_grid as _fit, grid_text
        views = [f for f in MOCKUP_FACINGS if f in r.grids] if "all" in fit_grid else list(fit_grid)
        from multiprocessing import Pool
        from .mockup import _fit_view_init, _fit_view_one
        with Pool(min(8, len(views)), initializer=_fit_view_init, initargs=(r, frames[anim], frame, sprites, MOCKUP_FACINGS, chars)) as pool:
            results = pool.map(_fit_view_one, views)
        for facing, (g, b, a) in zip(views, results):
            print(f"fit-grid {facing}: {b:.4f} -> {a:.4f}")
            print(grid_text(g))
            if apply and a > b:
                old_g = r.grids[facing]  # the row below the jaw stays as it was: the fit cannot tell a tip from a collar
                last = max((y for y in range(old_g.shape[0]) if (old_g[y] != ".").any()), default=None)
                if last is not None and last < g.shape[0]:
                    g[last] = old_g[last]
                apply_grid(r.path, facing, g)
                r.grids[facing] = g
                print(f"   written to {r.path.name} (last row kept)")
    if optimize:  # bounded palette search; prints the moves, applies nothing
        from .mockup import optimize_palette
        idle = [frames[anim][f][frame] for f in MOCKUP_FACINGS]
        moves = optimize_palette(r, sprites, lambda rec: [render_frame(rec, fr) for fr in idle],
                                 radius=28 if min_gain >= 0.001 else 20, step=8 if min_gain >= 0.001 else 4, min_gain=min_gain)
        # a palette move lifts the ceiling too: the goal is a distance below it, so report the net margin
        from .character import hex_rgb
        from .mockup import ceiling as _ceiling
        lines = []
        for a, b, c, d, g in moves:  # (optimize_palette leaves kept moves applied: start from the original colour)
            r.ramps[a][b] = hex_rgb(c)
        for a, b, c, d, g in moves:
            before = float(np.mean([_ceiling(sp, palette_letters(r)) for sp in sprites]))
            r.ramps[a][b] = hex_rgb(d)
            after = float(np.mean([_ceiling(sp, palette_letters(r)) for sp in sprites]))
            dc = after - before
            lines.append(f"{a}.{b} {c} -> {d} (score +{g:.4f}, ceiling {dc:+.4f}, net margin {g - dc * (1 - (goal or 3) / 100):+.4f})")
        print("optimize: " + ("; ".join(lines) or "no move gains") + ("" if not moves else "   (moves applied cumulatively for the ceiling column; nothing written)"))
    written = apply and (draft or fit_grid)
    if written:  # the scores above were taken before the grids were written: re-score the file
        r2 = Recipe(r.path)
        scores = [similarity(sp, render_frame(r2, frames[anim][f][frame])) for sp, f in zip(sprites, MOCKUP_FACINGS)]
    print("similarity " + "  ".join(f"{f}={v:.4f}" for f, v in zip(MOCKUP_FACINGS, scores)) + f"  mean={np.mean(scores):.4f}"
          + ("  (after the grids were written)" if written else ""))
    if quiet:
        return
    # loss per body part, in score points (render side + mockup side), per view then mean
    print("loss      " + "  ".join(f"{f:>10}" for f in MOCKUP_FACINGS) + "        mean")
    for g, vs in parts.items():
        cells = [f"{a + b:.3f}({a:.2f}/{b:.2f})" for a, b, _ in vs]
        print(f"{g:9} " + "  ".join(f"{c:>10}" for c in cells) + f"  {np.mean([a + b for a, b, _ in vs]):.3f}")


def main():
    ap = argparse.ArgumentParser(prog="chargen")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("names", nargs="*")
    p = sub.add_parser("preview"); p.add_argument("name"); p.add_argument("anims", nargs="*")
    h = sub.add_parser("heads"); h.add_argument("name")
    cr = sub.add_parser("crops"); cr.add_argument("name"); cr.add_argument("--recipe", action="append", default=[])
    cr.add_argument("--box", default="17,32", help="frame rows y0,y1 (torso 17,31; feet 24,32; head 4,20)")
    cr.add_argument("--diff", action="store_true", help="outline pixels that differ from the current recipe")
    ln = sub.add_parser("lint"); ln.add_argument("name")
    rv = sub.add_parser("review"); rv.add_argument("name")
    gr = sub.add_parser("grid"); gr.add_argument("name"); gr.add_argument("view"); gr.add_argument("row", nargs="?", type=int); gr.add_argument("text", nargs="?")
    tt = sub.add_parser("turntable"); tt.add_argument("name"); tt.add_argument("anims", nargs="*", default=["idle"])
    tt.add_argument("--scale", type=int, default=8); tt.add_argument("--ms", type=int, default=220)
    st = sub.add_parser("step"); st.add_argument("name"); st.add_argument("message"); st.add_argument("--snapshot", action="store_true")
    st.add_argument("--goal", type=float, metavar="PCT", help="also report the target PCT percent below the ceiling")
    st.add_argument("--amend", action="store_true", help="replace the last NOTES row instead of adding one")
    lb = sub.add_parser("labels"); lb.add_argument("anims", nargs="*")
    c = sub.add_parser("compare"); c.add_argument("name"); c.add_argument("--mockup"); c.add_argument("--recipe")
    c.add_argument("--text", nargs="*", default=(), metavar="VIEW", help="print views as text (or 'all')")
    c.add_argument("--fit", action="store_true", help="suggest palette moves from the mockup's colors")
    c.add_argument("--optimize", action="store_true", help="bounded palette search against the mockup (prints moves)")
    c.add_argument("--ceiling", action="store_true", help="score of the mockup quantized to the recipe's palette")
    c.add_argument("--fit-grid", nargs="*", default=(), metavar="VIEW", help="trace the mockup with the head grid (prints it)")
    c.add_argument("--widths", action="store_true", help="per-row silhouette extents, mockup vs render")
    c.add_argument("--digits", nargs="*", default=(), metavar="VIEW", help="cost maps as digits (or 'all')")
    c.add_argument("--slack", action="store_true", help="per-part loss now / at the palette ceiling")
    c.add_argument("--split", action="store_true", help="silhouette match vs colour loss per view")
    c.add_argument("--shift", action="store_true", help="best whole-grid offset per head grid")
    c.add_argument("--fit-part", metavar="CODES", help="fit table restricted to label codes, e.g. T or Rr")
    c.add_argument("--draft-grid", nargs="*", default=(), metavar="VIEW", help="draft a head grid from the mockup (or 'all')")
    c.add_argument("--hex", nargs=2, metavar=("VIEW", "Y0,Y1,X0,X1"), help="raw mockup hex for a box of frame pixels")
    c.add_argument("--quiet", action="store_true", help="no loss table")
    c.add_argument("--mirror-swap", action="store_true", help="with --draft-grid VIEW_l: swap hair and stubble (one-sided cut)")
    c.add_argument("--clean", action="store_true", help="with --draft-grid: the mechanical cleanups (visor chars off the lens rows, speckles, last row)")
    c.add_argument("--apply", action="store_true", help="with --draft-grid: write the grids into the recipe")
    c.add_argument("--hot", type=int, default=0, metavar="N", help="the N costliest pixels over all views")
    c.add_argument("--init-palette", action="store_true", help="median mockup colour per body part and tone (before grids)")
    c.add_argument("--goal", type=float, metavar="PCT", help="report the target as PCT percent below the palette ceiling")
    c.add_argument("--oracle", action="store_true", help="gain from a pixel copy of the mockup per body part: where the gap lives")
    c.add_argument("--ablate", action="store_true", help="drop each rule in turn and score (candidates to confirm with --hex)")
    c.add_argument("--min-gain", type=float, default=0.0015, help="--optimize keeps a move only above this gain (0.0004 for the last thousandths; it raises the ceiling too)")
    c.add_argument("--chars", help="legend characters --fit-grid may use (default: all)")
    c.add_argument("--try", dest="try_", metavar="FILE", help="a TOML file with [[rules]]: each appended to the recipe alone, then all together, with the per-view gains")
    c.add_argument("--labels", nargs="*", default=(), metavar="VIEW", help="print the frame's body-part labels and tones beside the mockup (or 'all')")
    c.add_argument("--sweep", type=int, default=0, metavar="N", help="forward rule search: score simple rule shapes on every part in every ramp, print the N best with per-view gains")
    c.add_argument("--sweep-parts", metavar="P,P", help="with --sweep: only these parts (default: every part and group)")
    c.add_argument("--all-slots", action="store_true", help="with --draft-grid: also offer every palette slot the legend lacks (letters appended to the legend with --apply)")
    a = ap.parse_args()
    if a.cmd == "build":
        cmd_build(a.names)
    elif a.cmd == "preview":
        cmd_preview(a.name, a.anims)
    elif a.cmd == "heads":
        cmd_heads(a.name)
    elif a.cmd == "crops":
        cmd_crops(a.name, a.recipe, tuple(int(v) for v in a.box.split(",")), a.diff)
    elif a.cmd == "lint":
        cmd_lint(a.name)
    elif a.cmd == "review":
        cmd_review(a.name)
    elif a.cmd == "grid":
        cmd_grid(a.name, a.view, a.row, a.text)
    elif a.cmd == "turntable":
        cmd_turntable(a.name, a.scale, a.ms, a.anims or ["idle"])
    elif a.cmd == "step":
        cmd_step(a.name, a.message, a.snapshot, a.goal, a.amend)
    elif a.cmd == "compare":
        cmd_compare(a.name, a.mockup, a.recipe, text=a.text, fit=a.fit, optimize=a.optimize, ceil=a.ceiling, fit_grid=a.fit_grid, chars=a.chars, widths_=a.widths, digits_=a.digits,
                    slack_=a.slack, split_=a.split, shift_=a.shift, fit_part_=a.fit_part, draft=a.draft_grid,
                    hex_=(a.hex[0], tuple(int(v) for v in a.hex[1].split(","))) if a.hex else None, quiet=a.quiet,
                    mirror_swap=a.mirror_swap, apply=a.apply, clean=a.clean, hot=a.hot, init_pal=a.init_palette, goal=a.goal, oracle_=a.oracle, min_gain=a.min_gain, ablate_=a.ablate, all_slots=a.all_slots, sweep_=a.sweep, sweep_parts=a.sweep_parts, labels_=a.labels, try_=a.try_)
    else:
        cmd_labels(a.anims)


if __name__ == "__main__":
    main()

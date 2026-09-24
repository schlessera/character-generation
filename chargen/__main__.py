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


def cmd_crops(name, recipes_, box):
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
    out = Image.new("RGBA", (len(FACINGS) * cw, len(paths) * ch), (60, 62, 80, 255))
    d = ImageDraw.Draw(out)
    for j, p in enumerate(paths):
        r = Recipe(p)
        for i, f in enumerate(FACINGS):
            im = Image.fromarray(render_frame(r, frames["idle"][f][0])).crop((6, y0, 6 + w, y1)).resize((w * s, h * s), Image.NEAREST)
            out.alpha_composite(im, (i * cw, j * ch))
        d.text((4, j * ch + 2), p.stem if j else "current", fill=(255, 255, 255, 255))
    dest = BUILD / "preview" / f"{name}_crops.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest)
    print(dest)


def cmd_heads(name):
    tpl = template()
    r = Recipe(CHARS / name / "recipe.toml")
    from .ascii import tone_ascii
    for facing in FACINGS:
        base = facing[:-2] if facing.endswith("_l") else facing
        t = np.pad(tpl.heads[base], HEAD_PAD)
        if facing.endswith("_l"):
            t = t[:, ::-1]
        ta = tone_ascii(t)
        g = r.grids.get(facing)
        print(f"[{facing}]  template | grid" + ("" if g is not None else "  (no grid)"))
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
                split_=False, shift_=False, fit_part_=None, draft=(), hex_=None, quiet=False):
    """Mockup (snapped to its pixel grid) above the render: whole figures, head close-ups,
    then heat maps of where the score is lost. `text` prints the given views as text,
    mockup | render in the recipe's palette letters; `fit` suggests palette moves."""
    from .mockup import (MOCKUP_FACINGS, breakdown, cost_maps, digits, draft_grid, extract, fit_part, grid_text, heat,
                         hex_box, palette_fit, palette_letters, place, shift_probe, similarity, slack, split, text_view,
                         widths)
    tpl = template()
    r = Recipe(Path(recipe) if recipe else CHARS / name / "recipe.toml")
    src = Path(mockup) if mockup else CHARS / name / "concept" / f"{name}-pixel-mockup.png"
    frames = build_frames(tpl)
    cell, gap = 32 * 12, 16
    sprites = extract(src)
    scores = []
    sheet = Image.new("RGBA", (gap + len(sprites) * (cell + gap), gap + 6 * (cell + gap)), (60, 62, 80, 255))
    parts: dict[str, list] = {}
    pal = palette_letters(r)
    pairs: dict[tuple, list] = {}
    part_pairs: dict[str, list] = {}
    from .mockup import quantize
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
            g = draft_grid(r, facing, placed, fr, chars=chars)
            print(f"== {facing}: drafted grid (nearest legend colour per cell; clean it by hand)")
            print(grid_text(g))
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
    if ceil:  # what this palette could reach with the mockup's exact shapes
        from .mockup import ceiling
        cs = [ceiling(sp, pal) for sp in sprites]
        print("ceiling    " + "  ".join(f"{f}={v:.3f}" for f, v in zip(MOCKUP_FACINGS, cs)) + f"  mean={np.mean(cs):.3f}")
    if fit_grid:  # trace the mockup with the head grids; prints the grids, applies nothing
        from .mockup import fit_grid as _fit, grid_text
        for facing in fit_grid:
            i = MOCKUP_FACINGS.index(facing)
            g, b, a = _fit(r, facing, sprites[i], frames[anim][facing][frame], render_frame, chars)
            print(f"fit-grid {facing}: {b:.3f} -> {a:.3f}")
            print(grid_text(g))
    if optimize:  # bounded palette search; prints the moves, applies nothing
        from .mockup import optimize_palette
        idle = [frames[anim][f][frame] for f in MOCKUP_FACINGS]
        moves = optimize_palette(r, sprites, lambda rec: [render_frame(rec, fr) for fr in idle])
        print("optimize: " + (", ".join(f"{a}.{b} {c} -> {d} (+{g:.3f})" for a, b, c, d, g in moves) or "no move gains"))
    print("similarity " + "  ".join(f"{f}={v:.4f}" for f, v in zip(MOCKUP_FACINGS, scores)) + f"  mean={np.mean(scores):.4f}")
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
    c.add_argument("--chars", help="legend characters --fit-grid may use (default: all)")
    a = ap.parse_args()
    if a.cmd == "build":
        cmd_build(a.names)
    elif a.cmd == "preview":
        cmd_preview(a.name, a.anims)
    elif a.cmd == "heads":
        cmd_heads(a.name)
    elif a.cmd == "crops":
        cmd_crops(a.name, a.recipe, tuple(int(v) for v in a.box.split(",")))
    elif a.cmd == "compare":
        cmd_compare(a.name, a.mockup, a.recipe, text=a.text, fit=a.fit, optimize=a.optimize, ceil=a.ceiling, fit_grid=a.fit_grid, chars=a.chars, widths_=a.widths, digits_=a.digits,
                    slack_=a.slack, split_=a.split, shift_=a.shift, fit_part_=a.fit_part, draft=a.draft_grid,
                    hex_=(a.hex[0], tuple(int(v) for v in a.hex[1].split(","))) if a.hex else None, quiet=a.quiet)
    else:
        cmd_labels(a.anims)


if __name__ == "__main__":
    main()

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


def cmd_compare(name, mockup=None, recipe=None, anim="idle", frame=0):
    """Mockup (snapped to its pixel grid) above the render: whole figures, then head close-ups."""
    from .mockup import MOCKUP_FACINGS, extract, place, similarity
    tpl = template()
    r = Recipe(Path(recipe) if recipe else CHARS / name / "recipe.toml")
    src = Path(mockup) if mockup else CHARS / name / "concept" / f"{name}-pixel-mockup.png"
    frames = build_frames(tpl)
    cell, gap = 32 * 12, 16
    sprites = extract(src)
    scores = []
    sheet = Image.new("RGBA", (gap + len(sprites) * (cell + gap), gap + 4 * (cell + gap)), (60, 62, 80, 255))
    for i, (sprite, facing) in enumerate(zip(sprites, MOCKUP_FACINGS)):
        rend = render_frame(r, frames[anim][facing][frame])
        scores.append(similarity(sprite, rend))
        heads = []
        for im in (sprite, rend):  # top 16 rows around the figure's center column
            ys = np.where(im[..., 3].any(1))[0]
            xs = np.where(im[..., 3].any(0))[0]
            cx = (xs[0] + xs[-1]) // 2
            heads.append(Image.fromarray(im).crop((cx - 8, ys[0], cx + 8, ys[0] + 16)))
        cells = [Image.fromarray(place(sprite, rend)), Image.fromarray(rend)] + heads
        for j, im in enumerate(cells):
            sheet.alpha_composite(im.resize((cell, cell), Image.NEAREST), (gap + i * (cell + gap), gap + j * (cell + gap)))
    out = BUILD / "preview" / f"{name}_compare.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out)
    print("similarity " + "  ".join(f"{f}={v:.3f}" for f, v in zip(MOCKUP_FACINGS, scores)) + f"  mean={np.mean(scores):.3f}")


def main():
    ap = argparse.ArgumentParser(prog="chargen")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("names", nargs="*")
    p = sub.add_parser("preview"); p.add_argument("name"); p.add_argument("anims", nargs="*")
    h = sub.add_parser("heads"); h.add_argument("name")
    lb = sub.add_parser("labels"); lb.add_argument("anims", nargs="*")
    c = sub.add_parser("compare"); c.add_argument("name"); c.add_argument("--mockup"); c.add_argument("--recipe")
    a = ap.parse_args()
    if a.cmd == "build":
        cmd_build(a.names)
    elif a.cmd == "preview":
        cmd_preview(a.name, a.anims)
    elif a.cmd == "heads":
        cmd_heads(a.name)
    elif a.cmd == "compare":
        cmd_compare(a.name, a.mockup, a.recipe)
    else:
        cmd_labels(a.anims)


if __name__ == "__main__":
    main()

"""Hand-authored pixel sprites: one text file per sprite, one palette char per pixel.

  python -m chargen.pixeltool draft NAME...    rough draft from the generated reference art
                                               (block-mode downscale snapped to the palette)
  python -m chargen.pixeltool render NAME... [-o out.png]
      reference art | sprite at 12x | sprite next to the character at 4x (true game scale)
  python -m chargen.pixeltool check [NAME...]  size / palette validation
  python -m chargen.pixeltool rebase NAME... [--ref REV]
      after repainting frame 0 of an animated prop: rebuild frames 1.. as the new frame 0
      plus each frame's own changes (where it differed from frame 0 at git REV, default HEAD)

Files: assets/props/pixel/NAME.txt. Line 1: "# NAME WxH", then H rows of W chars.
"""
from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .catalog import ROOT
from .props import SRC, cut_cells, quantize_sheet, resample

PIX = SRC / "pixel"
PREVIEW = ROOT / "build/pixel"


def palette() -> dict[str, tuple[int, int, int]]:
    cols = tomllib.loads((SRC / "palette.toml").read_text())["colors"]
    return {k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) for k, v in cols.items()}


def manifest() -> dict[str, dict]:
    """name -> item (w, h, kind, ...) plus where its reference art lives."""
    man = tomllib.loads((SRC / "props.toml").read_text())
    out = {}
    for si, sheet in enumerate(man["sheets"]):
        for name, it in sheet["items"].items():
            if sheet.get("kind") == "tiles":
                out[name] = {"w": sheet["tile"], "h": sheet["tile"], "kind": "tile", "cell": it, "sheet": si}
            else:
                out[name] = {**it, "sheet": si}
    return out, man


def reference(name: str) -> np.ndarray:
    items, man = manifest()
    it = items[name]
    sheet = man["sheets"][it["sheet"]]
    img = np.array(Image.open(SRC / "source" / sheet["file"]).convert("RGBA"))
    if it["kind"] == "tile":
        r, c = it["cell"]
        H, W = img.shape[:2]
        ch, cw = H // sheet["rows"], W // sheet["cols"]
        return img[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw]
    amin = sheet.get("alpha_min", 180)
    boxes = cut_cells(img, sheet["cols"], sheet["rows"], amin, 4)
    y0, y1, x0, x1 = boxes[tuple(it["cell"])]
    crop = img[y0:y1, x0:x1].copy()
    crop[crop[..., 3] < amin, 3] = 0
    return crop


def size(name: str) -> tuple[int, int]:
    items, _ = manifest()
    it = items[name]
    if "h" in it:
        return it["w"], it["h"]
    ref = reference(name)
    return it["w"], max(1, round(it["w"] * ref.shape[0] / ref.shape[1]))


def frame_names(name: str) -> list[str]:
    """['fire_barrel', 'fire_barrel@1', ...] according to the item's `anim` timings."""
    n = len(manifest()[0][name].get("anim", [0]))
    return [name] + [f"{name}@{k}" for k in range(1, n)]


def read(name: str) -> np.ndarray:
    lines = (PIX / f"{name}.txt").read_text().splitlines()
    rows = [l for l in lines if l and not l.startswith("# ")]
    return np.array([list(r) for r in rows], "<U1")


def to_rgba(grid: np.ndarray, overrides: dict | None = None) -> np.ndarray:
    """Palette chars -> RGBA. `overrides` ({char: "#rrggbb"}) recolors chars, e.g. car paint."""
    pal = palette()
    for k, v in (overrides or {}).items():
        pal[k] = tuple(int(v[i:i + 2], 16) for i in (1, 3, 5))
    out = np.zeros(grid.shape + (4,), np.uint8)
    for k, c in pal.items():
        out[grid == k] = (*c, 255)
    return out


def draft_pixels(name: str) -> np.ndarray:
    """Automatic draft: the reference downscaled to the sprite size and snapped to the palette.
    This is only a starting point (and the \"why not just resample\" example in the README)."""
    w, h = size(name)
    ref = reference(name)
    items, _ = manifest()
    is_tile = items[name]["kind"] == "tile"
    if is_tile:
        small = np.array(Image.fromarray(ref[..., :3]).resize((w, h), Image.BOX))
        alpha = np.full((h, w), 255)
    else:
        rs = resample(quantize_sheet(ref, 128, 48), w, h, 128)
        small, alpha = rs[..., :3], rs[..., 3]
    pal = palette()
    keys = [k for k in pal if k != "#"] + ["#"]
    cols = np.array([pal[k] for k in keys], np.float32)
    d = ((small[..., None, :].astype(np.float32) - cols) ** 2 * np.array([0.3, 0.59, 0.11])).sum(-1)
    grid = np.array(keys)[d.argmin(-1)]
    grid[alpha == 0] = "."
    if not is_tile:  # 1px outline around the silhouette
        op = grid != "."
        p = np.pad(op, 1)
        edge = op & ~(p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:])
        grid[edge] = "#"
    return grid


def draft(name: str) -> Path:
    grid = draft_pixels(name)
    h, w = grid.shape
    PIX.mkdir(parents=True, exist_ok=True)
    path = PIX / f"{name}.txt"
    path.write_text(f"# {name} {w}x{h}\n" + "\n".join("".join(r) for r in grid) + "\n")
    return path


def check(names: list[str]) -> list[str]:
    pal = set(palette()) | {"."}
    errs = []
    for n in [f for name in names for f in frame_names(name)]:
        try:
            g = read(n)
        except Exception as e:  # noqa: BLE001
            errs.append(f"{n}: unreadable ({e})")
            continue
        w, h = size(n.split("@")[0])
        if g.shape != (h, w):
            errs.append(f"{n}: is {g.shape[1]}x{g.shape[0]}, expected {w}x{h}")
        bad = set(np.unique(g)) - pal
        if bad:
            errs.append(f"{n}: unknown chars {sorted(bad)}")
    return errs


def render(names: list[str], out: Path) -> Path:
    char = ROOT / "web/data/characters/juno/sheet.png"
    juno = Image.open(char).crop((0, 0, 32, 32)) if char.exists() else None
    panels = []
    for n in names:
        spr = Image.fromarray(to_rgba(read(n)))
        ref = Image.fromarray(reference(n))
        H = 12 * spr.height
        refp = ref.resize((max(1, ref.width * H // ref.height), H), Image.LANCZOS)
        big = spr.resize((spr.width * 12, H), Image.NEAREST)
        if manifest()[0][n]["kind"] == "tile":  # 3x3 repeat shows seams
            scene = Image.new("RGBA", (spr.width * 3 + 36, spr.height * 3), (32, 32, 46, 255))
            for ty in range(3):
                for tx in range(3):
                    scene.alpha_composite(spr, (tx * spr.width, ty * spr.height))
            if juno:
                scene.alpha_composite(juno, (spr.width * 3 + 2, scene.height - 32))
        else:
            scene = Image.new("RGBA", (spr.width + 40, max(spr.height, 32) + 4), (32, 32, 46, 255))
            scene.alpha_composite(spr, (2, scene.height - spr.height - 2))
            if juno:
                scene.alpha_composite(juno, (spr.width + 6, scene.height - 34))
        scene = scene.resize((scene.width * 4, scene.height * 4), Image.NEAREST)
        w = refp.width + big.width + scene.width + 40
        h = max(H, scene.height) + 20
        panel = Image.new("RGBA", (w, h), (24, 24, 34, 255))
        panel.alpha_composite(refp, (5, 18))
        panel.alpha_composite(big, (refp.width + 15, 18))
        panel.alpha_composite(scene, (refp.width + big.width + 30, 18))
        ImageDraw.Draw(panel).text((5, 3), f"{n}  {spr.width}x{spr.height}", fill=(220, 220, 230, 255))
        panels.append(panel)
    W = max(p.width for p in panels)
    im = Image.new("RGBA", (W, sum(p.height for p in panels)), (24, 24, 34, 255))
    y = 0
    for p in panels:
        im.alpha_composite(p, (0, y))
        y += p.height
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return out


def main():
    ap = argparse.ArgumentParser(prog="pixeltool")
    ap.add_argument("cmd", choices=["draft", "render", "check", "floor", "frames", "anim", "rebase"])
    ap.add_argument("names", nargs="*")
    ap.add_argument("-o", "--out")
    ap.add_argument("--force", action="store_true", help="draft: overwrite existing files")
    ap.add_argument("--ref", default="HEAD", help="rebase: git revision holding the old frames")
    a = ap.parse_args()
    names = a.names or sorted(manifest()[0])
    if a.cmd == "draft":
        for n in names:
            if (PIX / f"{n}.txt").exists() and not a.force:
                print(f"{n}: exists, skipped (use --force)")
                continue
            print(draft(n))
    elif a.cmd == "check":
        errs = check(names)
        print("\n".join(errs) if errs else f"ok ({len(names)} sprites)")
        sys.exit(1 if errs else 0)
    elif a.cmd == "frames":
        for n in names:
            for f in frame_names(n)[1:]:
                p = PIX / f"{f}.txt"
                if p.exists() and not a.force:
                    print(f"{f}: exists, skipped (use --force)")
                    continue
                p.write_text((PIX / f"{n}.txt").read_text().replace(f"# {n} ", f"# {f} ", 1))
                print(p)
    elif a.cmd == "rebase":
        for n in a.names:
            for p in rebase(n, a.ref):
                print(p)
    elif a.cmd == "anim":
        print(render_anim(names, Path(a.out) if a.out else PREVIEW / f"{names[0]}_anim.png"))
    elif a.cmd == "floor":
        print(floor(a.names, Path(a.out) if a.out else PREVIEW / "floor.png"))
    else:
        print(render(names, Path(a.out) if a.out else PREVIEW / f"{names[0]}.png"))


def _grid_at(name: str, rev: str) -> np.ndarray:
    import subprocess
    rel = (PIX / f"{name}.txt").relative_to(ROOT)
    text = subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    rows = [l for l in text.splitlines() if l and not l.startswith("# ")]
    return np.array([list(r) for r in rows], "<U1")


def rebase(name: str, rev: str = "HEAD") -> list[Path]:
    """Frames k>0 = the current frame 0, plus the pixels where frame k differed from frame 0
    at `rev`. Repaint frame 0 freely (texture, wear), then rebase to carry the motion over."""
    new0 = read(name)
    old0 = _grid_at(name, rev)
    out = []
    for f in frame_names(name)[1:]:
        oldk = _grid_at(f, rev)
        moved = oldk != old0
        grid = np.where(moved, oldk, new0)
        p = PIX / f"{f}.txt"
        header = p.read_text().splitlines()[0]
        p.write_text(header + "\n" + "\n".join("".join(r) for r in grid) + "\n")
        out.append(p)
    return out


def render_anim(names: list[str], out: Path) -> Path:
    """Per sprite: every frame at 10x with pixels that differ from frame 0 marked by a
    corner dot, then all frames at 3x in the game-scale row. Also writes an animated GIF."""
    rows = []
    items, _ = manifest()
    for n in names:
        fr = [to_rgba(read(f)) for f in frame_names(n)]
        ms = items[n].get("anim", [0])
        base = fr[0]
        s = 10
        h, w = base.shape[:2]
        row = Image.new("RGBA", (len(fr) * (w * s + 10) + 10, h * s + 30), (24, 24, 34, 255))
        d = ImageDraw.Draw(row)
        for k, f in enumerate(fr):
            x0 = 10 + k * (w * s + 10)
            big = Image.new("RGBA", (w * s, h * s), (40, 40, 56, 255))
            big.alpha_composite(Image.fromarray(f).resize((w * s, h * s), Image.NEAREST))
            row.alpha_composite(big, (x0, 22))
            diff = np.any(f != base, axis=-1)
            for yy, xx in zip(*np.nonzero(diff)):
                d.rectangle([x0 + xx * s, 22 + yy * s, x0 + xx * s + 2, 22 + yy * s + 2], fill=(255, 255, 0, 255))
            d.text((x0, 6), f"{n} f{k} {ms[k] if k < len(ms) else '?'}ms  changed={int(diff.sum())}", fill=(220, 220, 230, 255))
        rows.append(row)
        gif = [Image.fromarray(f).resize((w * 6, h * 6), Image.NEAREST) for f in fr]
        bg = [Image.new("RGBA", g.size, (32, 32, 46, 255)) for g in gif]
        for b_, g in zip(bg, gif):
            b_.alpha_composite(g)
        bg[0].save(out.parent / f"{n}.gif", save_all=True, append_images=bg[1:], duration=ms, loop=0, disposal=2)
    W = max(r.width for r in rows)
    im = Image.new("RGBA", (W, sum(r.height for r in rows)), (24, 24, 34, 255))
    y = 0
    for r in rows:
        im.alpha_composite(r, (0, y))
        y += r.height
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return out


def floor(names: list[str], out: Path) -> Path:
    """Random 12x8 patch mixing the given tiles, at 4x: shows repetition and seams."""
    tiles = [to_rgba(read(n)) for n in names]
    rng = np.random.default_rng(1)
    T = tiles[0].shape[0]
    patch = np.zeros((8 * T, 12 * T, 4), np.uint8)
    for ty in range(8):
        for tx in range(12):
            patch[ty * T:(ty + 1) * T, tx * T:(tx + 1) * T] = tiles[rng.integers(len(tiles))]
    im = Image.fromarray(patch)
    im = im.resize((im.width * 4, im.height * 4), Image.NEAREST)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return out


if __name__ == "__main__":
    main()

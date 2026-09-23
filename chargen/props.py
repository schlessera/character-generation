"""Prop and tile assets.

Sprites are hand-drawn pixel files (assets/props/pixel/*.txt, see chargen/pixeltool.py and
docs/pixel-art.md). The image-gen sheets in assets/props/source/ are design references:
the helpers here cut an object out of a sheet and make a rough palette draft from it
(`pixeltool draft`) that the pixel artist then redraws.
Output of build(): web/data/props/atlas.png + atlas.json (sprites, tiles, collision footprints),
atlas_emissive.png, and a labeled preview in build/preview/props.png.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from .catalog import ROOT

SRC = ROOT / "assets/props"
OUT = ROOT / "web/data/props"
PREVIEW_DIR = ROOT / "build/preview"


def _components(mask: np.ndarray) -> np.ndarray:
    """8-connected component labels (iterative flood fill, no scipy dependency)."""
    H, W = mask.shape
    lab = np.zeros((H, W), np.int32)
    n = 0
    for y0, x0 in zip(*np.nonzero(mask)):
        if lab[y0, x0]:
            continue
        n += 1
        stack = [(y0, x0)]
        lab[y0, x0] = n
        while stack:
            y, x = stack.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and mask[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = n
                        stack.append((yy, xx))
    return lab


def _dilate(m: np.ndarray, r: int) -> np.ndarray:
    out = m.copy()
    for _ in range(r):
        p = np.pad(out, 1)
        out = p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return out


def cut_cells(img: np.ndarray, cols: int, rows: int, alpha_min: int, merge: int) -> dict[tuple[int, int], tuple]:
    """Return {(row, col): (y0, y1, x0, x1)} bounding boxes of the object in each grid cell."""
    H, W = img.shape[:2]
    mask = img[..., 3] >= alpha_min
    # components on a downsampled, dilated mask: fast and merges sparks/debris into their object
    s = 4
    small = mask[: H // s * s, : W // s * s].reshape(H // s, s, W // s, s).any(axis=(1, 3))
    lab = _components(_dilate(small, max(1, merge // s)))
    boxes: dict[tuple[int, int], list] = {}
    for k in range(1, lab.max() + 1):
        ys, xs = np.nonzero(lab == k)
        if len(ys) < 12:
            continue
        cy, cx = ys.mean() * s, xs.mean() * s
        cell = (int(cy // (H / rows)), int(cx // (W / cols)))
        b = [ys.min() * s, (ys.max() + 1) * s, xs.min() * s, (xs.max() + 1) * s]
        if cell in boxes:  # several blobs in one cell belong to the same object
            o = boxes[cell]
            b = [min(o[0], b[0]), max(o[1], b[1]), min(o[2], b[2]), max(o[3], b[3])]
        boxes[cell] = b
    # tighten to the real (full-res) mask
    out = {}
    for cell, (y0, y1, x0, x1) in boxes.items():
        m = mask[y0:y1, x0:x1]
        ys, xs = np.nonzero(m)
        out[cell] = (y0 + ys.min(), y0 + ys.max() + 1, x0 + xs.min(), x0 + xs.max() + 1)
    return out


def resample(crop: np.ndarray, w: int, h: int, alpha_min: int) -> np.ndarray:
    """Block-mode downscale: each output pixel takes the most common (coarsely binned)
    opaque color of its source block; transparent if most of the block is transparent."""
    H, W = crop.shape[:2]
    out = np.zeros((h, w, 4), np.uint8)
    ys = np.linspace(0, H, h + 1).astype(int)
    xs = np.linspace(0, W, w + 1).astype(int)
    for j in range(h):
        for i in range(w):
            blk = crop[ys[j]:ys[j + 1], xs[i]:xs[i + 1]].reshape(-1, 4)
            op = blk[blk[:, 3] >= alpha_min]
            if len(op) * 2 < len(blk):
                continue
            code = (op[:, 0].astype(np.int32) << 16) | (op[:, 1].astype(np.int32) << 8) | op[:, 2]
            vals, counts = np.unique(code, return_counts=True)
            v = int(vals[counts.argmax()])
            out[j, i, :3] = (v >> 16, (v >> 8) & 255, v & 255)
            out[j, i, 3] = 255
    return out


def quantize_sheet(img: np.ndarray, alpha_min: int, n: int) -> np.ndarray:
    """Palette-reduce a whole source sheet at full resolution. Doing this before the
    downscale makes the block-mode pick real, saturated colors instead of averages."""
    op = img[..., 3] >= min(alpha_min, 100)
    strip = Image.fromarray(img[op][:, :3].reshape(1, -1, 3))
    pal = strip.quantize(colors=n, method=Image.Quantize.MEDIANCUT, kmeans=2, dither=Image.Dither.NONE)
    q = np.array(Image.fromarray(img[..., :3]).quantize(palette=pal, dither=Image.Dither.NONE).convert("RGB"))
    out = img.copy()
    out[..., :3] = q
    return out






def build() -> Path:
    """Pack the hand-drawn sprites (assets/props/pixel/*.txt) into the atlas. The source
    sheets are design references only; they never reach the game."""
    from .pixeltool import frame_names, manifest, read, to_rgba
    items, man = manifest()
    tile_em = next((sh.get("emissive_tiles", {}) for sh in man["sheets"] if sh.get("kind") == "tiles"), {})
    sprites, meta, tiles, emissive = {}, {}, {}, {}
    for name, it in items.items():
        if it["kind"] == "tile":
            g = read(name)
            tiles[name] = to_rgba(g)
            emissive[name] = _emissive(g, tile_em.get(name, ""))
            continue
        chars = it.get("emissive", "MnZxyY" if it.get("glow") else "")
        m = {k: v for k, v in it.items() if k not in ("cell", "sheet", "alpha_min", "outline", "emissive", "variants")}
        # the default look plus one sprite set per palette variant: NAME, NAME_VARIANT
        for vname, over in [("", None)] + list(it.get("variants", {}).items()):
            out = f"{name}_{vname}" if vname else name
            for k, f in enumerate(frame_names(name)):
                g = read(f)
                key = out if k == 0 else f"{out}@{k}"
                sprites[key] = to_rgba(g, over)
                emissive[key] = _emissive(g, chars)
            meta[out] = {**m, **({"variant_of": name} if vname else {})}
    return _pack(sprites, meta, tiles, emissive)


def _emissive(grid: np.ndarray, chars: str) -> np.ndarray:
    """Only the self-lit pixels (neon, fire): drawn unlit on top of the lit scene."""
    from .pixeltool import to_rgba
    px = to_rgba(grid)
    px[~np.isin(grid, list(chars))] = 0
    return px


def _pack(sprites, meta, tiles, emissive) -> Path:
    """Shelf-pack tiles (first row) and sprites into one atlas."""
    items = [("tile", k, v) for k, v in tiles.items()] + \
            sorted([("sprite", k, v) for k, v in sprites.items()], key=lambda t: -t[2].shape[0])
    W, pad = 512, 1
    x = y = shelf = 0
    pos = []
    for kind, k, im in items:
        h, w = im.shape[:2]
        if x + w > W:
            x, y, shelf = 0, y + shelf + pad, 0
        pos.append((kind, k, x, y, w, h))
        x += w + pad
        shelf = max(shelf, h)
    atlas = np.zeros((y + shelf, W, 4), np.uint8)
    glow = np.zeros_like(atlas)
    out = {"tiles": {}, "sprites": {}}
    for (kind, k, x, y, w, h), (_, _, im) in zip(pos, items):
        atlas[y:y + h, x:x + w] = im
        glow[y:y + h, x:x + w] = emissive[k]
        if kind == "tile":
            out["tiles"][k] = {"x": x, "y": y, "w": w, "h": h}
        else:
            base, _, idx = k.partition("@")
            spr = out["sprites"].setdefault(base, {"w": w, "h": h, **meta[base], "frames": []})
            spr["frames"].append((int(idx or 0), {"x": x, "y": y}))
    for spr in out["sprites"].values():  # frames in order; frame 0 also as x/y for static use
        spr["frames"] = [f for _, f in sorted(spr["frames"], key=lambda t: t[0])]
        spr.update(spr["frames"][0])
    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(atlas).save(OUT / "atlas.png")
    Image.fromarray(glow).save(OUT / "atlas_emissive.png")
    (OUT / "atlas.json").write_text(json.dumps(out, indent=1))
    return OUT


def preview(scale: int = 4, width: int = 400) -> Path:
    """All sprites and tiles on a dark floor at `scale`x, next to the character for size.

    Sprites are shelf-packed: each gets a cell as wide as itself (or its label), rows wrap at
    `width` px and are as tall as their tallest sprite, so big sprites never overlap others."""
    from PIL import ImageDraw
    atlas = Image.open(OUT / "atlas.png")
    meta = json.loads((OUT / "atlas.json").read_text())
    char = ROOT / "web/data/characters/juno/sheet.png"
    items = [(k, atlas.crop((s["x"], s["y"], s["x"] + s["w"], s["y"] + s["h"])))  # frame 0 of each sprite
             for k, s in meta["sprites"].items()]
    items.sort(key=lambda it: -it[1].height)  # similar sizes share a row
    if char.exists():
        items.insert(0, ("juno", Image.open(char).crop((0, 0, 32, 32))))
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    label_h, gap = 4, 6  # px at 1x: label line above each sprite, space between cells
    place, x, y, row_h = [], gap, 0, 0
    tiles = list(meta["tiles"].items())
    top = ((len(tiles) + 11) // 12) * 18 + 4
    y = top
    for k, spr in items:
        w = max(spr.width, int(probe.textlength(k) / scale) + 2)
        if x + w > width - gap and x > gap:
            x, y, row_h = gap, y + row_h + label_h + gap, 0
        place.append((k, spr, x, y, w))
        x += w + gap
        row_h = max(row_h, spr.height)
    rows_end = {}
    for k, spr, px, py, w in place:  # bottom-align sprites within their row
        rows_end[py] = max(rows_end.get(py, 0), spr.height)
    H = max(py + label_h + rows_end[py] for _, _, _, py, _ in place) + gap
    im = Image.new("RGBA", (width, H), (30, 29, 38, 255))
    for i, (k, t) in enumerate(tiles):
        im.alpha_composite(atlas.crop((t["x"], t["y"], t["x"] + 16, t["y"] + 16)), ((i % 12) * 18 + 2, (i // 12) * 18 + 2))
    for k, spr, px, py, w in place:
        im.alpha_composite(spr, (px + (w - spr.width) // 2, py + label_h + rows_end[py] - spr.height))
    big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    d = ImageDraw.Draw(big)
    for k, spr, px, py, w in place:
        d.text((px * scale, py * scale - 2), k, fill=(170, 170, 190, 255))
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    p = PREVIEW_DIR / "props.png"
    big.save(p)
    return p


if __name__ == "__main__":
    print(build())
    print(preview())

"""Label editing helpers.

  python -m chargen.labeltool check [FRAME...]    validate label files (all if none given)
  python -m chargen.labeltool render FRAME... -o out.png
      side-by-side: original | label colors | label colors over original, 12x zoom
  python -m chargen.labeltool zoom [FRAME...]
      16x zoomed frame with a pixel grid and axis numbers -> build/frames_zoom/NNN.png
      (the reference a human or agent looks at while labeling)
"""
from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import catalog
from .labels import canonical_frames, read_labels

LABEL_COLORS = {
    "H": (240, 200, 160), "N": (200, 150, 110), "T": (60, 120, 230),
    "R": (230, 60, 60), "r": (255, 170, 170), "L": (60, 200, 90), "l": (170, 255, 190),
    "P": (180, 70, 200), "p": (240, 170, 255), "Q": (230, 180, 40), "q": (255, 235, 150),
    "X": (40, 230, 230), ".": (0, 0, 0),
}
CACHE = catalog.ROOT / "build/cache"


def template(size: str = "16x32") -> catalog.Template:
    """Catalog load is ~2s (head fitting); cache it keyed on the source file mtime."""
    src = catalog.RAW / size / f"{size} All Animations.aseprite"
    p = CACHE / f"template_{size}.pkl"
    if p.exists() and p.stat().st_mtime > max(src.stat().st_mtime, Path(catalog.__file__).stat().st_mtime):
        return pickle.loads(p.read_bytes())
    tpl = catalog.load(size)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(pickle.dumps(tpl))
    return tpl


def label_rgba(lab: np.ndarray) -> np.ndarray:
    out = np.zeros(lab.shape + (4,), np.uint8)
    for k, c in LABEL_COLORS.items():
        if k != ".":
            out[lab == k] = (*c, 255)
    return out


def render(tpl, frames: list[int], scale: int = 12) -> Image.Image:
    w = tpl.w * scale
    im = Image.new("RGBA", (3 * w + 40, len(frames) * (w + 20)), (50, 52, 66, 255))
    d = ImageDraw.Draw(im)
    for r, i in enumerate(frames):
        lab = read_labels(tpl, i)
        orig = tpl.rgba[i]
        lc = label_rgba(lab)
        mix = orig.copy()
        m = lab != "."
        mix[m, :3] = (orig[m, :3] * 0.45 + lc[m, :3] * 0.55).astype(np.uint8)
        y = r * (w + 20) + 16
        d.text((4, y - 14), f"frame {i}", fill=(230, 230, 230, 255))
        for c, arr in enumerate([orig, lc, mix]):
            im.alpha_composite(Image.fromarray(arr).resize((w, w), Image.NEAREST), (10 + c * (w + 10), y))
    return im


def zoom(tpl, frames: list[int], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    s = 16
    for i in frames:
        im = Image.new("RGBA", (tpl.w * s + 24, tpl.h * s + 24), (60, 62, 80, 255))
        im.alpha_composite(Image.fromarray(tpl.rgba[i]).resize((tpl.w * s, tpl.h * s), Image.NEAREST), (24, 24))
        d = ImageDraw.Draw(im)
        for k in range(tpl.w + 1):
            c = (110, 110, 140, 255) if k % 4 else (170, 170, 200, 255)
            d.line([(24 + k * s, 24), (24 + k * s, 24 + tpl.h * s)], fill=c)
            d.line([(24, 24 + k * s), (24 + tpl.w * s, 24 + k * s)], fill=c)
        for k in range(0, tpl.w, 2):
            d.text((24 + k * s + 3, 6), str(k), fill=(220, 220, 220, 255))
            d.text((2, 24 + k * s + 3), str(k), fill=(220, 220, 220, 255))
        im.save(out_dir / f"{i:03d}.png")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "render", "zoom"])
    ap.add_argument("frames", nargs="*", type=int)
    ap.add_argument("-o", "--out", default="build/labels_preview.png")
    ap.add_argument("--size", default="16x32")
    a = ap.parse_args(argv)
    tpl = template(a.size)
    canon = canonical_frames(tpl)
    frames = a.frames or sorted(set(canon))
    frames = [canon[i] for i in frames]
    if a.cmd == "check":
        from .labels import validate
        errs = [e for e in validate(tpl) if int(e.split(":")[0]) in frames]
        print("\n".join(errs) if errs else f"ok ({len(frames)} frames)")
        sys.exit(1 if errs else 0)
    if a.cmd == "zoom":
        zoom(tpl, frames, catalog.ROOT / "build/frames_zoom")
        print(f"build/frames_zoom/ ({len(frames)} frames)")
        return
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    render(tpl, frames).save(a.out)
    print(a.out)


if __name__ == "__main__":
    main()

"""Compare a rendered character against its pixel mockup.

The mockup (image generation, see characters/<name>/concept/) is "pixel art" painted at
roughly 9 screen pixels per art pixel, with the five right-facing views stacked
vertically. `extract` snaps it back onto its art-pixel grid, so it can be shown next to
the rendered sprite at the same scale: the side-by-side that drives every fidelity pass.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

MOCKUP_FACINGS = ["down", "down_side", "side", "up_side", "up"]


def _pitch(im: np.ndarray) -> float:
    """Art-pixel size in screen pixels, from the dominant period of color edges."""
    edges = (np.abs(np.diff(im, axis=1)).sum(2) > 60).sum(0).astype(float)
    spec = np.abs(np.fft.rfft(edges - edges.mean()))
    lo = int(len(edges) / 16)  # search pitches between 4 and 16 px
    hi = int(len(edges) / 4)
    k = lo + int(np.argmax(spec[lo:hi + 1]))
    return len(edges) / k


def _segments(mask: np.ndarray, gap: int = 5) -> list[tuple[int, int]]:
    ys = np.where(mask)[0]
    segs, start, prev = [], ys[0], ys[0]
    for y in ys[1:]:
        if y > prev + gap:
            segs.append((start, prev))
            start = y
        prev = y
    segs.append((start, prev))
    return segs


def extract(path) -> list[np.ndarray]:
    """One RGBA sprite per stacked figure, top to bottom, at art-pixel resolution."""
    im = np.asarray(Image.open(path).convert("RGB")).astype(int)
    bg = im[5, 5]
    fg = np.abs(im - bg).sum(2) > 40
    p = _pitch(im)
    sprites = []
    for a, b in _segments(fg.any(1)):
        xs = np.where(fg[a:b + 1].any(0))[0]
        x0, x1 = xs[0], xs[-1]
        best = None
        for py in np.arange(0, p, 0.5):  # grid phase with the most uniform cells
            for px in np.arange(0, p, 0.5):
                ny, nx = int((b - a + 1 - py) / p), int((x1 - x0 + 1 - px) / p)
                cy = (a + py + (np.arange(ny) + 0.5) * p).astype(int)
                cx = (x0 + px + (np.arange(nx) + 0.5) * p).astype(int)
                blocks = np.stack([im[cy[:, None] + dy, cx[None, :] + dx]
                                   for dy in range(-2, 3) for dx in range(-2, 3)])
                score = blocks.std(0).sum()
                if best is None or score < best[0]:
                    best = (score, np.median(blocks, 0))
        rgb = best[1].astype(np.uint8)
        rgba = np.zeros(rgb.shape[:2] + (4,), np.uint8)
        rgba[..., :3] = rgb
        rgba[..., 3] = (np.abs(rgb.astype(int) - bg).sum(2) > 40) * 255
        sprites.append(rgba)
    return sprites


def place(sprite: np.ndarray, like: np.ndarray) -> np.ndarray:
    """The mockup sprite on a frame-sized canvas, feet and center aligned with `like`."""
    H, W = like.shape[:2]
    h, w = sprite.shape[:2]
    ys = np.where(like[..., 3].any(1))[0]
    xs = np.where(like[..., 3].any(0))[0]
    oy = ys[-1] + 1 - h
    ox = int(round((xs[0] + xs[-1]) / 2 - w / 2)) + 1
    out = np.zeros((H, W, 4), np.uint8)
    for y in range(h):
        for x in range(w):
            if 0 <= oy + y < H and 0 <= ox + x < W and sprite[y, x, 3]:
                out[oy + y, ox + x] = sprite[y, x]
    return out


def _redmean(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cheap perceptual RGB distance, 0..~765."""
    a, b = a.astype(float), b.astype(float)
    r = (a[..., 0] + b[..., 0]) / 2
    d = a - b
    return np.sqrt((2 + r / 256) * d[..., 0] ** 2 + 4 * d[..., 1] ** 2 + (2 + (255 - r) / 256) * d[..., 2] ** 2)


def _cost(src: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """Per opaque `src` pixel: its best match among `ref`'s 3x3 neighborhood (0 = same
    color, 1 = missing or clearly different)."""
    H, W = src.shape[:2]
    pad = np.pad(ref, ((1, 1), (1, 1), (0, 0)))
    best = np.ones((H, W))
    for dy in range(3):
        for dx in range(3):
            n = pad[dy:dy + H, dx:dx + W]
            c = np.where(n[..., 3] > 0, np.minimum(1, _redmean(src[..., :3], n[..., :3]) / 150), 1)
            best = np.minimum(best, c)
    return best[src[..., 3] > 0]


def similarity(sprite: np.ndarray, render: np.ndarray) -> float:
    """0..1 match between the mockup view and the render, best over +-1 px shifts.

    Symmetric: every opaque pixel of either image looks for a same-colored pixel within
    one pixel in the other; a missing or clearly different one costs 1. Tolerant of
    one-pixel drift but not of wrong shapes or colors. The mockup's head is taller than
    the template's, so 1.0 is unreachable; the trend between versions is what matters.
    """
    base = place(sprite, render)
    best = 0.0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            m = np.roll(base, (dy, dx), axis=(0, 1))
            c1, c2 = _cost(m, render), _cost(render, m)
            best = max(best, 1 - (c1.sum() + c2.sum()) / max(len(c1) + len(c2), 1))
    return best

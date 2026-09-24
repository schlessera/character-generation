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


def _cost_map(src: np.ndarray, ref: np.ndarray) -> np.ndarray:
    """Per pixel: the best match of `src` among `ref`'s 3x3 neighborhood (0 = same color,
    1 = missing or clearly different); 0 where `src` is transparent."""
    H, W = src.shape[:2]
    pad = np.pad(ref, ((1, 1), (1, 1), (0, 0)))
    best = np.ones((H, W))
    for dy in range(3):
        for dx in range(3):
            n = pad[dy:dy + H, dx:dx + W]
            c = np.where(n[..., 3] > 0, np.minimum(1, _redmean(src[..., :3], n[..., :3]) / 150), 1)
            best = np.minimum(best, c)
    return np.where(src[..., 3] > 0, best, 0)


def _cost(src: np.ndarray, ref: np.ndarray) -> np.ndarray:
    return _cost_map(src, ref)[src[..., 3] > 0]


def cost_maps(sprite: np.ndarray, render: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(mockup placed at the best shift, cost of each render pixel, cost of each mockup pixel).

    The per-pixel view of `similarity`: where the render loses score, and where the mockup
    has pixels the render never matches. Used by `compare`'s heat-map rows."""
    base = place(sprite, render)
    best = None
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            m = np.roll(base, (dy, dx), axis=(0, 1))
            cr, cm = _cost_map(render, m), _cost_map(m, render)
            n = (render[..., 3] > 0).sum() + (m[..., 3] > 0).sum()
            s = 1 - (cr.sum() + cm.sum()) / max(n, 1)
            if best is None or s > best[0]:
                best = (s, m, cr, cm)
    return best[1], best[2], best[3]


def heat(cost: np.ndarray, under: np.ndarray) -> np.ndarray:
    """RGBA heat map: the image `under` dimmed, with its cost painted red on top."""
    out = under.copy()
    a = under[..., 3] > 0
    out[a, :3] = (under[a, :3] * 0.35).astype(np.uint8)
    c = np.clip(cost, 0, 1)
    out[a, 0] = np.clip(out[a, 0] + c[a] * 220, 0, 255).astype(np.uint8)
    out[a, 1] = np.clip(out[a, 1] + c[a] * 40, 0, 255).astype(np.uint8)
    return out


def breakdown(cost_render: np.ndarray, cost_mockup: np.ndarray, labels: np.ndarray,
              render: np.ndarray, mockup: np.ndarray) -> dict[str, tuple[float, float, int]]:
    """Per label group: (render-side loss, mockup-side loss, pixels), the losses in score
    points (so all groups sum to 1 - similarity). A mockup pixel takes the label of the
    render pixel under it, or, off the render, of the nearest render pixel within 2 px."""
    total = (render[..., 3] > 0).sum() + (mockup[..., 3] > 0).sum()
    # nearest label for mockup pixels outside the render's silhouette
    lab = labels.copy()
    a = render[..., 3] > 0
    for _ in range(2):
        pad = np.pad(lab, 1, constant_values=".")
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            n = pad[1 + dy:lab.shape[0] + 1 + dy, 1 + dx:lab.shape[1] + 1 + dx]
            fill = (lab == ".") & (n != ".")
            lab[fill] = n[fill]
    lab[a] = labels[a]
    groups = {"head": "H", "neck": "N", "torso": "T", "arm_r": "Rr", "arm_l": "Ll", "legs": "PQ", "feet": "pq", "none": "."}
    out = {}
    for g, codes in groups.items():
        m = np.isin(lab, list(codes))
        n = int((m & a).sum())
        out[g] = (cost_render[m].sum() / max(total, 1e-9), cost_mockup[m].sum() / max(total, 1e-9), n)
    return out


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


# ---------------------------------------------------------------- text views

def palette_letters(recipe) -> list[tuple[tuple[int, int, int], str]]:
    """Two-character codes for every recipe color: ramp initial + slot mark
    (base '', shade '-', light '+', deep '=', ink '#', blush '~'), plus the outline."""
    from .character import hex_rgb
    marks = {"base": "", "shade": "-", "light": "+", "deep": "=", "ink": "#", "blush": "~"}
    used: dict[str, str] = {}
    out = []
    for name, ramp in recipe.ramps.items():
        key = next((c for c in name[0].upper() + name[1:] if c.upper() not in used), name[0])
        used[key.upper()] = name
        for slot, c in ramp.items():
            out.append((c, (key + marks.get(slot, "?")).ljust(2)))
    if "color" in recipe.outline:
        c = recipe.color(recipe.outline["color"], 1)
        if c not in {p for p, _ in out}:  # a hex outline; a ramp one is already listed
            out.append((c, "##"))
    for ref in recipe.legend.values():  # fixed colors in the head legend
        if ref.startswith("#"):
            out.append((hex_rgb(ref), "x "))
    return out


def quantize(rgb: np.ndarray, pal: list[tuple[tuple[int, int, int], str]], limit: float = 60) -> str:
    cols = np.array([p[0] for p in pal])
    d = _redmean(np.asarray(rgb)[None].repeat(len(cols), 0), cols)
    i = int(np.argmin(d))
    return pal[i][1] if d[i] < limit else "??"


def text_view(mockup: np.ndarray, render: np.ndarray, pal) -> list[str]:
    """Rows of `mockup | render`, both written in the recipe's palette letters ('??' =
    no recipe color within reach), so the mockup can be read like a head grid."""
    both = (mockup[..., 3] > 0) | (render[..., 3] > 0)
    ys, xs = np.where(both.any(1))[0], np.where(both.any(0))[0]
    lines = [f"   cols {xs[0]}..{xs[-1]}"]
    for y in range(ys[0], ys[-1] + 1):
        a = "".join(quantize(mockup[y, x, :3], pal) if mockup[y, x, 3] else ". " for x in range(xs[0], xs[-1] + 1))
        b = "".join(quantize(render[y, x, :3], pal) if render[y, x, 3] else ". " for x in range(xs[0], xs[-1] + 1))
        lines.append(f"{y:2d} {a}| {b}")
    return lines


def palette_fit(pairs: dict[tuple[int, int, int], list[np.ndarray]], pal) -> list[str]:
    """For every render color: how many pixels, the median mockup color under them and the
    mean distance. Suggests palette moves; an edge color (outline) is unreliable because
    of one-pixel drift, so read it next to the text view."""
    names = {c: l.strip() for c, l in pal}
    lines = ["render color         n   mockup median   dist"]
    for c, lst in sorted(pairs.items(), key=lambda kv: -len(kv[1])):
        a = np.array(lst)
        med = np.median(a, 0).astype(int)
        d = _redmean(np.array(c)[None].repeat(len(a), 0), a).mean()
        lines.append(f"#{c[0]:02x}{c[1]:02x}{c[2]:02x} {names.get(tuple(c), '?'):14} {len(a):4d}   "
                     f"#{med[0]:02x}{med[1]:02x}{med[2]:02x}        {d:4.0f}")
    return lines


# ---------------------------------------------------------------- palette optimizer

def optimize_palette(recipe, sprites, renders_for, radius: int = 28, step: int = 8,
                     min_gain: float = 0.0015) -> list[tuple[str, str, str, str, float]]:
    """Bounded coordinate descent over the recipe's ramp slots against the mockup views.

    For every ramp slot, tries moving each channel by ±step (repeatedly, within `radius`
    of the original color) and keeps a move only if the mean similarity over all views
    improves by at least `min_gain`. The bound keeps the palette the design's own: a
    slot can be nudged toward the mockup, not replaced by whatever scores best. Returns
    (ramp, slot, old hex, new hex, gain) for the moves it kept; the recipe is left as it
    was, so the caller decides which moves to apply.
    """
    def hexs(c):
        return "#%02x%02x%02x" % tuple(c)

    def score():
        return float(np.mean([similarity(sp, im) for sp, im in zip(sprites, renders_for(recipe))]))

    base = score()
    moves = []
    for ramp, slots in recipe.ramps.items():
        for slot in list(slots):
            orig = slots[slot]
            best, best_c = base, orig
            improved = True
            while improved:
                improved = False
                for ch in range(3):
                    for d in (-step, step):
                        c = list(best_c)
                        c[ch] = max(0, min(255, c[ch] + d))
                        c = tuple(c)
                        if max(abs(a - b) for a, b in zip(c, orig)) > radius or c == best_c:
                            continue
                        slots[slot] = c
                        s = score()
                        if s > best + min_gain / 4:
                            best, best_c, improved = s, c, True
                slots[slot] = best_c
            if best - base >= min_gain:
                moves.append((ramp, slot, hexs(orig), hexs(best_c), best - base))
                base = best
            else:
                slots[slot] = orig
    return moves


def ceiling(sprite: np.ndarray, pal) -> float:
    """The mockup snapped to the recipe's palette, scored against the mockup itself: what a
    render with exactly the mockup's shapes but only this palette could reach. The gap
    between this and `similarity` is shape; the gap to 1.0 is palette."""
    cols = np.array([c for c, _ in pal], float)
    q = sprite.copy()
    a = sprite[..., 3] > 0
    px = sprite[a, :3].astype(float)
    d = np.stack([_redmean(px, np.repeat(c[None], len(px), 0)) for c in cols], 1)
    q[a, :3] = cols[np.argmin(d, 1)].astype(np.uint8)
    return similarity(sprite, q)

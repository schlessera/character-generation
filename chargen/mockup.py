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
# an eight-view mockup is a full turn-around, the rotate animation's order: the three left-facing
# views are then scored and drafted like the others instead of being mirrored from their twins
TURNAROUND_FACINGS = ["down", "down_side", "side", "up_side", "up", "up_side_l", "side_l", "down_side_l"]


def mockup_facings(n: int) -> list[str]:
    """Which template facing each extracted view is, by the number of views in the sheet."""
    if n == len(MOCKUP_FACINGS):
        return MOCKUP_FACINGS
    if n == len(TURNAROUND_FACINGS):
        return TURNAROUND_FACINGS
    raise ValueError(f"a mockup has 5 views ({', '.join(MOCKUP_FACINGS)}) or 8 ({', '.join(TURNAROUND_FACINGS)}); "
                     f"this one extracted as {n} (a figure split by a light row, or two touching?)")


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
        sprites.append(_main_run(rgba))
    return sprites


def _main_run(sprite: np.ndarray) -> np.ndarray:
    """Keep the longest run of non-empty rows: a neighbouring figure's shoe or hair row can
    land in the snapped cells of this one when the stack's gaps are tight."""
    rows = sprite[..., 3].any(1)
    best, cur, start = (0, 0), 0, 0
    for i, v in enumerate(list(rows) + [False]):
        if v:
            cur = cur + 1 if cur else 1
            start = i if cur == 1 else start
            if cur > best[1] - best[0]:
                best = (start, i + 1)
        else:
            cur = 0
    return sprite[best[0]:best[1]]


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


def _shift(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """`a` moved by (dy, dx) with transparent fill: np.roll wrapped the sole row to the top of the
    frame whenever the best placement was one row down (every view paid for it, ~0.01)."""
    H, W = a.shape[:2]
    out = np.zeros_like(a)
    ys, yd = (slice(0, H - dy), slice(dy, H)) if dy >= 0 else (slice(-dy, H), slice(0, H + dy))
    xs, xd = (slice(0, W - dx), slice(dx, W)) if dx >= 0 else (slice(-dx, W), slice(0, W + dx))
    out[yd, xd] = a[ys, xs]
    return out


def cost_maps(sprite: np.ndarray, render: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(mockup placed at the best shift, cost of each render pixel, cost of each mockup pixel).

    The per-pixel view of `similarity`: where the render loses score, and where the mockup
    has pixels the render never matches. Used by `compare`'s heat-map rows."""
    base = place(sprite, render)
    best = None
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            m = _shift(base, dy, dx)
            cr, cm = _cost_map(render, m), _cost_map(m, render)
            n = (render[..., 3] > 0).sum() + (m[..., 3] > 0).sum()
            s = 1 - (cr.sum() + cm.sum()) / max(n, 1)
            if best is None or s > best[0]:
                best = (s, m, cr, cm)
    return best[1], best[2], best[3]


def placement(sprite: np.ndarray, render: np.ndarray) -> tuple[int, int]:
    """Where the mockup view lands on the frame (row, col of its top-left) at the best shift.
    It moves when the render's silhouette changes (a grow, a shrink, a drafted head), and a
    grid drafted before the move is one pixel off afterwards: `just step` reports the change."""
    H, W = render.shape[:2]
    h, w = sprite.shape[:2]
    ys = np.where(render[..., 3].any(1))[0]
    xs = np.where(render[..., 3].any(0))[0]
    oy = int(ys[-1] + 1 - h)
    ox = int(round((xs[0] + xs[-1]) / 2 - w / 2)) + 1
    base = place(sprite, render)
    best = None
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            m = _shift(base, dy, dx)
            c1, c2 = _cost(m, render), _cost(render, m)
            sc = 1 - (c1.sum() + c2.sum()) / max(len(c1) + len(c2), 1)
            if best is None or sc > best[0]:
                best = (sc, dy, dx)
    return oy + best[1], ox + best[2]


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
            m = _shift(base, dy, dx)
            c1, c2 = _cost(m, render), _cost(render, m)
            best = max(best, 1 - (c1.sum() + c2.sum()) / max(len(c1) + len(c2), 1))
    return best


# ---------------------------------------------------------------- text views

def palette_letters(recipe) -> list[tuple[tuple[int, int, int], str]]:
    """Two-character codes for every recipe color: ramp initial + slot mark
    (base '', shade '-', light '+', deep '=', ink '#', blush '~'), plus the outline."""
    from .character import hex_rgb
    marks = {"base": "", "shade": "-", "light": "+", "deep": "=", "ink": "#", "blush": "~"}
    used: dict[str, str] = {ch.upper(): "legend" for ch in recipe.legend if ch != "-"}  # legend chars are taken
    out = []
    for name, ramp in recipe.ramps.items():
        key = next((c for c in name[0].upper() + name[1:] + "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if c.upper() not in used), name[0])
        used[key.upper()] = name
        for slot, c in ramp.items():
            out.append((c, (key + marks.get(slot, "?")).ljust(2)))
    if "color" in recipe.outline:
        c = recipe.color(recipe.outline["color"], 1)
        if c not in {p for p, _ in out}:  # a hex outline; a ramp one is already listed
            out.append((c, "##"))
    # the head legend's characters win for the colours they reference, so the text view reads
    # like a grid (and the drafted grid reads like the text view)
    by_col = {}
    for ch, ref in recipe.legend.items():
        if ref == "clear":
            continue
        col = hex_rgb(ref) if ref.startswith("#") else recipe.color(ref, 1)
        by_col.setdefault(col, ch)
    out = [(c, (by_col[c] + " ") if c in by_col else l) for c, l in out]
    for col, ch in by_col.items():
        if col not in {p for p, _ in out}:
            out.append((col, ch + " "))
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


def labels_view(mockup: np.ndarray, render: np.ndarray, frame, pal) -> list[str]:
    """Rows of `mockup | labels | tones`: what body part and template tone lie under every
    mockup pixel, so a feature that crosses a part boundary (a coat's skirt over the hand, a
    boot over the leg's last row) is named by the label the rule needs."""
    both = (mockup[..., 3] > 0) | (render[..., 3] > 0)
    ys, xs = np.where(both.any(1))[0], np.where(both.any(0))[0]
    tone_ch = {0: " ", 1: ".", 2: "s", 3: "l", 4: "b", 5: "#"}
    lines = [f"   cols {xs[0]}..{xs[-1]}   mockup | labels (H head N neck T torso R/L arms r/l hands P/Q legs p/q feet) | tones (. lit s shade l light b blush # ink)"]
    for y in range(ys[0], ys[-1] + 1):
        a = "".join(quantize(mockup[y, x, :3], pal) if mockup[y, x, 3] else ". " for x in range(xs[0], xs[-1] + 1))
        lab = "".join(frame.labels[y, x] if frame.tones[y, x] else " " for x in range(xs[0], xs[-1] + 1))
        ton = "".join(tone_ch.get(int(frame.tones[y, x]), "?") for x in range(xs[0], xs[-1] + 1))
        lines.append(f"{y:2d} {a}| {lab} | {ton}")
    return lines


def palette_fit(pairs: dict[tuple[int, int, int], list[np.ndarray]], pal) -> list[str]:
    """For every render color: how many pixels, the median mockup color under them and the
    mean distance. Suggests palette moves; an edge color (outline) is unreliable because
    of one-pixel drift, so read it next to the text view."""
    names = {c: l.strip() for c, l in pal}
    lines = ["render color         n   mockup median   dist  spread   (~ wide: the median is not a colour the mockup uses much; --hex before moving)"]
    for c, lst in sorted(pairs.items(), key=lambda kv: -len(kv[1])):
        a = np.array(lst)
        med = np.median(a, 0).astype(int)
        ds = _redmean(np.array(c)[None].repeat(len(a), 0), a)
        spread = _redmean(np.repeat(med[None], len(a), 0).astype(float), a).std()
        lines.append(f"#{c[0]:02x}{c[1]:02x}{c[2]:02x} {names.get(tuple(c), '?'):14} {len(a):4d}   "
                     f"#{med[0]:02x}{med[1]:02x}{med[2]:02x}        {ds.mean():4.0f}   {spread:4.0f} {'~' if spread > 60 else ''}")
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


# ---------------------------------------------------------------- head-grid fitter

def fit_grid(recipe, facing: str, sprite: np.ndarray, frame, render, chars: str | None = None,
             min_gain: float = 0.0008, sweeps: int = 2) -> tuple[np.ndarray, float, float]:
    """Trace the mockup with the head grid: for every grid cell that lands on the head (or
    beside it), try each legend character and keep the one that raises the view's
    similarity by at least `min_gain`. `chars` limits the candidates (e.g. hair tones
    only). Greedy, a few sweeps. Returns (grid, score before, score after); the recipe's
    grid is left as it was."""
    from .character import HEAD_PAD
    grid = recipe.grids[facing].copy()
    orig = recipe.grids[facing]
    cands = list(chars) if chars else list(recipe.legend) + ["."]
    _, hx, hy, _ = frame.head
    H, W = frame.tones.shape

    def score():
        recipe.grids[facing] = grid
        return similarity(sprite, render(recipe, frame))
    base = before = score()
    for _ in range(sweeps):
        changed = False
        for gy in range(grid.shape[0]):
            for gx in range(grid.shape[1]):
                y, x = hy + gy - HEAD_PAD, hx + gx - HEAD_PAD
                if not (0 <= y < H and 0 <= x < W):
                    continue
                cur = grid[gy, gx]
                best, best_c = base, cur
                for c in cands:
                    if c == cur:
                        continue
                    grid[gy, gx] = c
                    s = score()
                    if s > best + min_gain:
                        best, best_c = s, c
                grid[gy, gx] = best_c
                if best_c != cur:
                    base, changed = best, True
        if not changed:
            break
    recipe.grids[facing] = orig
    return grid, before, base


def grid_text(grid: np.ndarray) -> str:
    return "\n".join("".join(row) for row in grid)


# ---------------------------------------------------------------- more instruments
# Each of these answers one question the iteration loop kept asking. They print text,
# because text is what the agent reads best.

def widths(mockup: np.ndarray, render: np.ndarray, labels: np.ndarray) -> list[str]:
    """Per row: the mockup's and the render's horizontal extent, the difference on each
    side (positive = the mockup is wider there), and the labels at the render's edges.
    Differences of 1 are free under the metric's tolerance; look for 2 and more."""
    out = [" row  mockup    render    dL dR  edge labels"]
    for y in range(mockup.shape[0]):
        m = np.where(mockup[y, :, 3])[0]
        n = np.where(render[y, :, 3])[0]
        if not len(m) and not len(n):
            continue
        ms = f"[{m[0]:2d},{m[-1]:2d}]" if len(m) else "   --  "
        ns = f"[{n[0]:2d},{n[-1]:2d}]" if len(n) else "   --  "
        d = f"{n[0] - m[0]:+d} {m[-1] - n[-1]:+d}" if len(m) and len(n) else "     "
        lab = "".join(sorted(set(labels[y][n]))) if len(n) else ""
        out.append(f"  {y:2d}  {ms}   {ns}   {d}  {lab}")
    return out


def digits(mockup: np.ndarray, render: np.ndarray, cost_render: np.ndarray, cost_mockup: np.ndarray) -> list[str]:
    """The cost maps as digits 0-9 per pixel: `mockup side | render side`. A 9 is a pixel
    with nothing similar within one pixel in the other image."""
    both = (mockup[..., 3] > 0) | (render[..., 3] > 0)
    ys, xs = np.where(both.any(1))[0], np.where(both.any(0))[0]
    out = [f"   cols {xs[0]}..{xs[-1]}   mockup-side | render-side"]
    for y in range(ys[0], ys[-1] + 1):
        a = "".join(str(min(9, int(cost_mockup[y, x] * 9.99))) if mockup[y, x, 3] else "." for x in range(xs[0], xs[-1] + 1))
        b = "".join(str(min(9, int(cost_render[y, x] * 9.99))) if render[y, x, 3] else "." for x in range(xs[0], xs[-1] + 1))
        out.append(f"{y:2d} {a} | {b}")
    return out


def quantized(mockup: np.ndarray, pal) -> np.ndarray:
    cols = np.array([c for c, _ in pal], float)
    q = mockup.copy()
    a = mockup[..., 3] > 0
    px = mockup[a, :3].astype(float)
    d = np.stack([_redmean(px, np.repeat(c[None], len(px), 0)) for c in cols], 1)
    q[a, :3] = cols[np.argmin(d, 1)].astype(np.uint8)
    return q


def slack(mockup: np.ndarray, render: np.ndarray, labels: np.ndarray, pal) -> dict[str, tuple[float, float]]:
    """Per part: (loss now, loss of the mockup quantized to the palette). The difference is
    the room left for placement; the second number is noise no recipe can remove."""
    _, cr, cm = cost_maps_placed(mockup, render)
    now = breakdown(cr, cm, labels, render, mockup)
    q = quantized(mockup, pal)
    cq, cm2 = _cost_map(q, mockup), _cost_map(mockup, q)
    ceil = breakdown(cq, cm2, labels, q, mockup)
    return {p: (now[p][0] + now[p][1], ceil[p][0] + ceil[p][1]) for p in now}


def cost_maps_placed(placed: np.ndarray, render: np.ndarray):
    """Like cost_maps, for a mockup that is already placed (no further shift)."""
    return placed, _cost_map(render, placed), _cost_map(placed, render)


def split(mockup: np.ndarray, render: np.ndarray) -> tuple[float, float]:
    """(silhouette match, colour loss): the silhouette allows one pixel of drift; the
    colour loss is the cost of pixels that do have a neighbour but the wrong colour."""
    def dil(a):
        p = np.pad(a, 1)
        return (p[1:-1, 1:-1] | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
                | p[:-2, :-2] | p[:-2, 2:] | p[2:, :-2] | p[2:, 2:])
    _, cr, cm = cost_maps_placed(mockup, render)
    a, b = render[..., 3] > 0, mockup[..., 3] > 0
    n = a.sum() + b.sum()
    sil = 1 - ((a & ~dil(b)).sum() + (b & ~dil(a)).sum()) / n
    col = (cr[a & dil(b)].sum() + cm[b & dil(a)].sum()) / n
    return float(sil), float(col)


def shift_probe(recipe, facing: str, sprite: np.ndarray, frame, render, chars: str | None = None) -> tuple[int, int, float]:
    """The best one-pixel offset for a facing's head grid (dx, dy, gain), of the whole grid
    or only of the cells in `chars` (e.g. the hair tones, leaving visor and ear in place).
    A consistent direction across views means the hair wants more volume on that side;
    act by adding hair on that side, not by moving the face."""
    g = recipe.grids[facing]
    base = similarity(sprite, render(recipe, frame))
    best = (0, 0, 0.0)
    H, W = g.shape
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == dy == 0:
                continue
            src = g if chars is None else np.where(np.isin(g, list(chars)), g, ".")
            keep = np.full_like(g, ".") if chars is None else np.where(np.isin(g, list(chars)), ".", g)
            sh = keep.copy()
            moved = src[max(0, -dy):H + min(0, -dy), max(0, -dx):W + min(0, -dx)]
            dst = sh[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)]
            dst[moved != "."] = moved[moved != "."]
            recipe.grids[facing] = sh
            gain = similarity(sprite, render(recipe, frame)) - base
            if gain > best[2]:
                best = (dx, dy, gain)
    recipe.grids[facing] = g
    return best


def fit_part(pairs_by_letter: dict[str, list], pal) -> list[str]:
    """Like palette_fit, but per palette letter and restricted by the caller to some body
    parts, with the mean cost: which colours, on this part, sit where the mockup has
    something else."""
    out = [f"{'render':6} {'n':>4}  median mockup  as letter  mean cost  total"]
    for k, v in sorted(pairs_by_letter.items(), key=lambda kv: -sum(c for _, c in kv[1])):
        med = np.median(np.array([p for p, _ in v]), 0).astype(int)
        out.append(f"{k:6} {len(v):4d}  #{med[0]:02x}{med[1]:02x}{med[2]:02x}        {quantize(med, pal):>4}      "
                   f"{np.mean([c for _, c in v]):.2f}     {sum(c for _, c in v):.1f}")
    return out


def _texture_to_hair(classes: dict) -> dict:
    """Translation table: each texture character becomes the hair's base (or its second character
    for the texture's second one, so a checker keeps two tones)."""
    hair, tex = classes["hair"], classes["texture"]
    base = hair[1] if len(hair) > 1 else hair[0]
    alt = hair[2] if len(hair) > 2 else base
    return str.maketrans(tex, "".join(alt if i == 1 else base for i in range(len(tex))))


def near_side(frame) -> tuple[str, str]:
    """Which of her arms is nearer the camera in this frame, and on which screen side the far
    arm lies: ("L"|"R", "left"|"right"|"behind"). The template draws the near arm fuller; the
    labels are anatomical (R = her right) even in mirrored frames, so this is the ground truth
    the playbook's 3D reasoning had to guess at."""
    on = frame.tones > 0
    xr = np.where(np.isin(frame.labels, ["R", "r"]) & on)[1]
    xl = np.where(np.isin(frame.labels, ["L", "l"]) & on)[1]
    if not len(xr) or not len(xl):
        return "R", "behind"
    near, far = ("L", xr) if len(xl) > len(xr) else ("R", xl)
    nx = xl.mean() if near == "L" else xr.mean()
    d = far.mean() - nx
    hidden = len(far) < 0.3 * max(len(xl), len(xr))  # the profile: the far arm is mostly behind the body (3/4: ~0.4)
    return near, "behind" if hidden or abs(d) < 1.5 else ("right" if d > 0 else "left")


def mirror_grid(recipe, facing: str, frame, head_tones: np.ndarray, swap: bool = False,
                shaved: str = "R", classes: dict | None = None) -> tuple[np.ndarray, str] | tuple[None, str]:
    """A left-facing grid drafted from its right-facing twin, mirrored about the head
    template's padded width (a drafted grid is wider than the template, so reversing the rows
    as strings misaligns). A mirror image swaps her left and right; with `swap` a one-sided
    cut (shaved side = `shaved`, her right by default) is put back on her own side using the
    frame's labels: the mane covers the near side, the shaved side shows as a two-column strip
    at the far edge (none in profile), hair does not overhang the far edge, the lens keeps its
    dark caps, and the ear moves with the shaved side. Returns (grid, what was done)."""
    from .character import HEAD_CLASSES, HEAD_PAD
    classes = classes or getattr(recipe, "head_classes", HEAD_CLASSES)
    hair, tex, lens, caps = classes["hair"], classes["texture"], classes["lens"], classes["caps"]
    base = facing[:-2]
    g = recipe.grids.get(base)
    if g is None:
        return None, "no twin"
    w = head_tones.shape[1] + 2 * HEAD_PAD
    out = np.full_like(g, ".")
    for x in range(min(w, g.shape[1])):
        out[:, x] = g[:, w - 1 - x]
    if not swap:
        return out, "mirrored"
    near, far_side = near_side(frame)
    head = np.pad(head_tones > 0, HEAD_PAD)[:, ::-1]  # the mirrored head silhouette
    H, W = out.shape
    stub_rows = {int(y) for y in np.where(np.isin(g, list(tex)).any(1))[0]}
    # the ear: outline cells drawn by the grid, and skin cells outside the head silhouette
    inside = np.zeros_like(out, dtype=bool)
    hh, hw = min(head.shape[0], H), min(head.shape[1], W)
    inside[:hh, :hw] = head[:hh, :hw]
    ear = (out == "o") | (np.isin(out, list("Ss")) & ~inside)
    tr = _texture_to_hair(classes)
    out = np.vectorize(lambda ch: ch.translate(tr))(out)
    done = f"mirrored about the head; near arm is her {'left' if near == 'L' else 'right'}, far side {far_side}"
    if near != shaved:  # the mane is nearest: shaved side = a far strip, no far overhang, no ear
        out[ear] = hair[1] if len(hair) > 1 else hair[0]  # the ear sat on the shaved side; the mane covers it now
        cols_all = np.where(inside.any(0))[0]
        glo, ghi = (cols_all[0], cols_all[-1]) if len(cols_all) else (0, W - 1)
        for y in range(H):
            xs = np.where(inside[y])[0]
            lo, hi = (xs[0], xs[-1]) if len(xs) else (glo, ghi)
            for x in range(W):  # hair drawn past the far edge belonged to the mane on the other side
                past = (far_side == "left" and x < lo) or (far_side == "right" and x > hi)
                if past and out[y, x] in hair:
                    out[y, x] = "."
            if far_side != "behind" and y in stub_rows and len(xs):
                cols = (lo, lo + 1) if far_side == "left" else (hi - 1, hi)
                for x in cols:
                    if 0 <= x < W and out[y, x] in hair:
                        out[y, x] = tex[0] if (x + y) % 2 or len(tex) < 2 else tex[1]
        done += "; mane near, shaved strip at the far edge" if far_side != "behind" else "; all mane (profile)"
    for y in range(H):  # the lens keeps a dark cap at both ends
        vs = np.where(np.isin(out[y], list(lens)))[0]
        if len(vs) >= 3:
            for x in (vs[0] - 1, vs[-1] + 1):
                if 0 <= x < W and out[y, x] != "." and out[y, x] not in lens:
                    out[y, x] = caps[0]
    return out, done


def unlisted_slots(recipe) -> dict[str, str]:
    """Palette slots whose colour no legend character references, each given a free letter:
    the draft picks legend colours only, while the ceiling quantizes to every slot, so a short
    legend is a built-in gap. Used by `--draft-grid --all-slots`; the letters are appended to
    the legend by `apply_legend`."""
    from .character import hex_rgb
    have = set()
    for ref in recipe.legend.values():
        if ref != "clear":
            have.add(hex_rgb(ref) if ref.startswith("#") else recipe.color(ref, 1))

    def near(col):  # a slot within a few RGB steps of a legend colour adds a coupling, not a colour
        return any(_redmean(np.array(col, float), np.array(h, float)) < 30 for h in have)
    taken = set(recipe.legend) | {"."}
    free = [c for c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" if c not in taken]
    out = {}
    for name, ramp in recipe.ramps.items():
        for slot, col in ramp.items():
            if col in have or near(col) or not free:
                continue
            have.add(col)
            pref = [c for c in (name[0], name[0].upper(), slot[0], slot[0].upper()) if c in free]
            ch = pref[0] if pref else free[0]
            free.remove(ch)
            out[ch] = f"{name}.{slot}"
    return out


def apply_legend(recipe_path, entries: dict[str, str], recipe=None) -> None:
    """Append legend entries at the end of the [head.legend] block of the recipe file. With
    `recipe`, each entry is written as the slot's hex literal with the slot in a comment: the
    grid then holds the mockup's colour and does not follow a body ramp (a chrome ink used for
    hair edges recoloured the hair when the chrome moved)."""
    text = recipe_path.read_text()
    start = text.find("[head.legend]")
    if start < 0:
        return
    nxt = text.find("\n[", start + 1)
    end = len(text) if nxt < 0 else nxt
    block = text[start:end].rstrip("\n")
    if recipe is not None:
        lines = "".join('\n{} = "#{:02x}{:02x}{:02x}"   # {} at draft time (--all-slots); a literal, so the grid keeps this colour'
                        .format(ch, *recipe.color(ref, 1), ref) for ch, ref in entries.items())
    else:
        lines = "".join(f'\n{ch} = "{ref}"' for ch, ref in entries.items())
    recipe_path.write_text(text[:start] + block + lines + "\n" + text[end:])


def draft_grid(recipe, facing: str, placed: np.ndarray, frame, rows: int | None = None,
               chars: str | None = None, extra: dict[str, str] | None = None) -> np.ndarray:
    """A head grid drafted from the mockup: every grid cell that lands on the head, the neck
    or beside them takes the legend character whose colour is nearest to the mockup pixel
    under it; cells over the mockup's background stay '.'. `rows` limits the grid's height
    (the hair may hang below the head; the collar should not become hair), `chars` limits
    the candidates. This is what redrawing a grid from `--text` amounts to, without the
    transcription; hand-clean it afterwards (isolated speckles, the lens ends, the ear)."""
    from .character import HEAD_PAD
    _, hx, hy, _ = frame.head
    legend = {k: recipe.color(v, 1) for k, v in {**recipe.legend, **(extra or {})}.items()
              if v != "clear" and (chars is None or k in chars)}
    keys = list(legend)
    cols = np.array([legend[k] for k in keys], float)
    ref = recipe.grids.get(facing)
    h = ref.shape[0] if ref is not None else 16
    w = ref.shape[1] if ref is not None else 20
    if rows:
        h = min(h, rows)
    g = np.full((h, w), ".", "<U1")
    H, W = frame.tones.shape
    head_rows = np.where((frame.labels == "H").any(1))[0]
    bottom = int(head_rows[-1]) + 1 if len(head_rows) else H  # hair may hang one row past the jaw
    allowed = (frame.labels == "H") | (np.isin(frame.labels, ["N", "."]) & (np.arange(H)[:, None] <= bottom))
    for gy in range(h):
        for gx in range(w):
            y, x = hy + gy - HEAD_PAD, hx + gx - HEAD_PAD
            if not (0 <= y < H and 0 <= x < W) or not allowed[y, x] or not placed[y, x, 3]:
                continue
            d = _redmean(np.repeat(placed[y, x, :3][None], len(cols), 0).astype(float), cols)
            g[gy, gx] = keys[int(np.argmin(d))]
    return g


def hex_box(placed: np.ndarray, y0: int, y1: int, x0: int, x1: int) -> list[str]:
    """Raw mockup hex per pixel for a box (frame rows y0..y1-1, cols x0..x1-1): the truth
    behind the palette letters where several dark ramps sit a few RGB steps apart."""
    out = [f"   cols {x0}..{x1 - 1}"]
    for y in range(y0, min(y1, placed.shape[0])):
        out.append(f"{y:2d} " + " ".join(f"{p[0]:02x}{p[1]:02x}{p[2]:02x}" if p[3] else "------" for p in placed[y, x0:x1]))
    return out


# ---------------------------------------------------------------- drafts: clean and apply

def clean_grid(g: np.ndarray, legend: dict, classes: dict | None = None, despeckle: bool = True,
               last_row: bool = True) -> np.ndarray:
    """The mechanical part of cleaning a drafted grid: rim characters outside the lens rows (a
    dark pixel is nearest to the rim greys), lone speckles inside the hair or texture (a cell
    unlike all its neighbours takes their majority), and the last row keeps hair characters only
    (it is the row below the jaw: hanging tips yes, collar no). Which characters are hair, texture,
    lens and rim comes from `[head.classes]` (see HEAD_CLASSES in character.py)."""
    from .character import HEAD_CLASSES
    classes = classes or HEAD_CLASSES
    hair, stubble, lens = classes["hair"], classes["texture"], classes["lens"]
    g = g.copy()
    vis = [ch for ch in classes["rim"] if ch in legend]  # not the lens: a lone lens cell may be the tip past the face
    lens_rows = {y for y in range(g.shape[0]) if sum(ch in lens for ch in g[y]) >= 3}
    keep_rows = lens_rows | {y + 1 for y in lens_rows} | {y - 1 for y in lens_rows}  # the rims sit beside the lens
    tex = set(hair + stubble)
    H, W = g.shape

    def majority(y, x):
        nb = [g[yy, xx] for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)) if 0 <= yy < H and 0 <= xx < W]
        nb = [c for c in nb if c in tex]
        return max(set(nb), key=nb.count) if nb else "."

    for y in range(H):
        if y in keep_rows:
            continue
        for x in range(W):
            if g[y, x] in vis:  # a stray visor colour inside the hair: what surrounds it, never '.'
                g[y, x] = majority(y, x)  # ('.' would show the template's skin as a tan dot)
    for y in range(H if despeckle else 0):  # (on spiky light hair the "speckles" are the mockup's
        for x in range(W):                   # strand texture: the caller scores both and keeps the better)
            if g[y, x] not in tex:
                continue
            nb = [g[yy, xx] for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)) if 0 <= yy < H and 0 <= xx < W]
            nb = [c for c in nb if c in tex]
            if len(nb) >= 3 and g[y, x] not in nb:
                top = max(set(nb), key=nb.count)
                if nb.count(top) >= 3:
                    g[y, x] = top
    last = H - 1
    while last > 0 and (g[last] == ".").all():
        last -= 1
    for x in range(W if last_row else 0):  # the row below the jaw: hanging hair tips only, and not their outline
        if g[last, x] != "." and g[last, x] not in hair[1:]:  # (the first hair char is its outline: it chops the collar into dashes)
            g[last, x] = "."
    return g


def apply_grid(recipe_path, facing: str, g: np.ndarray) -> None:
    """Write a grid into the recipe file: replace the facing's block under [head.grids], or
    append one. Only the grid text moves; the rest of the file is untouched."""
    text = recipe_path.read_text()
    block = f'{facing} = """\n' + grid_text(g) + '\n"""'
    start = text.find(f"\n{facing} = \"\"\"")
    if start >= 0:
        end = text.index('"""', start + len(facing) + 6) + 3
        text = text[:start + 1] + block + text[end:]
    else:
        if "[head.grids]" not in text:
            text = text.rstrip("\n") + "\n\n[head.grids]\n"
        text = text.rstrip("\n") + "\n" + block + "\n"
    recipe_path.write_text(text)


def hot_spots(views, n: int = 20) -> list[str]:
    """The n costliest pixels over all views: view, row, col, what the mockup and the render
    show there (palette letters) and the cost. `views` = [(facing, placed, rend, cr, cm, pal)]."""
    rows = []
    for facing, placed, rend, cr, cm, pal in views:
        tot = cr + cm
        for y, x in zip(*np.where(tot > 0)):
            m = quantize(placed[y, x, :3], pal) if placed[y, x, 3] else "--"
            r_ = quantize(rend[y, x, :3], pal) if rend[y, x, 3] else "--"
            rows.append((float(tot[y, x]), facing, int(y), int(x), m, r_))
    rows.sort(reverse=True)
    out = [f"{'cost':>5} {'view':10} {'row':>3} {'col':>3}  mockup  render"]
    for c, f, y, x, m, r_ in rows[:n]:
        out.append(f"{c:5.2f} {f:10} {y:3d} {x:3d}  {m:6}  {r_}")
    return out


def init_palette(views, tone_ids: dict, parts: dict | None = None) -> list[str]:
    """Per body part and template tone, the median mockup colour under the render's pixels
    (before any head grid exists the body parts are reliable, the head is not). Grouped by
    the recipe's own [parts] lines when given (this design's parts, not another character's),
    else by single parts. `views` = [(facing, placed, labels, tones)]."""
    from .character import part_codes
    if parts:
        groups = {name: part_codes(name) for name in parts if name not in ("head", "fx")}
    else:
        groups = {"neck": "N", "torso": "T", "arm_l": "L", "hand_l": "l", "arm_r": "R", "hand_r": "r", "leg_l": "Q", "leg_r": "P", "feet": "pq"}
    names = {v: k for k, v in tone_ids.items()}
    out = [f"{'part':14} {'tone':6} {'n':>4}  median   spread"]
    for label, codes in groups.items():
        for tone in ("base", "shade", "light", "ink"):
            px = []
            for facing, placed, labels, tones in views:
                m = np.isin(labels, list(codes)) & (tones == tone_ids[tone]) & (placed[..., 3] > 0)
                px += list(placed[m, :3])
            if len(px) < 4:
                continue
            a = np.array(px, float)
            med = np.median(a, 0).astype(int)
            spread = _redmean(np.repeat(med[None].astype(float), len(a), 0), a).std()
            out.append(f"{label:14} {tone:6} {len(px):4d}  #{med[0]:02x}{med[1]:02x}{med[2]:02x}  {spread:5.0f}{' ~' if spread > 80 else ''}")
    out.append("(~ = wide: two populations, or trim on that part's tone (caps on the feet, glow on the arm): read --hex on a box; the head needs its grids first)")
    return out


def oracle(views, pal, groups=None) -> list[str]:
    """Where the remaining gap lives: for each body-part group, copy the mockup's pixels
    (quantized to the palette) over the render on that part's mask and score again. The gain
    is what a pixel-perfect version of that part would be worth; the rest is the metric's
    tolerance and the mockup's noise. `views` = [(facing, sprite, placed, rend, labels)]."""
    groups = groups or {"head": "H", "torso+arms": "TRLrl", "legs+feet": "PQpq", "body": "NTRLrlPQpq"}
    out = [f"{'part':12} {'gain':>8}   (mean over views; the whole-body figure is the most any rule set could add)"]
    for name, codes in groups.items():
        gains = []
        for facing, sprite, placed, rend, labels in views:
            base = similarity(sprite, rend)
            q = quantized(placed, pal)
            r2 = rend.copy()
            m = np.isin(labels, list(codes)) & (q[..., 3] > 0)
            r2[m] = q[m]
            gains.append(similarity(sprite, r2) - base)
        out.append(f"{name:12} {np.mean(gains):+8.4f}")
    return out


def ablate(recipe, sprites, renders_for) -> list[str]:
    """Drop each rule in turn and score: a rule that scores better removed is a detail this
    mockup lacks (confirm with --hex before deleting; the score alone is not a reason)."""
    base = float(np.mean([similarity(sp, im) for sp, im in zip(sprites, renders_for(recipe))]))
    rows = []
    rules = recipe.rules
    for i, rule in enumerate(rules):
        recipe.rules = rules[:i] + rules[i + 1:]
        s = float(np.mean([similarity(sp, im) for sp, im in zip(sprites, renders_for(recipe))]))
        rows.append((s - base, i + 1, rule.get("type"), rule.get("part"), rule.get("color", ""), rule.get("facings", "")))
    recipe.rules = rules
    rows.sort(reverse=True)
    out = [f"{'without':>8}  rule  (gain when removed; base {base:.4f})"]
    for d, i, t, p, c, f in rows:
        out.append(f"{d:+8.4f}  {i:3d}  {t} {p} {c} {f if f else ''}")
    return out


# ---------------------------------------------------------------- forward rule search

SWEEP_PARTS = ["torso", "neck", "arm_l", "arm_r", "hand_l", "hand_r", "leg_l", "leg_r", "foot_l", "foot_r", "arms", "hands", "legs", "feet"]


def sweep_candidates(recipe, parts=None) -> list[dict]:
    """Simple rule shapes on every part in every ramp's base colour: the forward search that
    `--ablate` (backward) lacks. Each is appended after the recipe's rules, so it paints last."""
    shapes = [
        {"type": "rows", "from": "top", "n": 1}, {"type": "rows", "from": "bottom", "n": 1},
        {"type": "band", "at": 0.5}, {"type": "stripe", "straight": True},
        {"type": "region", "anchor": "front", "n": 1}, {"type": "region", "anchor": "back", "n": 1},
        {"type": "grow", "sides": ["front"]}, {"type": "grow", "sides": ["back"]},
        {"type": "shrink", "sides": ["front"]}, {"type": "shrink", "sides": ["back"]},
    ]
    colours: list[tuple[str, tuple]] = []  # one candidate per distinct colour (a tee, a mask and a rim
    for ramp, slots in recipe.ramps.items():  # in the same grey are one candidate, named for the first)
        if ramp == "fx" or "base" not in slots:
            continue
        if not any(_redmean(np.array(slots["base"], float), np.array(c, float)) < 20 for _, c in colours):
            colours.append((ramp, slots["base"]))
    out = []
    for part in (parts or SWEEP_PARTS):
        for shape in shapes:
            if shape["type"] == "shrink":
                out.append({**shape, "part": part})
                continue
            for ramp, _ in colours:
                out.append({**shape, "part": part, "color": f"{ramp}.base"})
    return out


_SWEEP: dict = {}


def _sweep_init(recipe, frames, sprites, base):
    _SWEEP.update(recipe=recipe, frames=frames, sprites=sprites, base=base)


def _sweep_one(rule):
    from .character import _rule_mask, part_codes, render_frame
    r, frames, sprites, base = _SWEEP["recipe"], _SWEEP["frames"], _SWEEP["sprites"], _SWEEP["base"]
    r.rules = r.rules + [rule]
    try:
        deltas = [similarity(sp, render_frame(r, fr)) - b for sp, fr, b in zip(sprites, frames, base)]
    finally:
        r.rules = r.rules[:-1]
    covers = []  # views where the rule repaints a whole part: a one-column cyber-shin vanished that way
    if rule["type"] not in ("grow", "shrink"):
        codes = list(part_codes(rule["part"]))
        for i, fr in enumerate(frames):
            m = _rule_mask({**rule, "ink": True}, fr)
            for c in codes:
                part = (fr.labels == c) & (fr.tones > 0)
                if part.sum() and (m & part).sum() == part.sum():
                    covers.append(i)
                    break
    return deltas, covers


def sweep(recipe, sprites, frames, facings, n: int = 20, parts=None, workers: int | None = None) -> list[str]:
    """Score every candidate rule across the views and print the best: mean gain over all views,
    the gain if the rule were limited to the views where it helps (with those facings), and
    the rule. A pick is a candidate to confirm on `just crops --diff` and in `--hex`, not a
    result; a rule that gains on one view and loses on its mirror usually wants `facings`."""
    import os
    from multiprocessing import Pool
    from .character import render_frame
    base = [similarity(sp, render_frame(recipe, fr)) for sp, fr in zip(sprites, frames)]
    cands = sweep_candidates(recipe, parts)
    workers = workers or max(1, min(8, (os.cpu_count() or 2) - 1))
    with Pool(workers, initializer=_sweep_init, initargs=(recipe, frames, sprites, base)) as pool:
        deltas = pool.map(_sweep_one, cands, chunksize=8)
    rows = []
    for rule, (d, covers) in zip(cands, deltas):
        pos = [f for f, v in zip(facings, d) if v > 0.0005]
        cov = [facings[i] for i in covers if facings[i] in pos]
        rows.append((float(np.mean(d)), float(sum(max(v, 0) for v in d) / len(d)), pos, cov, rule))
    rows.sort(key=lambda r: -r[1])
    out = [f"{len(cands)} candidates over {len(facings)} views ({workers} workers); base mean {np.mean(base):.4f}",
           f"{'mean':>8} {'if limited':>10}  facings where it gains                rule   (! = repaints a whole part there: check the feature is still visible)"]
    for mean, lim, pos, cov, rule in rows[:n]:
        desc = " ".join(f"{k}={v}" for k, v in rule.items() if k != "type")
        out.append(f"{mean:+8.4f} {lim:+10.4f}  {','.join(pos) or '-':38} {rule['type']} {desc}"
                   + (f"   ! whole part in {','.join(cov)}" if cov else ""))
    return out

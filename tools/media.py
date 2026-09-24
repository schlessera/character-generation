"""Regenerate the README images in docs/images from the real pipeline and the running game.

Everything here is derived from repository data (template, labels, recipes, pixel files,
generated concept art) or captured from the playground in headless Chromium.
Run with `just media` (it builds first).
"""
from __future__ import annotations

import base64
import io
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chargen.character import FACINGS, Recipe, build_frames, render_frame  # noqa: E402
from chargen.labels import load_all  # noqa: E402
from chargen.labeltool import LABEL_COLORS, label_rgba, template  # noqa: E402
from chargen.pixeltool import draft_pixels, reference, to_rgba, read  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs/images"
OUT.mkdir(parents=True, exist_ok=True)
BG = (24, 23, 34, 255)
PANEL = (34, 33, 48, 255)
TEXT = (214, 216, 230, 255)
DIM = (140, 142, 165, 255)


def font(size: int):
    for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/TTF/DejaVuSansMono.ttf"]:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


F = font(14)
FS = font(12)


def up(im: Image.Image | np.ndarray, s: int) -> Image.Image:
    if isinstance(im, np.ndarray):
        im = Image.fromarray(im)
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


def on_bg(im: Image.Image, pad: int = 0, color=BG) -> Image.Image:
    out = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), color)
    out.alpha_composite(im.convert("RGBA"), (pad, pad))
    return out


def save(im: Image.Image, name: str) -> None:
    im.convert("RGB").save(OUT / name, optimize=True)
    print("wrote", name)


def caption_row(items: list[tuple[str, Image.Image]], gap: int = 18, pad: int = 16) -> Image.Image:
    h = max(i.height for _, i in items) + 30
    w = sum(i.width for _, i in items) + gap * (len(items) - 1) + 2 * pad
    out = Image.new("RGBA", (w, h + 2 * pad), BG)
    d = ImageDraw.Draw(out)
    x = pad
    for label, im in items:
        d.text((x, pad), label, font=F, fill=TEXT)
        out.alpha_composite(im.convert("RGBA"), (x, pad + 26 + (h - 30 - im.height)))
        x += im.width + gap
    return out


def gif(frames: list[Image.Image], name: str, ms: int | list[int]) -> None:
    rgb = [f.convert("RGB") for f in frames]
    # one shared adaptive palette keeps colors stable across frames (no flicker); built from
    # a strip of sampled frames so colors that only appear later (a passing car) are in it
    sample = rgb[::max(1, len(rgb) // 12)]
    strip = Image.new("RGB", (sample[0].width, sample[0].height * len(sample)))
    for i, f in enumerate(sample):
        strip.paste(f, (0, i * f.height))
    pal = strip.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in rgb]
    q[0].save(OUT / name, save_all=True, append_images=q[1:], duration=ms, loop=0, optimize=True)
    print("wrote", name)


# ---------------------------------------------------------------- template & labels

tpl = template()
frames = build_frames(tpl)
labels = load_all(tpl)
TONE = {1: (250, 243, 232), 2: (185, 179, 161), 3: (231, 213, 198), 4: (209, 157, 167), 5: (47, 37, 34)}


def tone_img(i: int) -> np.ndarray:
    out = np.zeros((tpl.h, tpl.w, 4), np.uint8)
    for t, c in TONE.items():
        out[tpl.tones[i] == t] = (*c, 255)
    return out


def template_sheet():
    """The raw template: every animation (rows) for the down-facing direction + one row per facing."""
    rows = [(a, tpl.anims[a]["down"]) for a in ["idle", "walk", "run", "jump", "attack", "interact"]]
    rows.append(("rotate", tpl.anims["rotate"]["all"]))
    s, cw = 4, 32 * 4 + 6
    w = 110 + 8 * cw
    out = Image.new("RGBA", (w, len(rows) * (32 * s + 6) + 20), BG)
    d = ImageDraw.Draw(out)
    for r, (name, fr) in enumerate(rows):
        y = 10 + r * (32 * s + 6)
        d.text((12, y + 56), name, font=F, fill=TEXT)
        for c, i in enumerate(fr):
            out.alpha_composite(up(tone_img(i), s), (110 + c * cw, y))
    save(out, "template-sheet.png")


def label_figure():
    """One frame: pixels | tone ASCII-like view | part labels | overlay, plus a legend."""
    i = 0
    lab = labels[i]
    s = 10
    orig = up(tone_img(i), s)
    lc = up(label_rgba(lab), s)
    mix = tone_img(i).copy()
    m = lab != "."
    mix[m, :3] = (mix[m, :3] * 0.4 + label_rgba(lab)[m, :3] * 0.6).astype(np.uint8)
    fig = caption_row([("template frame", on_bg(orig)), ("part labels", on_bg(lc)), ("overlay", on_bg(up(mix, s)))])
    names = {"H": "head", "N": "neck", "T": "torso", "R": "right arm", "r": "right hand", "L": "left arm",
             "l": "left hand", "P": "right leg", "p": "right foot", "Q": "left leg", "q": "left foot", "X": "fx"}
    leg = Image.new("RGBA", (fig.width, 60), BG)
    d = ImageDraw.Draw(leg)
    x, y = 16, 6
    for k, n in names.items():
        d.rectangle([x, y + 2, x + 12, y + 14], fill=LABEL_COLORS[k])
        d.text((x + 18, y), f"{k} {n}", font=FS, fill=TEXT)
        x += 150
        if x > fig.width - 150:
            x, y = 16, y + 22
    out = Image.new("RGBA", (fig.width, fig.height + leg.height), BG)
    out.alpha_composite(fig, (0, 0))
    out.alpha_composite(leg, (0, fig.height))
    save(out, "labels-frame.png")


def label_sheet():
    """Labels across animations: consistent sides and parts even in extreme poses."""
    pick = [("idle", "side"), ("walk", "down_side"), ("run", "side"), ("jump", "down"), ("attack", "down_side")]
    s = 4
    rows = []
    for a, dname in pick:
        ims = []
        for i in tpl.anims[a][dname]:
            mix = tone_img(i).copy()
            m = labels[i] != "."
            mix[m, :3] = (mix[m, :3] * 0.3 + label_rgba(labels[i])[m, :3] * 0.7).astype(np.uint8)
            ims.append(up(mix, s))
        rows.append((f"{a}/{dname}", ims))
    cw = 32 * s + 4
    out = Image.new("RGBA", (150 + 7 * cw, len(rows) * (32 * s + 4) + 12), BG)
    d = ImageDraw.Draw(out)
    for r, (name, ims) in enumerate(rows):
        y = 6 + r * (32 * s + 4)
        d.text((12, y + 56), name, font=F, fill=TEXT)
        for c, im in enumerate(ims):
            out.alpha_composite(im, (150 + c * cw, y))
    save(out, "labels-sheet.png")


# ---------------------------------------------------------------- characters

juno = Recipe(ROOT / "characters/juno/recipe.toml")
glitch = Recipe(ROOT / "characters/juno-glitch/recipe.toml")


def idle(recipe, facing):
    f = frames["idle"][facing][0]
    return render_frame(recipe, f) if recipe else _tones(f)


def _tones(f):
    out = np.zeros(f.tones.shape + (4,), np.uint8)
    for t, c in TONE.items():
        out[f.tones == t] = (*c, 255)
    return out


def facings_figure():
    s = 5
    rows = [("template", None), ("Juno", juno)]
    cw = 32 * s
    out = Image.new("RGBA", (130 + 8 * cw, 2 * (32 * s + 10) + 36), BG)
    d = ImageDraw.Draw(out)
    for c, fname in enumerate(FACINGS):
        d.text((130 + c * cw + 8, 8), fname.replace("_side", "-side").replace("_l", " (left)"), font=FS, fill=DIM)
    for r, (name, rec) in enumerate(rows):
        y = 30 + r * (32 * s + 10)
        d.text((12, y + 70), name, font=F, fill=TEXT)
        for c, fname in enumerate(FACINGS):
            out.alpha_composite(up(idle(rec, fname), s), (130 + c * cw, y))
    save(out, "juno-facings.png")


ITERATION_STRIP = [0, 5, 10, 15, 20, 25, 40, 55, 70, 90, 110]  # the columns of the iteration figures


def _snapshots(subset=None):
    """(step, recipe) for every saved iteration step (characters/juno/history/step-NN.toml)."""
    steps = sorted((ROOT / "characters/juno/history").glob("step-*.toml"), key=lambda p: int(p.stem.split("-")[1]))
    snaps = [(int(p.stem.split("-")[1]), Recipe(p)) for p in steps]
    return [s for s in snaps if subset is None or s[0] in subset]


def iteration_figures():
    """Pixel mockup, then the recipe after every saved iteration step, left to right."""
    from chargen.mockup import MOCKUP_FACINGS, extract, place, similarity
    sprites = extract(ROOT / "characters/juno/concept/juno-pixel-mockup.png")
    snaps = _snapshots(ITERATION_STRIP)
    cols = [("pixel mockup", None)] + [(f"step {n}", rec) for n, rec in snaps]

    def view(rec, sprite, facing):
        im = idle(juno, facing)
        return place(sprite, im) if rec is None else idle(rec, facing)

    # full figures: one row per view
    s, lw = 4, 20
    cw = 32 * s
    out = Image.new("RGBA", (lw + len(cols) * cw, 30 + len(sprites) * cw), BG)
    d = ImageDraw.Draw(out)
    for c, (label, rec) in enumerate(cols):
        d.text((lw + c * cw + (cw - d.textlength(label, font=FS)) / 2, 10), label, font=FS,
               fill=TEXT if rec is None or c == len(cols) - 1 else DIM)
        for r, (sprite, facing) in enumerate(zip(sprites, MOCKUP_FACINGS)):
            out.alpha_composite(up(view(rec, sprite, facing), s), (lw + c * cw, 30 + r * cw))
    save(out, "juno-iteration.png")

    # head close-ups: front, profile and back, where most of the iterating happened
    s, hw = 6, 22
    cw = hw * s + 8
    out = Image.new("RGBA", (lw + len(cols) * cw, 30 + 3 * (16 * s + 8)), BG)
    d = ImageDraw.Draw(out)
    for c, (label, rec) in enumerate(cols):
        d.text((lw + c * cw + (cw - d.textlength(label, font=FS)) / 2, 10), label, font=FS,
               fill=TEXT if rec is None or c == len(cols) - 1 else DIM)
        for r, i in enumerate((0, 2, 4)):
            im = sprites[i] if rec is None else idle(rec, MOCKUP_FACINGS[i])
            ys = np.where(im[..., 3].any(1))[0]
            xs = np.where(im[..., 3].any(0))[0]
            cx = (xs[0] + xs[-1]) // 2
            head = Image.fromarray(im).crop((cx - hw // 2, ys[0], cx + hw // 2, ys[0] + 16))
            out.alpha_composite(up(head, s), (lw + c * cw + 4, 30 + r * (16 * s + 8)))
    save(out, "juno-iteration-heads.png")

    # similarity to the mockup per saved step (all snapshots)
    scores = []
    for n, rec in _snapshots():
        v = [similarity(sp, idle(rec, f)) for sp, f in zip(sprites, MOCKUP_FACINGS)]
        scores.append((n, float(np.mean(v)), min(v), max(v)))
    similarity_chart(scores)


def similarity_chart(scores):
    """Line chart: mean similarity to the mockup (band = worst..best view) per saved step."""
    W, H = 720, 300
    L, R, T, B = 56, 44, 44, 40
    out = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(out)
    d.text((L, 12), "Similarity to the pixel mockup (mean of 5 views, band = worst to best view)", font=FS, fill=TEXT)
    n_max = max(n for n, *_ in scores) or 1
    lo_v = np.floor(min(lo for *_, lo, _ in scores) * 20) / 20
    hi_v = np.ceil(max(hi for *_, hi in scores) * 20) / 20
    X = lambda n: L + (W - L - R) * n / n_max
    Y = lambda v: T + (H - T - B) * (hi_v - v) / (hi_v - lo_v)
    grid, ink, series = (52, 51, 68, 255), DIM, (216, 48, 124, 255)
    v = lo_v
    while v <= hi_v + 1e-9:
        d.line([(L, Y(v)), (W - R, Y(v))], fill=grid, width=1)
        d.text((8, Y(v) - 7), f"{v:.2f}", font=FS, fill=ink)
        v += 0.05
    for n, *_ in scores:
        d.text((X(n) - d.textlength(str(n), font=FS) / 2, H - B + 8), str(n), font=FS, fill=ink)
    d.text((W - R - d.textlength("iteration step", font=FS), H - 18), "iteration step", font=FS, fill=ink)
    band = [(X(n), Y(hi)) for n, _, _, hi in scores] + [(X(n), Y(lo)) for n, _, lo, _ in reversed(scores)]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(layer).polygon(band, fill=(216, 48, 124, 50))
    out.alpha_composite(layer)
    pts = [(X(n), Y(m)) for n, m, *_ in scores]
    d.line(pts, fill=series, width=2)
    for (x, y), (n, m, *_) in zip(pts, scores):
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=series, outline=BG, width=2)
        d.text((x - 14, y - 22), f"{m:.3f}", font=FS, fill=TEXT)
    save(out, "juno-similarity.png")


REPLICA_RUNS = [(1, "history-run1"), (2, "history-run2"), (3, "history-run3"), (4, "history-run4"), (5, "history-run5")]
REPLICA_CEILING = 0.9342


def _run_scores(folder):
    rows = []
    for line in (ROOT / "characters/replica" / folder / "NOTES.md").read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0].isdigit() and cells[2]:
            try:
                rows.append((int(cells[0]), float(cells[2])))
            except ValueError:
                pass
    return rows


def replica_chart():
    """One line per replay of the skill: similarity per step, with the palette ceiling and the
    goal lines (percent below it). Each run started from the skeleton and the mockup alone."""
    W, H = 880, 340
    L, R, T, B = 56, 190, 44, 40
    out = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(out)
    d.text((L, 12), "Five replays of the skill by fresh agents: similarity per step (every run starts at 0.64, the skeleton)", font=FS, fill=TEXT)
    runs = [(n, folder, _run_scores(folder)) for n, folder in REPLICA_RUNS]
    n_max = max(st for _, _, r in runs for st, _ in r)
    lo_v, hi_v = 0.85, 0.94
    X = lambda n: L + (W - L - R) * n / n_max
    Y = lambda v: T + (H - T - B) * (hi_v - v) / (hi_v - lo_v)
    grid, ink = (52, 51, 68, 255), DIM
    v = lo_v
    while v <= hi_v + 1e-9:
        d.line([(L, Y(v)), (W - R, Y(v))], fill=grid, width=1)
        d.text((8, Y(v) - 7), f"{v:.2f}", font=FS, fill=ink)
        v += 0.01
    for n in range(0, n_max + 1, 2):
        d.text((X(n) - 4, H - B + 8), str(n), font=FS, fill=ink)
    d.text((W - R - d.textlength("step", font=FS), H - 18), "step", font=FS, fill=ink)
    for label, v, col, dy in (("palette ceiling 0.934", REPLICA_CEILING, TEXT, -7), ("goal 1% = pixel tracing", REPLICA_CEILING * 0.99, (150, 150, 180, 255), -7),
                              ("goal 3%", REPLICA_CEILING * 0.97, (255, 200, 80, 255), -14), ("goal 4%", REPLICA_CEILING * 0.96, (255, 160, 60, 255), 0)):
        d.line([(L, Y(v)), (W - R, Y(v))], fill=col, width=1)
        d.text((W - R + 6, Y(v) + dy), label, font=FS, fill=col)
    palette = [(216, 48, 124, 255), (80, 180, 255, 255), (120, 220, 120, 255), (240, 120, 60, 255), (200, 140, 255, 255)]
    names = {1: "run 1: skill v1 (0.90 at step 11)", 2: "run 2: v2, draft-grid (step 5)", 3: "run 3: v3, one command (step 2)",
             4: "run 4: goal 1%, stopped at 2.4%", 5: "run 5: goal 3% (step 1)"}
    for (n, folder, rows), col in zip(runs, palette):
        pts = [(X(st), Y(sc)) for st, sc in rows if sc >= lo_v]
        d.line(pts, fill=col, width=2)
        for x, y in pts:
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=col)
        d.text((L + 8, H - B - 16 * (6 - n) - 6), names[n], font=FS, fill=col)
    save(out, "replica-runs.png")


def replica_figure():
    """Juno (110 hand-guided steps) above the replica (a fresh agent, the skill, six steps)."""
    rows = [("Juno, 110 steps", juno), ("replica, 6 steps", Recipe(ROOT / "characters/replica/recipe.toml"))]
    s, lw = 4, 130
    cw = 32 * s
    out = Image.new("RGBA", (lw + len(FACINGS) * cw, 30 + len(rows) * (32 * s + 10)), BG)
    d = ImageDraw.Draw(out)
    for c, fname in enumerate(FACINGS):
        d.text((lw + c * cw + 8, 8), fname.replace("_side", "-side").replace("_l", " (left)"), font=FS, fill=DIM)
    for r, (name, rec) in enumerate(rows):
        y = 30 + r * (32 * s + 10)
        d.text((12, y + 60), name, font=F, fill=TEXT)
        for c, fname in enumerate(FACINGS):
            out.alpha_composite(up(idle(rec, fname), s), (lw + c * cw, y))
    save(out, "replica-vs-juno.png")


SSS_STAGES = [("template", "the animated template"), ("labels", "every pixel labeled"),
              ("shaded", "labels, with the template's shading"), ("first", "the first recipe"),
              ("final", "the recipe after 25 steps")]
SSS_ROTATION = ["down", "down_side", "side", "up_side", "up", "up_side_l", "side_l", "down_side_l"]
# quick colorways for the last stage: material -> one base color (shades are derived)
SSS_VARIANTS = [
    {"hair": "#9dff3a", "jacket": "#3a2a55", "orange": "#ff3fd2", "cyan": "#ffe93f"},
    {"hair": "#7fd8ff", "jacket": "#d6dbe4", "orange": "#2b8cff", "skin": "#e8b894", "pants": "#39404f"},
    {"hair": "#d8262e", "jacket": "#4a1418", "orange": "#ffc83a", "cyan": "#ff5a3c", "skin": "#8a5534"},
    {"hair": "#f4f1e6", "jacket": "#1c1c22", "orange": "#ffe24a", "chrome": "#d9b45a", "skin": "#f0c8a8"},
    {"hair": "#8a4dff", "jacket": "#15294f", "orange": "#ff6fb0", "cyan": "#7dff9a", "pants": "#22222e"},
    {"hair": "#ff8a1f", "jacket": "#135a5c", "orange": "#ffe64a", "skin": "#c98a5e", "shoes": "#ff8a1f"},
    {"hair": "#3a3a44", "jacket": "#7a1f3d", "orange": "#e8e8f0", "cyan": "#ff3f5a", "skin": "#5e3a26"},
    {"hair": "#2fe0c0", "jacket": "#2a2a2a", "orange": "#2fe0c0", "chrome": "#e05a2a", "pants": "#4a3a2a"},
    {"hair": "#f2c14e", "jacket": "#5a3a22", "orange": "#c0392b", "cyan": "#3ff0ff", "skin": "#e0a878"},
    {"hair": "#ff4fd8", "jacket": "#e8e2f0", "orange": "#8a4dff", "pants": "#e8e2f0", "shoes": "#1c1c22"},
]


def _ramp(hex_color: str) -> dict:
    """A full ramp (base/shade/light/deep/blush/ink) from one base color."""
    import colorsys
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s_ = colorsys.rgb_to_hls(r, g, b)
    at = lambda k: tuple(round(c * 255) for c in colorsys.hls_to_rgb(h, max(0, min(1, l * k)), s_))
    return {"base": at(1.0), "shade": at(0.72), "light": at(0.86), "deep": at(0.52), "blush": at(1.05), "ink": at(0.25)}


def _variant(over: dict):
    import copy
    rec = copy.deepcopy(juno)
    for material, col in over.items():
        ramp = _ramp(col)
        rec.ramps[material] = {k: v for k, v in ramp.items() if k in rec.ramps[material] or k in ("base", "shade", "light")}
    return rec


def _font(size: int, bold: bool = True):
    for f in [f"/usr/share/fonts/truetype/noto/NotoSans-ExtraCondensed{'Bold' if bold else ''}.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def _stage_px(stage: str, f, first) -> np.ndarray:
    """One walk frame as a pipeline stage: template tones, flat labels, shaded labels, or a recipe."""
    if stage == "template":
        return _tones(f)
    if stage in ("labels", "shaded"):
        out = np.zeros(f.tones.shape + (4,), np.uint8)
        base = np.array(TONE[1], float)
        for code, col in LABEL_COLORS.items():
            if code == ".":
                continue
            m = (f.labels == code) & (f.tones > 0)
            for t in range(1, 5):
                k = np.array(TONE[t], float) / base if stage == "shaded" else np.ones(3)
                sel = m & (f.tones == t)
                out[sel] = (*np.clip(np.array(col) * k, 0, 255).astype(np.uint8), 255)
        out[f.tones == 5] = (18, 13, 20, 255)  # keep the template's ink outline
        return out
    return render_frame(first if stage == "first" else juno, f)


def semantic_gif():
    """Template -> labels -> shaded labels -> first recipe -> final recipe -> colorways, and back
    through the stages again. Every stage is a whole number of full turns through the eight
    facings while Juno keeps walking (one walk cycle per facing); walking and turning always run
    forward, so the loop is seamless."""
    first = Recipe(ROOT / "characters/juno/history/step-00.toml")
    W, H, s = 480, 480, 10
    per_facing, wipe = 4, 6
    turn = per_facing * len(SSS_ROTATION)
    title_f, caption_f, handle_f = _font(46), _font(20, False), _font(20, False)
    variants = [_variant(v) for v in SSS_VARIANTS]
    names = [n for n, _ in SSS_STAGES] + ["variants"]
    order = names + names[-2:0:-1]  # forward, then back (without repeating the ends)
    turns = {"variants": 2}  # the colorways get two turns
    per_variant = 2 * turn // len(variants)
    captions = dict(SSS_STAGES) | {"variants": "any colorway: a ten-line recipe"}

    def stage_px(stage, f, j):
        if stage == "variants":
            return render_frame(variants[min(j // per_variant, len(variants) - 1)], f)
        return _stage_px(stage, f, first)

    out, k = [], 0
    for si, stage in enumerate(order):
        nxt, n = order[(si + 1) % len(order)], turns.get(stage, 1) * turn
        for j in range(n):
            facing = SSS_ROTATION[(k // per_facing) % len(SSS_ROTATION)]
            walk = frames["walk"][facing]
            f = walk[k % len(walk)]
            px = stage_px(stage, f, j)
            if j >= n - wipe:  # wipe into the next stage (right to left when going back)
                after = stage_px(nxt, f, 0)
                edge = round((j - (n - wipe) + 1) / (wipe + 1) * 32)
                px = px.copy()
                if names.index(nxt) < names.index(stage):
                    px[:, 32 - edge:] = after[:, 32 - edge:]
                else:
                    px[:, :edge] = after[:, :edge]
            out.append(_sss_frame(px, captions[stage], title_f, caption_f, handle_f, W, H, s))
            k += 1
    gif(out, "semantic-sprite-skinning.gif", 100)


def _sss_frame(px, caption, title_f, caption_f, handle_f, W, H, s) -> Image.Image:
    im = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(im)
    # title: "Semantic Sprite " white, "Skinning" magenta
    a, b = "Semantic Sprite ", "Skinning"
    wa, wb = d.textlength(a, font=title_f), d.textlength(b, font=title_f)
    x0 = (W - wa - wb) / 2
    d.text((x0, 18), a, font=title_f, fill=(236, 238, 246))
    d.text((x0 + wa, 18), b, font=title_f, fill=(255, 63, 164))
    # ground shadow + sprite
    cx, top = W // 2, 88
    d.ellipse([cx - 60, top + 31 * s - 14, cx + 60, top + 31 * s + 8], fill=(14, 13, 20))
    im.alpha_composite(up(px, s), (cx - 16 * s, top))
    tw = d.textlength(caption, font=caption_f)
    d.text(((W - tw) / 2, top + 32 * s + 10), caption, font=caption_f, fill=DIM)
    hw = d.textlength("@schlessera", font=handle_f)
    d.text((W - hw - 14, H - 32), "@schlessera", font=handle_f, fill=(150, 152, 175))
    return im


VISOR_FIX, ARM_FIX = "d3f8508", "e589148"  # the commits that fixed the two bugs in the README


def _git_show(rev: str, path: str) -> str:
    return subprocess.run(["git", "show", f"{rev}:{path}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def debugging_figures():
    """Before/after of two bugs the README walks through, rendered from the git history."""
    import dataclasses
    import tempfile
    s = 8
    # 1. the visor tip poking out past the back of the head (3/4 back views)
    with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False) as t:
        t.write(_git_show(VISOR_FIX + "^", "characters/juno/recipe.toml"))
    before, after = Recipe(Path(t.name)), Recipe(ROOT / "characters/juno/history/step-25.toml")
    ims = []
    for label, rec in [("before", before), ("after", after)]:
        pair = Image.new("RGBA", (64 * s, 24 * s), (0, 0, 0, 0))
        for c, facing in enumerate(["up_side", "up_side_l"]):
            pair.alpha_composite(up(idle(rec, facing)[2:26], s), (c * 32 * s, 0))
        ims.append((label, pair))
    save(caption_row(ims, gap=40), "debug-visor.png")
    # 2. right and left arm labels swapped in one frame of the walk to the north-east
    old = _git_show(ARM_FIX + "^", "assets/template/16x32/labels/043.txt")
    old_lab = np.array([list(r.split("|")[2]) for r in old.splitlines() if r and not r.startswith("#")], "<U1")
    walk = frames["walk"]["up_side"]
    rows = []
    for label, f3 in [("template", None), ("before", dataclasses.replace(walk[3], labels=old_lab)), ("after", walk[3])]:
        strip = Image.new("RGBA", (4 * 32 * s, 32 * s), (0, 0, 0, 0))
        for c, f in enumerate(walk[:3] + [f3 or walk[3]]):
            px = _tones(f) if f3 is None else render_frame(juno, f)
            strip.alpha_composite(up(px, s), (c * 32 * s, 0))
        d = ImageDraw.Draw(strip)
        d.rectangle([3 * 32 * s + 2, 2, 4 * 32 * s - 3, 32 * s - 3], outline=(255, 63, 164, 255), width=3)
        rows.append((label, strip))
    out = Image.new("RGBA", (rows[0][1].width + 120, len(rows) * (32 * s + 10) + 10), BG)
    dd = ImageDraw.Draw(out)
    for r, (label, strip) in enumerate(rows):
        y = 10 + r * (32 * s + 10)
        dd.text((12, y + 16 * s - 8), label, font=F, fill=TEXT)
        out.alpha_composite(strip, (120, y))
    save(out, "debug-arms.png")


def variants_figure():
    s = 6
    items = [("template", None), ("Juno", juno), ("Juno (Glitch)", glitch)]
    ims = []
    for name, rec in items:
        pair = Image.new("RGBA", (64 * s, 32 * s), (0, 0, 0, 0))
        pair.alpha_composite(up(idle(rec, "down"), s), (0, 0))
        pair.alpha_composite(up(idle(rec, "side"), s), (32 * s, 0))
        ims.append((name, pair))
    save(caption_row(ims, gap=40), "variants.png")


def walk_gif():
    """All 8 facings walking, template on top, Juno below."""
    s = 3
    fr_t = {f: frames["walk"][f] for f in FACINGS}
    out = []
    for k in range(4):
        im = Image.new("RGBA", (8 * 32 * s + 20, 2 * 32 * s + 30), BG)
        for c, fname in enumerate(FACINGS):
            f = fr_t[fname][k]
            im.alpha_composite(up(_tones(f), s), (10 + c * 32 * s, 10))
            im.alpha_composite(up(render_frame(juno, f), s), (10 + c * 32 * s, 20 + 32 * s))
        out.append(im)
    gif(out, "walk.gif", 140)


def anims_gif():
    """Juno through every animation, facing down-right, one after another."""
    s = 5
    seq = []
    for a in ["idle", "walk", "run", "jump", "attack", "interact"]:
        for f in frames[a]["down_side"]:
            im = Image.new("RGBA", (32 * s + 20, 32 * s + 40), BG)
            im.alpha_composite(up(render_frame(juno, f), s), (10, 30))
            ImageDraw.Draw(im).text((10, 8), a, font=F, fill=TEXT)
            seq.append((im, max(80, f.duration)))
    gif([i for i, _ in seq], "juno-anims.gif", [m for _, m in seq])


def concept_images():
    for src, name, w in [(ROOT / "characters/juno/concept/juno-concept.png", "juno-concept.jpg", 1200),
                         (ROOT / "characters/juno/concept/juno-pixel-mockup.png", "juno-pixel-mockup.jpg", 520),
                         (ROOT / "assets/props/concept/rooftop.png", "rooftop-concept.jpg", 1200)]:
        im = Image.open(src).convert("RGB")
        im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        im.save(OUT / name, quality=86, optimize=True)
        print("wrote", name)


# ---------------------------------------------------------------- props

def resample_vs_drawn():
    """Why concept art is redrawn, not resampled: reference | automatic downscale | hand-drawn."""
    names = ["vending_machine", "dumpster", "fire_barrel", "crates", "neon_sign"]
    s = 5
    rows = []
    for n in names:
        drawn = to_rgba(read(n))
        auto = to_rgba(draft_pixels(n))
        ref = Image.fromarray(reference(n))
        H = drawn.shape[0] * s
        refp = ref.resize((max(1, ref.width * H // ref.height), H), Image.LANCZOS)
        rows.append((n, refp, up(auto, s), up(drawn, s)))
    colw = [max(210, max(r[i].width for r in rows)) for i in (1, 2, 3)]
    rh = [max(r[1].height, r[2].height) for r in rows]
    W = 40 + sum(colw) + 60
    H = 40 + sum(rh) + 16 * len(rows)
    out = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(out)
    heads = ["generated reference", "resampled to game size", "hand-placed pixels"]
    x = 20
    for i, h in enumerate(heads):
        d.text((x, 10), h, font=F, fill=TEXT)
        x += colw[i] + 30
    y = 40
    for (n, refp, auto, drawn), h in zip(rows, rh):
        x = 20
        for im, cw in zip((refp, auto, drawn), colw):
            out.alpha_composite(im.convert("RGBA"), (x + (cw - im.width) // 2, y + h - im.height))
            x += cw + 30
        y += h + 16
    save(out, "props-resample-vs-drawn.png")


def grid_attempt():
    im = Image.open(ROOT / "assets/props/source/experiments/grid-locked-attempt.jpg").convert("RGB")
    g = Image.open(ROOT / "assets/props/source/experiments/grid-locked-guide.png").convert("RGB")
    w = 560
    a = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    b = g.resize((w, round(g.height * w / g.width)), Image.NEAREST)
    save(caption_row([("pixel-grid guide given to the model", b), ("what came back", a)], gap=30), "grid-attempt.png")


def props_sheet():
    shutil.copy(ROOT / "build/preview/props.png", OUT / "props-sheet.png")
    print("wrote props-sheet.png")


TEXTURE_PASS_REV = "454eb44"  # the props just before the texture-and-wear pass
TEXTURE_PASS = ["vending_machine", "dumpster", "water_tank", "crates", "bench", "fire_barrel",
                "neon_sign", "trash_bag", "cardboard_box", "flycar_parked"]


def texture_pass_figure():
    """The same props before and after the texture-and-wear pass (before = git TEXTURE_PASS_REV)."""
    from chargen.pixeltool import _grid_at
    s, gap = 4, 6
    befores = [to_rgba(_grid_at(n, TEXTURE_PASS_REV)) for n in TEXTURE_PASS]
    afters = [to_rgba(read(n)) for n in TEXTURE_PASS]
    W = sum(b.shape[1] for b in befores) + gap * (len(befores) - 1)
    H = max(b.shape[0] for b in befores)
    out = Image.new("RGBA", ((W + 2 * gap) * s + 150, (2 * H + 3 * gap) * s), BG)
    d = ImageDraw.Draw(out)
    for r, (label, ims) in enumerate([("before", befores), ("after", afters)]):
        y = (gap + r * (H + gap)) * s
        d.text((12, y + H * s // 2 - 8), label, font=F, fill=TEXT)
        x = 150 + gap * s
        for im in ims:
            out.alpha_composite(up(im, s), (x, y + (H - im.shape[0]) * s))
            x += (im.shape[1] + gap) * s
    save(out, "props-texture-pass.png")


def props_gif():
    """Animated props, shown in their own light: frames cycle at their real timings (approx)."""
    names = ["fire_barrel", "neon_sign", "vending_machine", "ac_unit", "antenna_mast", "holo_projector", "drone_pad", "mushroom_planter"]
    from chargen.pixeltool import frame_names
    s = 3
    sprites = {n: [to_rgba(read(f)) for f in frame_names(n)] for n in names}
    step = 100
    total = 2400
    out = []
    cols = 4
    cw, ch = 34 * s, 50 * s
    for t in range(0, total, step):
        im = Image.new("RGBA", (cols * cw + 20, 2 * ch + 20), BG)
        for i, n in enumerate(names):
            from chargen.pixeltool import manifest
            ms = manifest()[0][n]["anim"]
            k, acc = 0, t % sum(ms)
            while acc >= ms[k]:
                acc -= ms[k]
                k += 1
            spr = up(sprites[n][k], s)
            x = 10 + (i % cols) * cw + (cw - spr.width) // 2
            y = 10 + (i // cols) * ch + ch - spr.height - 8
            im.alpha_composite(spr, (x, y))
        out.append(im)
    gif(out, "prop-anims.gif", step)


def cars_figure():
    atlas = Image.open(ROOT / "web/data/props/atlas.png")
    meta = json.loads((ROOT / "web/data/props/atlas.json").read_text())["sprites"]
    s = 3
    ims = []
    for n in ["flycar_parked", "flycar_parked_red", "flycar_parked_taxi", "flycar_parked_police", "flycar_parked_black"]:
        m = meta[n]
        ims.append(up(atlas.crop((m["x"], m["y"], m["x"] + m["w"], m["y"] + m["h"])), s))
    juno_px = up(idle(juno, "down_side"), s)
    w = sum(i.width for i in ims[:3]) + 60
    out = Image.new("RGBA", (w + juno_px.width + 40, 2 * (38 * s) + 60), BG)
    x, y = 20, 20
    for i, im in enumerate(ims):
        if i == 3:
            x, y = 20, y + 38 * s + 20
        out.alpha_composite(im, (x, y))
        x += im.width + 20
    out.alpha_composite(juno_px, (out.width - juno_px.width - 20, out.height - juno_px.height - 20))
    save(out, "cars.png")


# ---------------------------------------------------------------- live captures

def captures():
    from playwright.sync_api import sync_playwright
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "8779", "--directory", str(ROOT / "web")],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(0.7)
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1000, "height": 700})
            pg.goto("http://localhost:8779/")
            pg.wait_for_function("window.__game && window.__game.chars.length && window.__game.lighting()")
            pg.evaluate("window.__game.autoFly(false); window.__game.clearFlyers();"
                        "window.__game.hud(false); window.__game.setCharacter('juno')")
            grab = lambda: Image.open(io.BytesIO(base64.b64decode(
                pg.evaluate("document.getElementById('game').toDataURL('image/png')").split(",")[1]))).convert("RGBA")

            def place(x, y, anim="idle", facing="down"):
                pg.evaluate(f"(() => {{ const h = window.__game.hero; h.x = {x}; h.y = {y};"
                            f" Object.assign(h, {{anim: '{anim}', facing: '{facing}', frame: 0, t: 0}}); }})()")

            # lighting off vs on (same spot, paused, fixed time)
            place(216, 132)
            pg.wait_for_timeout(200)
            pg.evaluate("window.__game.pause(true)")
            pg.evaluate("window.__game.setLighting(false); window.__game.draw(4000)")
            off = grab()
            pg.evaluate("window.__game.setLighting(true); window.__game.draw(4000)")
            on = grab()
            save(caption_row([("flat pixel art", up(off, 2)), ("with lights & computed shadows", up(on, 2))], gap=24), "lighting-compare.png")
            # shadows close-up near the fire barrel
            place(290, 94)
            pg.evaluate("window.__game.draw(4200)")
            save(up(grab().crop((200, 0, 400, 150)), 4), "shadows-closeup.png")
            # a flying car passing with its headlight pool
            place(200, 150)
            pg.evaluate("window.__game.setFlyers([{x: 250, y: 120, dir: 1, car: 'flycar_taxi', endX: 1e9, t0: 0}]); window.__game.draw(4400)")
            save(up(grab(), 2), "flyover.png")
            pg.evaluate("window.__game.clearFlyers(); window.__game.pause(false)")

            # hero gif: a seamless loop, stepped at a fixed 100 ms so it is identical on every
            # run. Juno walks up to the fire barrel (its light throws her shadow), kicks, walks
            # back and idles until she is exactly where the loop started; two cars pass, each
            # entering and leaving beyond the lights' reach inside the loop.
            hero_loop(pg, grab)
            b.close()
    finally:
        srv.terminate()


HERO_DT = 100           # ms per GIF frame and simulation step (all sprite frames are multiples)
HERO_START = (200, 140)
HERO_ROUTE = [          # (held key or None, steps); "j" presses attack once, then idles
    (None, 6), ("d", 14), ("w", 12), (None, 4), ("j", 9), (None, 6), ("a", 14), ("s", 12),
]
HERO_CARS = {           # step -> car (x in map px; start and end beyond the lights' reach)
    4: {"x": -420, "y": 175, "dir": 1, "car": "flycar_red", "endX": 920},
    34: {"x": 870, "y": 100, "dir": -1, "car": "flycar_taxi", "endX": -470},
}


def concept_title() -> Image.Image:
    """Juno's name block (name, rule, subtitle) cut from the concept sheet, its dark
    background keyed out to transparency."""
    im = np.asarray(Image.open(ROOT / "characters/juno/concept/juno-concept.png").convert("RGB"))[25:118, 12:418]
    im = im.astype(float)
    bg = np.median(im.reshape(-1, 3), axis=0)
    a = np.clip((np.abs(im - bg).max(2) - 12) / 70, 0, 1)
    rgb = np.clip((im - bg * (1 - a[..., None])) / np.maximum(a[..., None], 1e-3), 0, 255)
    return Image.fromarray(np.dstack([rgb, a * 255]).astype(np.uint8), "RGBA")


def hero_overlay(size: tuple[int, int]) -> Image.Image:
    """Name top left, concept bust bottom right, for compositing over the hero loop."""
    W, H = size
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    title = concept_title()
    title = title.resize((W * 2 // 5, round(title.height * (W * 2 // 5) / title.width)), Image.LANCZOS)
    # soft dark halo behind the letters: the alpha grown a little, blurred, darkened
    from PIL import ImageFilter
    pad = 24
    halo_a = Image.new("L", (title.width + 2 * pad, title.height + 2 * pad), 0)
    halo_a.paste(title.getchannel("A"), (pad, pad))
    halo_a = halo_a.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(9)).point(lambda v: min(255, v * 1.6))
    halo = Image.new("RGBA", halo_a.size, (6, 4, 10, 0))
    halo.putalpha(halo_a.point(lambda v: v * 0.85))
    out.alpha_composite(halo, (16 - pad + 2, 12 - pad + 3))
    out.alpha_composite(title, (16, 12))
    # small labels along the bottom, with the same soft halo as the title
    def label(text, size, x, anchor_right=False, center=False):
        f = _font(size, False)
        tw = int(f.getlength(text))
        tag = Image.new("RGBA", (tw + 2 * pad, size + 8 + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(tag).text((pad, pad), text, font=f, fill=(214, 216, 230, 255))
        halo = tag.getchannel("A").filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(7))
        shade = Image.new("RGBA", tag.size, (6, 4, 10, 0))
        shade.putalpha(halo.point(lambda v: min(255, int(v * 1.4))))
        x0 = (W - tw) // 2 if center else x
        y0 = H - size - 22
        out.alpha_composite(shade, (x0 - pad + 1, y0 - pad + 2))
        out.alpha_composite(tag, (x0 - pad, y0 - pad))
    label("@schlessera", 22, 16)
    label("Semantic Sprite Skinning Demo", 15, 0, center=True)
    bust = Image.open(ROOT / "characters/juno/concept/juno-bust.png").convert("RGBA")
    bust = bust.crop(bust.getbbox())
    h = H * 3 // 5
    bust = bust.resize((round(bust.width * h / bust.height), h), Image.LANCZOS)
    out.alpha_composite(bust, (W - bust.width - 8, H - bust.height))
    return out


def border_vignette(size: tuple[int, int], width: int = 70, strength: float = 0.45) -> Image.Image:
    """Darkening that only creeps in from the frame's edges (flat in the middle, no ellipse)."""
    W, H = size
    x = np.minimum(np.arange(W), W - 1 - np.arange(W)) / width
    y = np.minimum(np.arange(H), H - 1 - np.arange(H)) / width
    fx, fy = np.clip(1 - x, 0, 1) ** 2, np.clip(1 - y, 0, 1) ** 2
    a = strength * np.maximum(fx[None, :], fy[:, None])
    v = Image.new("RGBA", size, (4, 3, 8, 0))
    v.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
    return v


def hero_loop(pg, grab):
    """Two passes: the first finds the loop length, the second renders it with every prop
    animation fitted to a whole number of cycles (engine `loopMs`), so there is no seam."""
    n = _hero_pass(pg, None)
    pg.evaluate(f"window.__game.loopMs({n * HERO_DT})")
    shots = _hero_pass(pg, grab)
    pg.evaluate("window.__game.loopMs(0)")
    frames = [up(s_, 2) for s_ in shots[:-1]]
    vignette, overlay = border_vignette(frames[0].size), hero_overlay(frames[0].size)
    for f in frames:
        f.alpha_composite(vignette)
        f.alpha_composite(overlay)
    gif(frames, "hero.gif", HERO_DT)
    diff = np.abs(np.asarray(shots[0], int) - np.asarray(shots[-1], int)).max()
    print(f"hero loop: {len(shots) - 1} frames, {(len(shots) - 1) * HERO_DT} ms, seam difference {diff}")
    pg.evaluate("window.__game.pause(false)")


def _hero_pass(pg, grab):
    """Returns the frame count (grab=None) or the frames plus the loop-end frame for a seam check."""
    g = "window.__game"
    pg.evaluate(f"(() => {{ const g = {g}; g.pause(true); g.clearFlyers(); g.keys.clear();"
                f" Object.assign(g.hero, {{x: {HERO_START[0]}, y: {HERO_START[1]}, anim: 'idle', facing: 'down',"
                f" frame: 0, t: 0}}); }})()")
    state = lambda: pg.evaluate(f"(() => {{ const h = {g}.hero; return [h.x, h.y, h.anim, h.facing, h.frame, h.t,"
                                f" {g}.flyers().length]; }})()")
    start = state()
    plan = [k if i == 0 or k != "j" else None for k, n in HERO_ROUTE for i in range(n)]
    shots, step = [], 0
    while True:
        if step >= len(plan) and state() == start:
            break
        assert step < 400, "hero loop never returned to its start state"
        if grab:
            pg.evaluate(f"{g}.draw({step * HERO_DT})")
            shots.append(grab())
        key = plan[step] if step < len(plan) else None
        if step in HERO_CARS:
            car = json.dumps({**HERO_CARS[step], "t0": step * HERO_DT})
            pg.evaluate(f"{g}.flyers().push({car})")
        pg.evaluate(f"(() => {{ const g = {g}; g.keys.clear();"
                    + (f" if ('{key}' === 'j') g.press('j'); else g.keys.add('{key}');" if key else "")
                    + f" g.update({HERO_DT}); }})()")
        step += 1
        if step == len(plan):  # the route must return exactly (a blocked step would drift)
            x, y = state()[:2]
            assert abs(x - start[0]) < 1e-6 and abs(y - start[1]) < 1e-6, f"route ends at {x},{y}"
            pg.evaluate(f"Object.assign({g}.hero, {{x: {start[0]}, y: {start[1]}}})")  # float drift
    if not grab:
        return step
    pg.evaluate(f"{g}.draw({step * HERO_DT})")  # the state the loop wraps into: must equal frame 0
    return shots + [grab()]


if __name__ == "__main__":
    template_sheet()
    label_figure()
    label_sheet()
    facings_figure()
    iteration_figures()
    replica_chart()
    replica_figure()
    semantic_gif()
    debugging_figures()
    variants_figure()
    walk_gif()
    anims_gif()
    concept_images()
    resample_vs_drawn()
    grid_attempt()
    props_sheet()
    texture_pass_figure()
    props_gif()
    cars_figure()
    captures()

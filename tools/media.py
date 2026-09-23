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


def _snapshots():
    """(step, recipe) for every saved iteration step (characters/juno/history/step-NN.toml)."""
    steps = sorted((ROOT / "characters/juno/history").glob("step-*.toml"))
    return [(int(p.stem.split("-")[1]), Recipe(p)) for p in steps]


def iteration_figures():
    """Pixel mockup, then the recipe after every saved iteration step, left to right."""
    from chargen.mockup import MOCKUP_FACINGS, extract, place, similarity
    sprites = extract(ROOT / "characters/juno/concept/juno-pixel-mockup.png")
    snaps = _snapshots()
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

    # similarity to the mockup per saved step
    scores = []
    for n, rec in snaps:
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
    shadow = Image.new("RGBA", title.size, (8, 6, 12, 0))
    shadow.putalpha(title.getchannel("A").point(lambda v: v * 0.8))
    out.alpha_composite(shadow, (16 + 2, 12 + 2))
    out.alpha_composite(title, (16, 12))
    bust = Image.open(ROOT / "characters/juno/concept/juno-bust.png").convert("RGBA")
    bust = bust.crop(bust.getbbox())
    h = H * 3 // 5
    bust = bust.resize((round(bust.width * h / bust.height), h), Image.LANCZOS)
    out.alpha_composite(bust, (W - bust.width - 8, H - bust.height))
    return out


def hero_loop(pg, grab):
    """Two passes: the first finds the loop length, the second renders it with every prop
    animation fitted to a whole number of cycles (engine `loopMs`), so there is no seam."""
    n = _hero_pass(pg, None)
    pg.evaluate(f"window.__game.loopMs({n * HERO_DT})")
    shots = _hero_pass(pg, grab)
    pg.evaluate("window.__game.loopMs(0)")
    frames = [up(s_, 2) for s_ in shots[:-1]]
    overlay = hero_overlay(frames[0].size)
    for f in frames:
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

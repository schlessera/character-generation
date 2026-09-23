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
    # one shared adaptive palette keeps colors stable across frames (no flicker)
    pal = rgb[0].quantize(colors=255, method=Image.Quantize.MEDIANCUT)
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

            # hero gif: Juno walks through the lit roof while cars fly over
            place(120, 132, "walk", "side")
            pg.evaluate("window.__game.setFlyers([{x: -160, y: 175, dir: 1, car: 'flycar_red', endX: 900, t0: 0},"
                        "{x: 640, y: 95, dir: -1, car: 'flycar_taxi', endX: -400, t0: 0}])")
            shots = []
            keys = [("d", 1600), ("s", 500), ("d", 900), ("w", 700)]
            for key, dur in keys:
                pg.keyboard.down(key)
                t_end = time.time() + dur / 1000
                while time.time() < t_end:
                    shots.append(grab())
                    pg.wait_for_timeout(70)
                pg.keyboard.up(key)
            pg.keyboard.press("j")
            for _ in range(8):
                shots.append(grab())
                pg.wait_for_timeout(70)
            gif([up(s_, 2) for s_ in shots], "hero.gif", 95)
            b.close()
    finally:
        srv.terminate()


if __name__ == "__main__":
    template_sheet()
    label_figure()
    label_sheet()
    facings_figure()
    variants_figure()
    walk_gif()
    anims_gif()
    concept_images()
    resample_vs_drawn()
    grid_attempt()
    props_sheet()
    props_gif()
    cars_figure()
    captures()

"""Build the template catalog: normalized animations, per-frame pixels, head tracking.

The catalog is the single internal representation every other step builds on:
  anims[name][dir] -> list of frame indices (+ durations)
  frames[i] -> RGBA pixels, class map (palette tone), head placement
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .aseprite import read

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "vendor/eris-esra-character-templates"

# Template tones. Every template pixel is exactly one of these.
TONES = {
    "base": (250, 243, 232),     # lit skin / fill
    "shade": (185, 179, 161),    # shaded fill, far side
    "light": (231, 213, 198),    # soft shade: face contour, mouth, nose
    "blush": (209, 157, 167),    # cheeks
    "ink": (47, 37, 34),         # outline, eyes, darkest fill (far limbs)
}
TONE_IDS = {name: i + 1 for i, name in enumerate(TONES)}  # 0 = transparent
DIRS = ["down", "down_side", "side", "up_side", "up"]
ROTATE_DIRS = ["down", "down_side", "side", "up_side", "up", "up_side_l", "side_l", "down_side_l"]


@dataclass
class HeadFit:
    dir: str
    flip: bool
    x: int  # top-left of head template in frame coords
    y: int
    score: float


@dataclass
class Template:
    size: str
    w: int
    h: int
    rgba: np.ndarray            # N x H x W x 4
    tones: np.ndarray           # N x H x W uint8 (TONE_IDS)
    durations: list[int]
    anims: dict[str, dict[str, list[int]]]
    heads: dict[str, np.ndarray] = field(default_factory=dict)  # dir -> tone crop (0 = not head)
    head_fits: list[HeadFit] = field(default_factory=list)


def _tones(rgba: np.ndarray) -> np.ndarray:
    out = np.zeros(rgba.shape[:-1], np.uint8)
    for name, rgb in TONES.items():
        m = np.all(rgba[..., :3] == rgb, axis=-1) & (rgba[..., 3] > 0)
        out[m] = TONE_IDS[name]
    unknown = (rgba[..., 3] > 0) & (out == 0)
    assert not unknown.any(), "template has off-palette pixels"
    return out


def _normalize_tags(tags) -> dict[str, dict[str, list[int]]]:
    """Map raw aseprite tags to anims[anim][dir]. Direction comes from tag order
    within an animation (the source file has typos such as a second 'Jump_Side'
    that is really Jump_Up), always down, down_side, side, up_side, up."""
    anims: dict[str, dict[str, list[int]]] = {}
    for t in tags:
        anim = re.split(r"[ _]", t.name)[0].lower()
        anim = {"punch": "attack"}.get(anim, anim)
        frames = list(range(t.start, t.end + 1))
        if anim == "rotate":
            anims["rotate"] = {"all": frames}
            continue
        dirs = anims.setdefault(anim, {})
        dirs[DIRS[len(dirs)]] = frames
    return anims


HEAD_ROWS = 11  # skull top to chin in every idle direction of the 16x32 template


def _head_template(tones: np.ndarray) -> np.ndarray:
    """Crop the head from an idle frame: HEAD_ROWS rows from the top opaque row."""
    top = np.where(tones.any(axis=1))[0][0]
    crop = tones[top:top + HEAD_ROWS]
    cols = np.where(crop.any(axis=0))[0]
    return crop[:, cols[0]:cols[-1] + 1].copy()


def _fit_head(tones: np.ndarray, heads: dict[str, np.ndarray], dirs: list[str], flips=(False, True)) -> HeadFit:
    """Slide each head template over the frame. Score mixes silhouette agreement
    (robust to redrawn faces) with exact tone agreement (disambiguates direction)."""
    best = HeadFit("down", False, 0, 0, -1.0)
    H, W = tones.shape
    ink = TONE_IDS["ink"]
    for d in dirs:
        for flip in flips:
            t = heads[d][:, ::-1] if flip else heads[d]
            th, tw = t.shape
            for y in range(0, H - th + 1):
                for x in range(0, W - tw + 1):
                    win = tones[y:y + th, x:x + tw]
                    sil = ((win > 0) == (t > 0)).mean()
                    outline = ((win == ink) == (t == ink)).mean()
                    exact = (win == t)[t > 0].mean()
                    score = 0.4 * sil + 0.3 * outline + 0.3 * exact
                    if score > best.score:
                        best = HeadFit(d, flip, x, y, float(score))
    return best


def load(size: str = "16x32") -> Template:
    a = read(str(RAW / size / f"{size} All Animations.aseprite"))
    rgba = np.stack([a.flatten(i) for i in range(len(a.frames))])
    tones = np.stack([_tones(f) for f in rgba])
    anims = _normalize_tags(a.tags)
    tpl = Template(size, a.width, a.height, rgba, tones, [f.duration_ms for f in a.frames], anims)
    for d in DIRS:
        tpl.heads[d] = _head_template(tones[anims["idle"][d][0]])
    frame_dir = {i: d for a_, dd in anims.items() for d, fr in dd.items() for i in fr}
    for i, t in enumerate(tones):
        d = frame_dir[i]
        # Idle/walk/run/interact/jump keep the tagged facing. Rotate and attack
        # spin the head, so search every direction and mirror.
        if d in DIRS and i not in anims["attack"][d]:
            tpl.head_fits.append(_fit_head(t, tpl.heads, [d], (False,)))
        else:
            tpl.head_fits.append(_fit_head(t, tpl.heads, DIRS))
    return tpl


def save_meta(tpl: Template, path: Path) -> None:
    meta = {
        "size": tpl.size, "frame_w": tpl.w, "frame_h": tpl.h,
        "durations": tpl.durations, "anims": tpl.anims,
        "head_fits": [f.__dict__ for f in tpl.head_fits],
    }
    path.write_text(json.dumps(meta, indent=1))

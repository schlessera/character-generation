"""Per-frame body-part label maps for the template.

Labels are the one-time investment that makes characters cheap: a character is a
recipe that maps (part, tone) -> color plus a few anchored overlays, so every new
character reuses these maps across all frames.

Storage: assets/template/<size>/labels/NNN.txt, one file per unique frame, two
aligned grids per row so humans and agents can edit them in a text editor:
    YY |<tones, 32 chars>|<labels, 32 chars>|
Duplicate frames (identical pixels) share the canonical frame's file.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from .ascii import TONE_CHARS
from .catalog import HEAD_ROWS, ROOT, Template

# Anatomical sides: R = the character's right. Facing down, their right is screen-left.
PARTS = {
    ".": "none",
    "H": "head",        # skull, face, ears, and the head's outline
    "N": "neck",
    "T": "torso",       # chest, belly, hips/pelvis
    "R": "arm_r", "r": "hand_r",
    "L": "arm_l", "l": "hand_l",
    "P": "leg_r", "p": "foot_r",
    "Q": "leg_l", "q": "foot_l",
    "X": "fx",          # attack smears / motion effects
}
# Recipes may target a group instead of individual parts.
GROUPS = {
    "arms": "RL", "hands": "rl", "legs": "PQ", "feet": "pq",
    "upper": "NTRL", "lower": "PQ", "body": "NTRLrlPQpq",
}
LABEL_DIR = ROOT / "assets/template"


def canonical_frames(tpl: Template) -> list[int]:
    """canon[i] = first frame index with identical pixels."""
    seen: dict[str, int] = {}
    canon = []
    for i, f in enumerate(tpl.rgba):
        h = hashlib.md5(f.tobytes()).hexdigest()
        canon.append(seen.setdefault(h, i))
    return canon


def frame_info(tpl: Template) -> dict[int, tuple[str, str, int]]:
    info = {}
    for a, dirs in tpl.anims.items():
        for d, fr in dirs.items():
            for k, i in enumerate(fr):
                info[i] = (a, d, k)
    return info


def propose(tpl: Template, i: int) -> np.ndarray:
    """Rough automatic labels: head from head tracking, a hip line, screen-side split."""
    tones = tpl.tones[i]
    fit = tpl.head_fits[i]
    _, d, _ = frame_info(tpl)[i]
    lab = np.full(tones.shape, ".", "<U1")
    op = tones > 0
    head = np.zeros_like(op)
    hw = tpl.heads[fit.dir].shape[1]
    hmask = tpl.heads[fit.dir] > 0
    if fit.flip:
        hmask = hmask[:, ::-1]
    head[fit.y:fit.y + HEAD_ROWS, fit.x:fit.x + hw] = hmask
    head &= op
    lab[head] = "H"
    ys, xs = np.where(op & ~head)
    if len(ys) == 0:
        return lab
    bottom = fit.y + HEAD_ROWS
    hip = bottom + 9
    cx = fit.x + hw / 2
    screen_left_is_right = d in ("down", "down_side")
    for y, x in zip(ys, xs):
        left = x < cx
        rside = left == screen_left_is_right
        if y <= bottom:
            lab[y, x] = "N"
        elif y < hip:
            lab[y, x] = "T"
        else:
            foot = y >= tones.shape[0] - 2
            lab[y, x] = ("p" if foot else "P") if rside else ("q" if foot else "Q")
    return lab


def path(tpl: Template, i: int) -> Path:
    return LABEL_DIR / tpl.size / "labels" / f"{i:03d}.txt"


def write(tpl: Template, i: int, lab: np.ndarray) -> None:
    a, d, k = frame_info(tpl)[i]
    fit = tpl.head_fits[i]
    lines = [f"# frame {i} {a}/{d}[{k}] {tpl.durations[i]}ms head={fit.dir}{'(flip)' if fit.flip else ''}@{fit.x},{fit.y}"]
    for y in range(tpl.h):
        t = "".join(TONE_CHARS[v] for v in tpl.tones[i][y])
        lines.append(f"{y:02d} |{t}|{''.join(lab[y])}|")
    p = path(tpl, i)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n")


def read_labels(tpl: Template, i: int) -> np.ndarray:
    rows = [l for l in path(tpl, i).read_text().splitlines() if l and not l.startswith("#")]
    lab = np.array([list(r.split("|")[2]) for r in rows], "<U1")
    return lab


def load_all(tpl: Template) -> np.ndarray:
    canon = canonical_frames(tpl)
    return np.stack([read_labels(tpl, canon[i]) for i in range(len(canon))])


def validate(tpl: Template) -> list[str]:
    errs = []
    canon = canonical_frames(tpl)
    for i in sorted(set(canon)):
        try:
            lab = read_labels(tpl, i)
        except Exception as e:  # noqa: BLE001
            errs.append(f"{i}: unreadable ({e})")
            continue
        if lab.shape != tpl.tones[i].shape:
            errs.append(f"{i}: shape {lab.shape}")
            continue
        bad = set(np.unique(lab)) - set(PARTS)
        if bad:
            errs.append(f"{i}: unknown labels {bad}")
        op = tpl.tones[i] > 0
        if ((lab != ".") != op).any():
            n = ((lab != ".") != op).sum()
            errs.append(f"{i}: {n} px where label/opacity disagree")
    return errs

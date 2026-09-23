"""Contact sheets for visual verification. One row per (anim, dir), frames left to right."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

BG = (60, 62, 80, 255)


def contact_sheet(frames: list[np.ndarray], rows: list[list[int]], labels: list[str],
                  scale: int = 6, boxes: dict[int, list[tuple]] | None = None) -> Image.Image:
    """frames: RGBA arrays. rows: frame indices per row. boxes: frame -> [(x0,y0,x1,y1,color)]."""
    h, w = frames[0].shape[:2]
    cols = max(len(r) for r in rows)
    lw = 110
    cell_w, cell_h = w * scale + 4, h * scale + 4
    sheet = Image.new("RGBA", (lw + cols * cell_w, len(rows) * cell_h), BG)
    d = ImageDraw.Draw(sheet)
    for ri, (row, label) in enumerate(zip(rows, labels)):
        d.text((4, ri * cell_h + cell_h // 2 - 5), label, fill=(230, 230, 230, 255))
        for ci, fi in enumerate(row):
            im = Image.fromarray(frames[fi]).resize((w * scale, h * scale), Image.NEAREST)
            ox, oy = lw + ci * cell_w + 2, ri * cell_h + 2
            d.rectangle([ox - 1, oy - 1, ox + w * scale, oy + h * scale], outline=(80, 84, 104, 255))
            sheet.alpha_composite(im, (ox, oy))
            d.text((ox + 2, oy + 1), str(fi), fill=(150, 150, 170, 255))
            for (x0, y0, x1, y1, c) in (boxes or {}).get(fi, []):
                d.rectangle([ox + x0 * scale, oy + y0 * scale, ox + x1 * scale - 1, oy + y1 * scale - 1], outline=c)
    return sheet


def anim_rows(anims: dict) -> tuple[list[list[int]], list[str]]:
    rows, labels = [], []
    for a, dirs in anims.items():
        for d, fr in dirs.items():
            rows.append(fr)
            labels.append(f"{a}/{d}")
    return rows, labels

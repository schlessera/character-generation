"""ASCII views of tone maps: the fastest way to read and hand-edit template pixels."""
import numpy as np

TONE_CHARS = " .slb#"  # 0 transparent, base, shade, light, blush, ink


def tone_ascii(tones: np.ndarray) -> list[str]:
    return ["".join(TONE_CHARS[v] for v in row) for row in tones]


def side_by_side(grids: list[list[str]], gap: str = " | ") -> str:
    return "\n".join(f"{y:2d} " + gap.join(g[y] for g in grids) for y in range(len(grids[0])))

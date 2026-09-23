"""Generate web/bluenoise.png: a tileable 64x64 blue-noise threshold map (void and cluster).

Blue noise has almost no low-frequency energy, so dithering with it reads as fine, even
grain instead of the cross-hatch of ordered (Bayer) dithering or the clumps of white noise.
The lighting uses it to break up the edges of its flat light bands (see docs/lighting.md).
Deterministic: the same seed always gives the same texture.

  uv run python tools/bluenoise.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

N, SIGMA, SEED = 64, 1.5, 7
ROOT = Path(__file__).resolve().parent.parent


def _kernel() -> np.ndarray:
    d = np.minimum(np.arange(N), N - np.arange(N))  # toroidal distance: the map tiles
    return np.exp(-(d[:, None] ** 2 + d[None, :] ** 2) / (2 * SIGMA ** 2))


def void_and_cluster() -> np.ndarray:
    K = np.fft.rfft2(_kernel())
    energy = lambda m: np.fft.irfft2(np.fft.rfft2(m) * K, s=(N, N))
    rng = np.random.default_rng(SEED)
    pts = np.zeros((N, N), bool)
    pts.flat[rng.choice(N * N, N * N // 10, replace=False)] = True
    while True:  # relax the initial pattern: move the tightest cluster into the largest void
        e = energy(pts)
        c = np.argmax(np.where(pts, e, -np.inf))
        pts.flat[c] = False
        v = np.argmin(np.where(pts, np.inf, energy(pts)))
        if v == c:
            pts.flat[c] = True
            break
        pts.flat[v] = True
    rank = np.zeros((N, N), int)
    ones = int(pts.sum())
    p = pts.copy()
    for r in range(ones - 1, -1, -1):  # phase 1: remove clusters, ranking downward
        c = np.argmax(np.where(p, energy(p), -np.inf))
        p.flat[c] = False
        rank.flat[c] = r
    p = pts.copy()
    for r in range(ones, N * N):  # phases 2-3: fill voids, ranking upward
        v = np.argmin(np.where(p, np.inf, energy(p)))
        p.flat[v] = True
        rank.flat[v] = r
    return rank


if __name__ == "__main__":
    rank = void_and_cluster()
    img = (rank * 256 // (N * N)).astype(np.uint8)
    out = ROOT / "web/bluenoise.png"
    Image.fromarray(img).save(out)
    print(out, img.shape, "mean", round(float(img.mean()), 1))

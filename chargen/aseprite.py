"""Minimal Aseprite (.aseprite/.ase) reader: layers, frames, cels, tags, durations.

Spec: https://github.com/aseprite/aseprite/blob/main/docs/ase-file-specs.md
Supports RGBA color depth (32bpp), raw/compressed image cels, linked cels.
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field

import numpy as np


@dataclass
class Layer:
    index: int
    name: str
    flags: int
    type: int  # 0 image, 1 group, 2 tilemap
    child_level: int
    opacity: int
    blend: int

    @property
    def visible(self) -> bool:
        return bool(self.flags & 1)


@dataclass
class Cel:
    layer: int
    x: int
    y: int
    opacity: int
    image: np.ndarray  # HxWx4 uint8


@dataclass
class Frame:
    duration_ms: int
    cels: dict[int, Cel] = field(default_factory=dict)


@dataclass
class Tag:
    name: str
    start: int
    end: int
    direction: int  # 0 fwd, 1 reverse, 2 pingpong, 3 pingpong reverse
    repeat: int


@dataclass
class AsepriteFile:
    width: int
    height: int
    depth: int
    layers: list[Layer]
    frames: list[Frame]
    tags: list[Tag]

    def flatten(self, frame: int, visible_only: bool = True, layers: set[int] | None = None) -> np.ndarray:
        """Composite a frame (normal blend, straight alpha) into HxWx4 uint8."""
        out = np.zeros((self.height, self.width, 4), np.float32)
        for li, layer in enumerate(self.layers):
            if layer.type != 0 or (visible_only and not self._visible(li)):
                continue
            if layers is not None and li not in layers:
                continue
            cel = self.frames[frame].cels.get(li)
            if cel is None:
                continue
            _blit(out, cel.image, cel.x, cel.y, cel.opacity / 255 * layer.opacity / 255)
        return np.clip(out, 0, 255).astype(np.uint8)

    def _visible(self, li: int) -> bool:
        # A layer is visible only if it and all its parent groups are visible.
        layer = self.layers[li]
        if not layer.visible:
            return False
        level = layer.child_level
        for j in range(li - 1, -1, -1):
            if self.layers[j].child_level < level:
                if not self.layers[j].visible:
                    return False
                level = self.layers[j].child_level
        return True


def _blit(dst: np.ndarray, src: np.ndarray, x: int, y: int, opacity: float) -> None:
    h, w = src.shape[:2]
    H, W = dst.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    d = dst[y0:y1, x0:x1]
    sa = s[..., 3:4] / 255 * opacity
    da = d[..., 3:4] / 255
    oa = sa + da * (1 - sa)
    rgb = np.where(oa > 0, (s[..., :3] * sa + d[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6), 0)
    d[..., :3] = rgb
    d[..., 3:4] = oa * 255


def read(path: str) -> AsepriteFile:
    data = open(path, "rb").read()
    (_size, magic, nframes, W, H, depth) = struct.unpack_from("<IHHHHH", data, 0)
    assert magic == 0xA5E0, "not an aseprite file"
    assert depth == 32, f"only RGBA supported, got {depth}bpp"
    off = 128
    layers: list[Layer] = []
    frames: list[Frame] = []
    tags: list[Tag] = []

    def string(o: int) -> tuple[str, int]:
        (n,) = struct.unpack_from("<H", data, o)
        return data[o + 2:o + 2 + n].decode("utf-8"), o + 2 + n

    for _ in range(nframes):
        fsize, fmagic, old_chunks, dur = struct.unpack_from("<IHHH", data, off)
        assert fmagic == 0xF1FA
        (new_chunks,) = struct.unpack_from("<I", data, off + 12)
        nchunks = new_chunks or old_chunks
        frame = Frame(dur)
        frames.append(frame)
        co = off + 16
        for _ in range(nchunks):
            csize, ctype = struct.unpack_from("<IH", data, co)
            body = co + 6
            if ctype == 0x2004:  # layer
                flags, ltype, level, _dw, _dh, blend, opacity = struct.unpack_from("<HHHHHHB", data, body)
                name, _ = string(body + 16)
                layers.append(Layer(len(layers), name, flags, ltype, level, opacity, blend))
            elif ctype == 0x2005:  # cel
                li, x, y, op, ctype2, _z = struct.unpack_from("<HhhBHh", data, body)
                p = body + 16
                if ctype2 == 1:  # linked
                    (src,) = struct.unpack_from("<H", data, p)
                    c = frames[src].cels[li]
                    frame.cels[li] = Cel(li, x, y, op, c.image)
                elif ctype2 in (0, 2):
                    w, h = struct.unpack_from("<HH", data, p)
                    raw = data[p + 4:co + csize]
                    if ctype2 == 2:
                        raw = zlib.decompress(raw)
                    img = np.frombuffer(raw[:w * h * 4], np.uint8).reshape(h, w, 4).copy()
                    frame.cels[li] = Cel(li, x, y, op, img)
            elif ctype == 0x2018:  # tags
                (n,) = struct.unpack_from("<H", data, body)
                p = body + 10
                for _ in range(n):
                    a, b, d, rep = struct.unpack_from("<HHBH", data, p)
                    name, p = string(p + 17)
                    tags.append(Tag(name, a, b, d, rep))
            co += csize
        off += fsize
    return AsepriteFile(W, H, depth, layers, frames, tags)

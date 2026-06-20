"""ColorField — the L0 color primitive (per-cell OKLab, UNVERIFIABLE-aware)."""
from __future__ import annotations

from dataclasses import dataclass

from .color import Triple, srgb_to_oklab
from .pngview import decode_png


@dataclass(frozen=True)
class ColorField:
    """A 2-D field of OKLab color triples with a first-class UNVERIFIABLE mask.

    lab     — row-major, length width*height; each entry an (L, a, b) triple.
    unknown — row-major bool mask, True where the cell is UNVERIFIABLE.
    """

    width: int
    height: int
    lab: tuple[Triple, ...]
    unknown: tuple[bool, ...]

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("color field dimensions must be positive")
        n = self.width * self.height
        if len(self.lab) != n:
            raise ValueError(f"lab length {len(self.lab)} != {n}")
        if len(self.unknown) != n:
            raise ValueError(f"unknown length {len(self.unknown)} != {n}")

    def index(self, x: int, y: int) -> int:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError(f"({x},{y}) out of {self.width}x{self.height}")
        return y * self.width + x

    def at(self, x: int, y: int) -> Triple:
        return self.lab[self.index(x, y)]

    def is_unknown(self, x: int, y: int) -> bool:
        return self.unknown[self.index(x, y)]


def color_field_from_png(payload: bytes) -> ColorField:
    """Lower an 8-bit PNG into an OKLab ColorField. Raises PngDecodeError on
    anything undecodable (the caller fail-closes)."""
    img = decode_png(payload)
    n = img.width * img.height
    ch = img.channels
    px = img.pixels
    lab: list[Triple] = [(0.0, 0.0, 0.0)] * n
    for i in range(n):
        if ch == 1:
            v = px[i] / 255.0
            rgb = (v, v, v)
        elif ch == 2:
            v = px[i * 2] / 255.0
            rgb = (v, v, v)
        else:                       # 3=RGB or 4=RGBA (alpha ignored)
            base = i * ch
            rgb = (px[base] / 255.0, px[base + 1] / 255.0, px[base + 2] / 255.0)
        lab[i] = srgb_to_oklab(rgb)
    return ColorField(img.width, img.height, tuple(lab), (False,) * n)

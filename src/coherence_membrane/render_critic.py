"""Render-critic — wire the vintage renderer to the grounded critic + memory.

render -> perceive -> critique(compose[novelty vs corpus, structural fitness =
OKLab-dE source-vs-output fidelity]) -> remember, as a generator yielding witnessed
step events. Composes shipped parts; retro.py untouched. Stdlib only; inert.
"""
from __future__ import annotations

from .color import delta_e_ok
from .color_field import color_field_from_png, downscale_color_field

FIDELITY_CW = 64


def render_fidelity_deviation(form) -> float:
    """Mean OKLab dE between source and output, downscaled to a common grid.
    `form = (source_png, output_png)`. inf when nothing comparable (fail-closed)."""
    source_png, output_png = form
    src = color_field_from_png(source_png)
    out = color_field_from_png(output_png)
    cw = min(src.width, out.width, FIDELITY_CW)
    ch = max(1, round(cw * src.height / src.width))
    ch = min(ch, src.height, out.height)
    s = downscale_color_field(src, cw, ch)
    o = downscale_color_field(out, cw, ch)
    diffs = [delta_e_ok(s.lab[i], o.lab[i]) for i in range(cw * ch)
             if not s.unknown[i] and not o.unknown[i]]
    if not diffs:
        return float("inf")
    return sum(diffs) / len(diffs)

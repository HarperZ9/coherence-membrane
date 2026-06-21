from __future__ import annotations

from coherence_membrane.pngencode import encode_png
from coherence_membrane.retro import render_vintage
from coherence_membrane.render_critic import render_fidelity_deviation


def _gradient_png(w=32, h=32) -> bytes:
    """A deterministic horizontal RGB gradient PNG (something to quantize)."""
    rows = bytearray()
    for y in range(h):
        for x in range(w):
            rows.extend((int(255 * x / (w - 1)), int(255 * y / (h - 1)), 128))
    return encode_png(w, h, bytes(rows), channels=3)


def test_fidelity_faithful_lower_than_aggressive():
    src = _gradient_png()
    faithful = render_vintage(src, target_width=32, palette_k=16, dither=True, scanlines=False)
    aggressive = render_vintage(src, target_width=4, palette_k=2, dither=False, scanlines=True)
    dev_faithful = render_fidelity_deviation((src, faithful.output_png))
    dev_aggressive = render_fidelity_deviation((src, aggressive.output_png))
    assert dev_faithful >= 0.0
    assert dev_faithful < dev_aggressive   # a faithful render is structurally closer to the source


def test_fidelity_identity_is_near_zero():
    # comparing a render to itself (as both source and output) is ~0 deviation
    src = _gradient_png()
    r = render_vintage(src, target_width=32, palette_k=16, scanlines=False)
    assert render_fidelity_deviation((r.output_png, r.output_png)) < 1e-9

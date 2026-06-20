from __future__ import annotations

import math

from coherence_membrane.color import (
    linear_to_srgb,
    oklab_to_srgb,
    srgb_to_linear,
    srgb_to_oklab,
)


def test_gamma_roundtrip_and_anchors():
    assert abs(srgb_to_linear(0.0)) < 1e-12
    assert abs(srgb_to_linear(1.0) - 1.0) < 1e-12
    for c in (0.0, 0.04, 0.2, 0.5, 1.0):
        assert abs(linear_to_srgb(srgb_to_linear(c)) - c) < 1e-9


def test_oklab_canonical_anchors():
    # canonical Ottosson: sRGB white -> (1,0,0), black -> (0,0,0)
    L, a, b = srgb_to_oklab((1.0, 1.0, 1.0))
    assert abs(L - 1.0) < 1e-3 and abs(a) < 1e-3 and abs(b) < 1e-3
    L0, a0, b0 = srgb_to_oklab((0.0, 0.0, 0.0))
    assert abs(L0) < 1e-6 and abs(a0) < 1e-6 and abs(b0) < 1e-6


def test_oklab_roundtrip():
    for rgb in [(1, 0, 0), (0, 1, 0), (0, 0, 1), (0.2, 0.5, 0.8), (0.5, 0.5, 0.5)]:
        rgb = tuple(float(c) for c in rgb)
        rt = oklab_to_srgb(srgb_to_oklab(rgb))
        assert all(abs(rt[i] - rgb[i]) < 1e-6 for i in range(3))

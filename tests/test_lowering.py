from __future__ import annotations

import pytest

from coherence_membrane.field import FieldKind
from coherence_membrane.lowering import field_from_png
from coherence_membrane.pngencode import encode_png
from coherence_membrane.pngview import PngDecodeError


def _uniform_png(value, w=4, h=4):
    return encode_png(w, h, bytes([value, value, value] * (w * h)), channels=3)


def test_field_from_png_white_is_one():
    f = field_from_png(_uniform_png(255))
    assert f.kind is FieldKind.LUMINANCE
    assert f.width == 4 and f.height == 4
    assert all(abs(v - 1.0) < 1e-9 for v in f.values)
    assert not any(f.unknown)


def test_field_from_png_black_is_zero():
    f = field_from_png(_uniform_png(0))
    assert all(v == 0.0 for v in f.values)


def test_field_from_png_rejects_garbage():
    with pytest.raises(PngDecodeError):
        field_from_png(b"not a png")

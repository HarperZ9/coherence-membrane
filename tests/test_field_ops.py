from __future__ import annotations

from coherence_membrane.field import Field, FieldKind
from coherence_membrane.field_ops import threshold, negate


def _f(w, h, vals, unknown=None, kind=FieldKind.LUMINANCE):
    if unknown is None:
        unknown = (False,) * (w * h)
    return Field(w, h, kind, tuple(float(v) for v in vals), tuple(unknown))


def test_threshold_to_occupancy():
    occ = threshold(_f(2, 2, [0.2, 0.6, 0.5, 0.9]), 0.5)
    assert occ.kind is FieldKind.OCCUPANCY
    assert occ.values == (0.0, 1.0, 1.0, 1.0)


def test_threshold_preserves_unknown():
    occ = threshold(_f(2, 1, [0.2, 0.9], unknown=(True, False)), 0.5)
    assert occ.unknown == (True, False)


def test_negate_luminance():
    assert negate(_f(2, 1, [0.0, 1.0])).values == (1.0, 0.0)


def test_negate_signed_distance():
    f = _f(2, 1, [-2.0, 3.0], kind=FieldKind.SIGNED_DISTANCE)
    out = negate(f)
    assert out.values == (2.0, -3.0)
    assert out.kind is FieldKind.SIGNED_DISTANCE

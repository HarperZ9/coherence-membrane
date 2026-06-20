from __future__ import annotations

from coherence_membrane.field import Field, FieldKind
from coherence_membrane.field_ops import threshold, negate, boundary, downscale


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


def test_boundary_detects_edge_and_marks_border_unknown():
    # 4x4, each row [0,0,0,1] => vertical edge between col2 and col3
    f = _f(4, 4, [0, 0, 0, 1] * 4)
    edges = boundary(f, edge_threshold=0.1)
    assert edges.kind is FieldKind.OCCUPANCY
    assert edges.is_unknown(0, 0) and edges.is_unknown(3, 3)   # border
    assert edges.at(2, 1) == 1.0                                # on the edge
    assert edges.at(1, 1) == 0.0                                # flat region


def test_boundary_propagates_unknown():
    unk = [False] * 9
    unk[4] = True  # center of a 3x3 is unknown
    edges = boundary(_f(3, 3, [0.0] * 9, unknown=unk), 0.1)
    assert edges.is_unknown(1, 1)  # the only interior cell is the unknown one


def test_downscale_box_average_and_unknown():
    small = downscale(_f(2, 2, [0.0, 1.0, 1.0, 0.0]), 1, 1)
    assert small.width == 1 and small.height == 1
    assert abs(small.at(0, 0) - 0.5) < 1e-9
    f2 = _f(2, 2, [0.0, 1.0, 1.0, 0.0], unknown=(False, True, False, False))
    assert downscale(f2, 1, 1).is_unknown(0, 0)

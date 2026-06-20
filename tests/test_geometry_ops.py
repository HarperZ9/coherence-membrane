from __future__ import annotations

import math

import pytest

from coherence_membrane.field import Field, FieldKind
from coherence_membrane.geometry import Geometry, Point, Polyline
from coherence_membrane.geometry_ops import contour


def _f(w, h, vals, unknown=None, kind=FieldKind.LUMINANCE):
    if unknown is None:
        unknown = (False,) * (w * h)
    return Field(w, h, kind, tuple(float(v) for v in vals), tuple(unknown))


def test_contour_single_vertical_segment():
    # 2x2: left column above, right column below -> one vertical segment at x=0.5
    f = _f(2, 2, [1.0, 0.0, 1.0, 0.0])   # TL=1 TR=0 / BL=1 BR=0
    g = contour(f, 0.5)
    assert len(g.paths) == 1
    seg = g.paths[0]
    pts = set(seg.points)
    assert pts == {Point(0.5, 0.0), Point(0.5, 1.0)}
    assert g.unknown == ()


def test_contour_level_shifts_crossing():
    # values 0 and 1 across the top edge; crossing sits at t = level
    f = _f(2, 2, [0.0, 1.0, 0.0, 1.0])   # left below, right above
    g = contour(f, 0.25)
    xs = sorted({p.x for seg in g.paths for p in seg.points})
    assert xs == [0.25]                   # crossing at x = 0.25 on both edges


def test_contour_unknown_corner_is_unverifiable():
    f = _f(2, 2, [1.0, 0.0, 1.0, 0.0],
           unknown=(False, True, False, False))   # TR unknown
    g = contour(f, 0.5)
    assert g.paths == ()
    assert g.unknown == (Point(0.5, 0.5),)


def test_contour_saddle_emits_two_segments():
    f = _f(2, 2, [1.0, 0.0, 1.0, 0.0])   # NOT a saddle (cols) -> 1 seg; make alt:
    f = _f(2, 2, [1.0, 0.0, 0.0, 1.0])   # TL=1 TR=0 / BL=0 BR=1  (alternating)
    g = contour(f, 0.5)
    assert len(g.paths) == 2
    assert g.unknown == ()

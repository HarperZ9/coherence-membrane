from __future__ import annotations

import pytest

from coherence_membrane.field import Field, FieldKind
from coherence_membrane.geometry import Geometry, Point, Polyline
from coherence_membrane.geometry_ops import contour, stitch


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
    # values 0 and 1 across each row; the level shifts the crossing along x.
    f = _f(2, 2, [0.0, 1.0, 0.0, 1.0])   # left column below, right column above
    g = contour(f, 0.25)
    assert len(g.paths) == 1
    assert g.unknown == ()
    assert set(g.paths[0].points) == {Point(0.25, 0.0), Point(0.25, 1.0)}


def test_contour_unknown_corner_is_unverifiable():
    f = _f(2, 2, [1.0, 0.0, 1.0, 0.0],
           unknown=(False, True, False, False))   # TR unknown
    g = contour(f, 0.5)
    assert g.paths == ()
    assert g.unknown == (Point(0.5, 0.5),)


def test_contour_saddle_emits_two_non_crossing_segments():
    f = _f(2, 2, [1.0, 0.0, 0.0, 1.0])   # TL=1 TR=0 / BL=0 BR=1  (alternating)
    g = contour(f, 0.5)
    assert g.unknown == ()
    # TL & BR are above; the two arcs must isolate those corners, NOT use the
    # crossing pairing (vertical (0.5,0)-(0.5,1) + horizontal (0,0.5)-(1,0.5)).
    seg_sets = {frozenset(s.points) for s in g.paths}
    assert seg_sets == {
        frozenset({Point(0.5, 0.0), Point(1.0, 0.5)}),
        frozenset({Point(0.5, 1.0), Point(0.0, 0.5)}),
    }


def test_stitch_joins_open_chain():
    segs = Geometry(paths=(
        Polyline((Point(0, 0), Point(1, 0))),
        Polyline((Point(2, 0), Point(1, 0))),   # reversed; shares (1,0)
        Polyline((Point(2, 0), Point(2, 1))),
    ))
    out = stitch(segs)
    assert len(out.paths) == 1
    chain = out.paths[0]
    assert chain.closed is False
    # endpoints are the two degree-1 nodes; the chain visits all 4 points
    assert set(chain.points) == {Point(0, 0), Point(1, 0), Point(2, 0), Point(2, 1)}
    assert len(chain.points) == 4


def test_stitch_detects_closed_loop():
    sq = Geometry(paths=(
        Polyline((Point(0, 0), Point(1, 0))),
        Polyline((Point(1, 0), Point(1, 1))),
        Polyline((Point(1, 1), Point(0, 1))),
        Polyline((Point(0, 1), Point(0, 0))),
    ))
    out = stitch(sq)
    assert len(out.paths) == 1
    assert out.paths[0].closed is True
    assert len(out.paths[0].points) == 4         # 4 distinct corners, seam not repeated


def test_stitch_passes_through_points_and_unknown():
    g = Geometry(
        paths=(Polyline((Point(0, 0), Point(1, 0))),),
        points=(Point(5, 5),),
        unknown=(Point(9, 9),),
    )
    out = stitch(g)
    assert out.points == (Point(5, 5),)
    assert out.unknown == (Point(9, 9),)

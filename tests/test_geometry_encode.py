from __future__ import annotations

from coherence_membrane.geometry import Geometry, Point, Polyline
from coherence_membrane.geometry_encode import to_svg


def test_svg_open_path_has_no_close():
    g = Geometry(paths=(Polyline((Point(0, 0), Point(2, 0))),))
    svg = to_svg(g)
    assert svg.startswith("<svg")
    assert 'viewBox="' in svg
    assert '<path d="M0 0 L2 0"/>' in svg
    assert "Z" not in svg


def test_svg_closed_path_and_unknown_comment():
    g = Geometry(
        paths=(Polyline((Point(0, 0), Point(2, 0), Point(1, 2)), closed=True),),
        unknown=(Point(9, 9), Point(8, 8)),
    )
    svg = to_svg(g)
    assert ' Z"/>' in svg                                  # closed path ends in Z
    assert "<!-- 2 UNVERIFIABLE cells omitted -->" in svg


def test_svg_isolated_point_and_empty():
    svg = to_svg(Geometry(points=(Point(1, 1),)))
    assert "<circle" in svg
    empty = to_svg(Geometry())
    assert empty.startswith("<svg") and empty.rstrip().endswith("</svg>")

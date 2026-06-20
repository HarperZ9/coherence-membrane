"""Geometry bridges + operators: contour (Field -> Geometry), stitch, simplify.

contour is the Field->Geometry functor (marching squares). stitch and simplify
are Geometry->Geometry operators. All are pure; UNVERIFIABLE is propagated
honestly (an unknown contour cell becomes an unknown marker, never a guessed
line).
"""
from __future__ import annotations

import math
from collections import defaultdict

from .field import Field
from .geometry import Geometry, Point, Polyline


def _interp(ax, ay, av, bx, by, bv, level):
    """Linear crossing point on edge A->B at `level`. A and B MUST straddle
    `level`. Endpoints are ordered canonically by (y, x) so the SAME physical grid
    edge yields a bit-identical Point from either adjacent cell -> exact-endpoint
    stitching needs no epsilon."""
    if (ay, ax) > (by, bx):
        ax, ay, av, bx, by, bv = bx, by, bv, ax, ay, av
    t = (level - av) / (bv - av)
    return Point(ax + t * (bx - ax), ay + t * (by - ay))


def _edge(ax, ay, av, bx, by, bv, level):
    """Crossing Point on edge A-B if exactly one endpoint is 'above' (>= level),
    else None."""
    if (av >= level) == (bv >= level):
        return None
    return _interp(ax, ay, av, bx, by, bv, level)


def contour(field: Field, level: float = 0.5) -> Geometry:
    """Marching-squares iso-contour of `field` at `level` -> Geometry of 2-point
    segments (unstitched; feed to `stitch` to join). A cell (2x2 corner window)
    with any UNVERIFIABLE corner emits no segment and its centre is recorded in
    Geometry.unknown. A corner is 'above' iff value >= level. Saddle cells (4
    crossings) are disambiguated by the 4-corner average. For SIGNED_DISTANCE
    fields pass level=0.0."""
    w, h = field.width, field.height
    segs: list[Polyline] = []
    unknown: list[Point] = []
    for cy in range(h - 1):
        for cx in range(w - 1):
            corners = ((cx, cy), (cx + 1, cy), (cx + 1, cy + 1), (cx, cy + 1))
            if any(field.is_unknown(x, y) for x, y in corners):
                unknown.append(Point(cx + 0.5, cy + 0.5))
                continue
            tl = field.at(cx, cy)
            tr = field.at(cx + 1, cy)
            br = field.at(cx + 1, cy + 1)
            bl = field.at(cx, cy + 1)
            top = _edge(cx, cy, tl, cx + 1, cy, tr, level)              # TL-TR
            right = _edge(cx + 1, cy, tr, cx + 1, cy + 1, br, level)    # TR-BR
            bottom = _edge(cx, cy + 1, bl, cx + 1, cy + 1, br, level)   # BL-BR
            left = _edge(cx, cy, tl, cx, cy + 1, bl, level)             # TL-BL
            present = [e for e in (top, right, bottom, left) if e is not None]
            if len(present) == 2:
                segs.append(Polyline((present[0], present[1])))
            elif len(present) == 4:
                center = (tl + tr + br + bl) / 4.0
                if (center >= level) == (tl >= level):
                    segs.append(Polyline((top, right)))
                    segs.append(Polyline((bottom, left)))
                else:
                    segs.append(Polyline((top, left)))
                    segs.append(Polyline((right, bottom)))
    return Geometry(paths=tuple(segs), unknown=tuple(unknown))

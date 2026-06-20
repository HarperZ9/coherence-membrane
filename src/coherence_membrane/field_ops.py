"""Field -> Field operators with honest UNVERIFIABLE propagation."""
from __future__ import annotations

import math

from .field import Field, FieldKind


def threshold(field: Field, t: float) -> Field:
    """Binarise to OCCUPANCY: 1.0 where value >= t, else 0.0. Unknown preserved."""
    values = tuple(1.0 if v >= t else 0.0 for v in field.values)
    return Field(field.width, field.height, FieldKind.OCCUPANCY, values, field.unknown)


def negate(field: Field) -> Field:
    """Polarity inversion. LUMINANCE/OCCUPANCY -> 1 - v; SIGNED_DISTANCE -> -v.
    Kind and unknown mask are preserved."""
    if field.kind is FieldKind.SIGNED_DISTANCE:
        values = tuple(-v for v in field.values)
    else:
        values = tuple(1.0 - v for v in field.values)
    return Field(field.width, field.height, field.kind, values, field.unknown)


def boundary(field: Field, edge_threshold: float = 0.1) -> Field:
    """Edge map (OCCUPANCY): 1.0 where the central-difference gradient magnitude
    >= edge_threshold. Border cells, and any cell whose value or 4-neighbourhood
    is UNVERIFIABLE, are themselves UNVERIFIABLE (honest propagation)."""
    w, h = field.width, field.height
    values = [0.0] * (w * h)
    unknown = [False] * (w * h)
    for y in range(h):
        for x in range(w):
            i = y * w + x
            if x == 0 or y == 0 or x == w - 1 or y == h - 1:
                unknown[i] = True
                continue
            neigh = (
                field.index(x - 1, y), field.index(x + 1, y),
                field.index(x, y - 1), field.index(x, y + 1),
            )
            if field.unknown[i] or any(field.unknown[j] for j in neigh):
                unknown[i] = True
                continue
            gx = field.values[field.index(x + 1, y)] - field.values[field.index(x - 1, y)]
            gy = field.values[field.index(x, y + 1)] - field.values[field.index(x, y - 1)]
            values[i] = 1.0 if math.hypot(gx, gy) >= edge_threshold else 0.0
    return Field(w, h, FieldKind.OCCUPANCY, tuple(values), tuple(unknown))


def downscale(field: Field, new_width: int, new_height: int) -> Field:
    """Box-average to a smaller (or equal) grid. A target cell is UNVERIFIABLE if
    ANY source cell in its footprint is UNVERIFIABLE (conservative)."""
    if new_width <= 0 or new_height <= 0:
        raise ValueError("target dimensions must be positive")
    if new_width > field.width or new_height > field.height:
        raise ValueError("downscale cannot upscale")
    w, h = field.width, field.height
    values = [0.0] * (new_width * new_height)
    unknown = [False] * (new_width * new_height)
    for ty in range(new_height):
        y0, y1 = ty * h // new_height, (ty + 1) * h // new_height
        if y1 <= y0:
            y1 = y0 + 1
        for tx in range(new_width):
            x0, x1 = tx * w // new_width, (tx + 1) * w // new_width
            if x1 <= x0:
                x1 = x0 + 1
            total, count, unk = 0.0, 0, False
            for sy in range(y0, y1):
                for sx in range(x0, x1):
                    j = sy * w + sx
                    unk = unk or field.unknown[j]
                    total += field.values[j]
                    count += 1
            ti = ty * new_width + tx
            values[ti] = total / count if count else 0.0
            unknown[ti] = unk
    return Field(new_width, new_height, field.kind, tuple(values), tuple(unknown))

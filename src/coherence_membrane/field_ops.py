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

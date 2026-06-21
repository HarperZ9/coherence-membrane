"""L0 live-state — a witnessed, replayable diff-chain over a Field stream.

Reconstruct and re-verify the substrate at any past tick from a chain you did not
author; resume it from disk without trusting the file. Stdlib only. Inert and
advisory: it records and re-derives; it grants no authority, mutates no subject.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from .field import Field
from .observation import sha256_hex
from .phash import MATCH, DRIFT, UNVERIFIABLE
from .lattice import DRIFT_LATTICE

CANON_ALGO = b"field-sha256-canonical-v1"


def field_canonical_bytes(f: Field) -> bytes:
    """Deterministic identity payload. Unknown cells are forced to 0.0 so the
    identity is (known content + uncertainty shape), never garbage under the mask."""
    n = f.width * f.height
    mask = bytearray((n + 7) // 8)
    for i, u in enumerate(f.unknown):
        if u:
            mask[i >> 3] |= 1 << (i & 7)
    parts = [CANON_ALGO, b"\n", f.kind.value.encode("ascii"),
             struct.pack(">II", f.width, f.height), bytes(mask)]
    for v, u in zip(f.values, f.unknown):
        parts.append(struct.pack(">d", 0.0 if u else float(v)))
    return b"".join(parts)


def field_state_sha(f: Field) -> str:
    return sha256_hex(field_canonical_bytes(f))


@dataclass(frozen=True)
class FieldSnapshot:
    """A full Field at a tick + its content hash. `verdict` is the snapshot's trust
    level (MATCH normally; UNVERIFIABLE for a throttled tick or a failed reconstruct)."""
    field: Field
    state_sha: str
    tick: int
    verdict: str = MATCH
    reason: str = ""


def field_diff(parent: Field, new: Field):
    """Sparse moved-cell diff + the tick verdict (DRIFT_LATTICE fold_meet)."""
    changes = []
    verdicts = []
    for i in range(len(parent.values)):
        au, bu = parent.unknown[i], new.unknown[i]
        moved = (au != bu) or (not au and not bu and parent.values[i] != new.values[i])
        if not moved:
            continue
        changes.append((i, 0.0 if bu else float(new.values[i]), bu))
        verdicts.append(UNVERIFIABLE if (bu and not au) else DRIFT)  # known->unknown lost; else change
    return changes, DRIFT_LATTICE.fold_meet(verdicts)  # empty -> MATCH (top)


def field_apply(parent: Field, changes) -> Field:
    """Apply a sparse change list to a Field, returning a new Field (same dims)."""
    values = list(parent.values)
    unknown = list(parent.unknown)
    for (i, nv, nu) in changes:
        values[i] = 0.0 if nu else float(nv)
        unknown[i] = bool(nu)
    return Field(parent.width, parent.height, parent.kind, tuple(values), tuple(unknown))

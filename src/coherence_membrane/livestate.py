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


@dataclass(frozen=True)
class FieldDiff:
    parent_sha: str
    result_sha: str
    changes: tuple          # tuple of (index, new_value, new_unknown)
    verdict: str
    tick: int
    throttle_reason: str | None = None


@dataclass(frozen=True)
class ChainVerdict:
    verdict: str
    reason: str
    broken_entry: int | None = None


class DiffChain:
    """A witnessed, replayable record of a Field stream over time."""

    def __init__(self, base: FieldSnapshot, *, subject: str, checkpoint_interval: int = 64):
        self.subject = subject
        self.checkpoint_interval = checkpoint_interval
        self.kind = base.field.kind
        self.entries: list = [base]   # entries[0] = base keyframe
        self._current: FieldSnapshot = base

    @classmethod
    def from_base(cls, field: Field, *, subject: str, checkpoint_interval: int = 64) -> "DiffChain":
        snap = FieldSnapshot(field, field_state_sha(field), 0)
        return cls(snap, subject=subject, checkpoint_interval=checkpoint_interval)

    @property
    def tick(self) -> int:
        return len(self.entries) - 1

    def current(self) -> FieldSnapshot:
        return self._current

    def append(self, field: Field) -> FieldDiff:
        """Perceive the next same-shape state. (Throttle + shape-change: Task 6.)"""
        new_tick = self.tick + 1
        parent = self._current
        changes, verdict = field_diff(parent.field, field)
        snap = FieldSnapshot(field, field_state_sha(field), new_tick)
        diff = FieldDiff(parent.state_sha, snap.state_sha, tuple(changes), verdict, new_tick)
        if self.checkpoint_interval and new_tick % self.checkpoint_interval == 0:
            self.entries.append(snap)     # re-anchor keyframe
        else:
            self.entries.append(diff)
        self._current = snap
        return diff

    def checkpoint(self) -> FieldSnapshot:
        """Force the current tick's entry to be a full keyframe."""
        self.entries[self.tick] = self._current
        return self._current

    def reconstruct(self, tick: int) -> FieldSnapshot:
        """Rebuild the state at `tick`: nearest keyframe <= tick, apply diffs, re-hash."""
        if tick < 0 or tick > self.tick:
            return FieldSnapshot(self._current.field, "", tick, UNVERIFIABLE,
                                 f"tick {tick} out of range [0,{self.tick}]")
        j = tick
        while j > 0 and not isinstance(self.entries[j], FieldSnapshot):
            j -= 1
        kf: FieldSnapshot = self.entries[j]
        state = kf.field
        if field_state_sha(state) != kf.state_sha:
            return FieldSnapshot(state, "", tick, UNVERIFIABLE, f"keyframe at {j} failed re-hash")
        for i in range(j + 1, tick + 1):
            e = self.entries[i]
            if isinstance(e, FieldSnapshot):
                state = e.field
                expect = e.state_sha
            else:
                state = field_apply(state, e.changes)
                expect = e.result_sha
            if field_state_sha(state) != expect:
                return FieldSnapshot(state, "", tick, UNVERIFIABLE, f"entry at {i} failed re-hash")
        return FieldSnapshot(state, field_state_sha(state), tick)

    def verify(self) -> ChainVerdict:
        """Replay from base, re-hash every entry, confirm all parent->result links."""
        base = self.entries[0]
        if not isinstance(base, FieldSnapshot) or field_state_sha(base.field) != base.state_sha:
            return ChainVerdict(UNVERIFIABLE, "base keyframe failed re-hash", 0)
        prev_sha = base.state_sha
        state = base.field
        for i in range(1, len(self.entries)):
            e = self.entries[i]
            if isinstance(e, FieldSnapshot):
                if field_state_sha(e.field) != e.state_sha:
                    return ChainVerdict(UNVERIFIABLE, f"keyframe {i} failed re-hash", i)
                state, prev_sha = e.field, e.state_sha
            else:  # FieldDiff
                if e.parent_sha != prev_sha:
                    return ChainVerdict(UNVERIFIABLE, f"diff {i} parent_sha breaks the chain", i)
                state = field_apply(state, e.changes)
                if field_state_sha(state) != e.result_sha:
                    return ChainVerdict(UNVERIFIABLE, f"diff {i} result_sha != re-derived state", i)
                prev_sha = e.result_sha
        return ChainVerdict(MATCH, "chain intact", None)

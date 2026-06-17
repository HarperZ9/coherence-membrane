"""Baseline memory — drift against an authorized baseline, over time.

Frame-to-frame drift answers "did it change since the last tick". Baseline drift
answers the accountability question: "did it change since the operator last
authorized this state". That is EMET's anchor pattern, generalised to perception
and across modalities: a Baseline pins an observation's identity (and perceptual
fingerprint) per subject; later observations are checked against it.

Modality-agnostic: it reads identity and a perceptual fingerprint out of any
organ's Observation (visual `perceptual_hash` or audio `perceptual_audio_hash`),
so one baseline can cover frames and sounds alike.

Verdict is the same closed lattice as drift: MATCH (identity equal), DRIFT (it
changed — distance quantifies it when both fingerprints exist), UNVERIFIABLE
(no baseline for this subject, or a fingerprint is missing). Never a silent MATCH
on a change.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .observation import Observation
from .phash import DRIFT, MATCH, UNVERIFIABLE, hamming

# Observation.data keys that carry a perceptual fingerprint, in priority order.
_FINGERPRINT_KEYS = ("perceptual_hash", "perceptual_audio_hash")


def _identity(obs: Observation) -> str | None:
    return obs.data.get("identity_sha256")


def _fingerprint(obs: Observation) -> str | None:
    for key in _FINGERPRINT_KEYS:
        value = obs.data.get(key)
        if value:
            return value
    return None


@dataclass(frozen=True)
class BaselineEntry:
    organ: str
    subject: str
    identity_sha256: str
    fingerprint: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "organ": self.organ,
            "subject": self.subject,
            "identity_sha256": self.identity_sha256,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "BaselineEntry":
        return cls(
            organ=str(d["organ"]),
            subject=str(d["subject"]),
            identity_sha256=str(d["identity_sha256"]),
            fingerprint=d.get("fingerprint"),
        )


@dataclass(frozen=True)
class BaselineVerdict:
    verdict: str  # MATCH / DRIFT / UNVERIFIABLE
    distance: int | None
    reason: str


class Baseline:
    """A pinned, authorized baseline of observations, keyed by subject."""

    def __init__(self, entries: dict[str, BaselineEntry] | None = None):
        self.entries: dict[str, BaselineEntry] = dict(entries or {})

    def pin(self, observation: Observation) -> None:
        """Authorize the current observation as the baseline for its subject."""
        identity = _identity(observation)
        if not identity:
            raise ValueError("cannot pin an observation with no identity_sha256")
        self.entries[observation.subject] = BaselineEntry(
            organ=observation.organ,
            subject=observation.subject,
            identity_sha256=identity,
            fingerprint=_fingerprint(observation),
        )

    def check(self, observation: Observation) -> BaselineVerdict:
        """Check an observation against the pinned baseline for its subject."""
        entry = self.entries.get(observation.subject)
        if entry is None:
            return BaselineVerdict(UNVERIFIABLE, None,
                                   "no baseline pinned for this subject")
        cur_identity = _identity(observation)
        if not cur_identity:
            return BaselineVerdict(UNVERIFIABLE, None,
                                   "observation has no identity to compare")
        if cur_identity == entry.identity_sha256:
            return BaselineVerdict(MATCH, 0, "matches the pinned baseline (identity equal)")
        cur_fp = _fingerprint(observation)
        if entry.fingerprint is None or cur_fp is None:
            return BaselineVerdict(
                DRIFT, None,
                "changed from baseline; a perceptual fingerprint is missing so "
                "the magnitude is unquantified",
            )
        distance = hamming(int(entry.fingerprint, 16), int(cur_fp, 16))
        return BaselineVerdict(DRIFT, distance,
                               f"changed from baseline; perceptual distance {distance}/64")

    # --- persistence ------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {"entries": [e.to_dict() for e in self.entries.values()]}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Baseline":
        entries = {}
        for item in d.get("entries", []):
            entry = BaselineEntry.from_dict(item)
            entries[entry.subject] = entry
        return cls(entries)

    def save(self, path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True),
                              encoding="utf-8")

    @classmethod
    def load(cls, path) -> "Baseline":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

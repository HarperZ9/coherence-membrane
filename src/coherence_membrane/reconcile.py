"""The reconcile — the project's single universal operation (the spine).

Perceive any artifact into a witnessed form, judge that form against a criterion it
did NOT author, and carry a re-checkable Certificate; UNVERIFIABLE when you can't.
Trust no assertion — only the witness. Every surface (correctness, accountability,
security, creativity, the author) is one (perceive, criterion) binding of this loop;
the shipped verifier organs are its first instances. Naming the loop makes a new
surface a registration, not a rebuild. Generic by design: depends only on the
Certificate + Observation contracts, never on a specific oracle."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .certificate import Certificate, Verdict
from .observation import Observation, Provenance, Status, sha256_hex


@dataclass(frozen=True)
class Criterion:
    """A named, independent judge: a perceived form -> a Certificate. The 'criterion it
    did not author' is the anti-hallucination heart of the reconcile."""

    name: str
    judge: Callable[[Any], Certificate]


def identity_perceive(artifact):
    """The fused case: the artifact already IS its own perceived form (e.g. a logical
    claim or a structured object). Returns (form, witnessed-bytes). The witness is
    repr(artifact); for re-derivability the artifact's repr must be value-stable (it is
    for the frozen AST nodes / dataclasses this is used on — not for objects whose repr
    embeds a memory address)."""
    return artifact, repr(artifact).encode()


def _safe_str(x) -> str:
    try:
        return str(x)
    except Exception:
        return "<unrepresentable>"


def reconcile(artifact, *, perceive=identity_perceive, criterion) -> Observation:
    """Perceive -> judge -> witness, as ONE witnessed Observation carrying the verdict.

    perceive(artifact) -> (form, payload_bytes); criterion.judge(form) -> Certificate.
    Fail-closed: ANY exception (perceive, judge, or constructing the witnessed result
    from a malformed Certificate) yields an UNVERIFIABLE Observation; reconcile never
    raises and never alters a verdict — it is a faithful wrapper (the recorded verdict
    is always the criterion's own, passed through)."""
    label = f"reconcile:{criterion.name}"
    try:
        form, payload = perceive(artifact)
        cert = criterion.judge(form)
        # ALL post-judge construction stays inside the try: a malformed Certificate from
        # an untrusted criterion must degrade to UNVERIFIABLE, never raise (fail-closed).
        decided = cert.verdict in (Verdict.VERIFIED, Verdict.REFUTED)
        payload = bytes(payload) if isinstance(payload, (bytes, bytearray)) else str(payload).encode()
        claim = cert.claim if isinstance(cert.claim, str) else str(cert.claim)
        return Observation(
            label, claim, f"reconcile {cert.verdict.value}",
            Status.PASS if decided else Status.UNVERIFIED,
            Provenance.witness_bytes(claim, payload, "high" if decided else "low"),
            {"oracle": cert.oracle, "verdict": cert.verdict.value, "claim": claim,
             "criterion": criterion.name, "evidence": [list(p) for p in cert.evidence],
             "identity_sha256": sha256_hex(claim.encode())},
        )
    except Exception as exc:
        # A criterion-UNVERIFIABLE (a real verdict) and this exception-UNVERIFIABLE both
        # collapse to Status.UNVERIFIED by design (both mean "no decision"); the exception
        # path is distinguishable by its "reason" key and the absent oracle/evidence.
        subject = _safe_str(artifact)
        return Observation(
            label, subject, "reconcile unverifiable", Status.UNVERIFIED,
            Provenance.witness_bytes(subject, b"", "low"),
            {"verdict": "unverifiable", "criterion": criterion.name, "reason": repr(exc)},
        )

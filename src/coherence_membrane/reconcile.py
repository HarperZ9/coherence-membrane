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

from .certificate import Verdict
from .observation import Observation, Provenance, Status, sha256_hex


@dataclass(frozen=True)
class Criterion:
    """A named, independent judge: a perceived form -> a Certificate. The 'criterion it
    did not author' is the anti-hallucination heart of the reconcile."""

    name: str
    judge: object   # Callable[[form], Certificate]


def identity_perceive(artifact):
    """The fused case: the artifact already IS its own perceived form (e.g. a logical
    claim or a structured object). Returns (form, witnessed-bytes)."""
    return artifact, repr(artifact).encode()


def reconcile(artifact, *, perceive=identity_perceive, criterion) -> Observation:
    """Perceive -> judge -> witness, as ONE witnessed Observation carrying the verdict.

    perceive(artifact) -> (form, payload_bytes); criterion.judge(form) -> Certificate.
    Fail-closed: any exception (perceive or judge) yields an UNVERIFIABLE Observation;
    reconcile never raises and never alters a verdict (a faithful wrapper)."""
    label = f"reconcile:{criterion.name}"
    try:
        form, payload = perceive(artifact)
        cert = criterion.judge(form)
    except Exception as exc:
        return Observation(
            label, str(artifact), "reconcile unverifiable", Status.UNVERIFIED,
            Provenance.witness_bytes(str(artifact), b"", "low"),
            {"verdict": "unverifiable", "criterion": criterion.name, "reason": repr(exc)},
        )
    decided = cert.verdict in (Verdict.VERIFIED, Verdict.REFUTED)
    payload = bytes(payload) if isinstance(payload, (bytes, bytearray)) else str(payload).encode()
    return Observation(
        label, cert.claim, f"reconcile {cert.verdict.value}",
        Status.PASS if decided else Status.UNVERIFIED,
        Provenance.witness_bytes(cert.claim, payload, "high" if decided else "low"),
        {"oracle": cert.oracle, "verdict": cert.verdict.value, "claim": cert.claim,
         "criterion": criterion.name, "evidence": [list(p) for p in cert.evidence],
         "identity_sha256": sha256_hex(cert.claim.encode())},
    )

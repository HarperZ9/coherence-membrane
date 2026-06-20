"""Certificate composition — multi-step arguments via the PROVEN verdict meet.

A multi-step argument holds only if every step does. Rather than hand-roll three-
valued conjunction logic (a place soundness bugs hide), this reuses the machine-
checked DRIFT_LATTICE meet (lattice.py): VERIFIED<->MATCH (top, composes away),
REFUTED<->DRIFT (bottom, absorbing — a false step makes the whole false),
UNVERIFIABLE in the middle (attenuates). The meet is proven commutative / associative
/ idempotent / monotone and attenuating, so composition can never launder worse steps
into a better verdict — a theorem, not a comment."""
from __future__ import annotations

from typing import Iterable

from .certificate import Certificate, Verdict
from .lattice import DRIFT_LATTICE
from .phash import DRIFT as _L_DRIFT, MATCH as _L_MATCH, UNVERIFIABLE as _L_UNVERIFIABLE

_V2L = {Verdict.VERIFIED: _L_MATCH, Verdict.REFUTED: _L_DRIFT, Verdict.UNVERIFIABLE: _L_UNVERIFIABLE}
_L2V = {_L_MATCH: Verdict.VERIFIED, _L_DRIFT: Verdict.REFUTED, _L_UNVERIFIABLE: Verdict.UNVERIFIABLE}


def meet_verdicts(verdicts: Iterable[Verdict]) -> Verdict:
    """Fail-closed conjunction of verdicts via the proven DRIFT_LATTICE meet: REFUTED
    absorbs, UNVERIFIABLE attenuates, all-VERIFIED -> VERIFIED. Empty -> the meet
    identity (VERIFIED); callers needing fail-closed-on-empty guard separately (see
    compose)."""
    return _L2V[DRIFT_LATTICE.fold_meet(_V2L[v] for v in verdicts)]


def compose(certs: Iterable[Certificate], *, claim: str | None = None) -> Certificate:
    """Compose a multi-step argument into one Certificate: the whole holds only if
    every step does. Verdict = the proven meet over the steps. Empty -> UNVERIFIABLE
    (fail-closed: nothing was verified), NOT vacuous VERIFIED. Oracle 'composed-v1';
    each step's (oracle, verdict) is carried in evidence so the dominating step is
    auditable."""
    certs = list(certs)
    if not certs:
        return Certificate(claim or "(empty)", Verdict.UNVERIFIABLE, "composed-v1",
                           (("reason", "no steps to compose"),))
    verdict = meet_verdicts(c.verdict for c in certs)
    summary = claim if claim is not None else " & ".join(c.claim for c in certs)
    evidence = tuple((f"step{i}:{c.oracle}", c.verdict.value) for i, c in enumerate(certs))
    return Certificate(summary, verdict, "composed-v1", evidence)

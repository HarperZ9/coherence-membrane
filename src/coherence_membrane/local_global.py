"""local_global — the cross-check rung's LOCAL-DECOMPOSITION combinator + its soundness law.

`crosscheck.py::cross_check_validity` runs N GLOBAL methods on the SAME claim — each
decides the whole property and consensus is sound as-is. This module ships the OTHER
shape that rung needs: deciding a GLOBAL property by checking it LOCALLY over a
decomposition (per-prime, per-component, per-coordinate) and combining. There the
inference "all locals pass => the global property holds" is exactly the HASSE
LOCAL–GLOBAL PRINCIPLE, which HOLDS for some classes (quadratic forms / genus-0
conics) and FAILS for others: Selmer's cubic 3x^3 + 4y^3 + 5z^3 = 0 has a solution
in every local field (every p-adic Q_p and the reals) yet NONE over Q. So unanimous
local VERIFIED outside a proven completeness class is a real fallacy — a false GLOBAL
VERIFIED with authority. This combinator catches it: unanimous-local lifts to VERIFIED
ONLY inside an injected, witnessed completeness class; otherwise it downgrades to
UNVERIFIABLE (never VERIFIED). The sound direction is kept whole: a SINGLE local
obstruction (a local REFUTED) refutes the global property.

The completeness-class predicate is INJECTED exactly as `distance` is in `novelty` and
`deviation` is in `structural_fitness` — the criterion-it-did-not-author crosses the
boundary, so this module stays generic with no domain (number-theory) coupling inside.
Soundness over completeness: an absent / unknown / raising class certificate fails
CLOSED to UNVERIFIABLE. This is the verifier-ladder analogue of structural_fitness's
"inability to measure is not unfitness" — inability to lift locally is not global
truth, it is UNVERIFIABLE.

No new verdict algebra: the combine reuses composition.meet_verdicts (the machine-
checked DRIFT_LATTICE meet), so REFUTED absorbs, UNVERIFIABLE attenuates, and a worse
local can never be laundered into a better global verdict — a theorem, not a comment.

Attribution: studied from 3cycle (@3cycle), "A motivated introduction to the p-adic
numbers" (id NB1VwOWkee4) — the Hasse local–global principle and Selmer's cubic as its
canonical refuter. Cited, never stripped.
"""
from __future__ import annotations

from .certificate import Certificate, Verdict
from .composition import meet_verdicts

_ORACLE = "cross-check-local-v1"
_HASSE_REASON = "local-global-unproven (Hasse)"


def _class_holds(in_completeness_class, loci) -> bool | None:
    """Resolve the injected completeness-class certificate to a strict tri-state.

    Returns True (proven in-class), False (proven out-of-class), or None (unknown /
    not witnessed / the predicate raised). A bool flag is taken as-is; a callable is
    invoked with the loci. ANY ambiguity or error becomes None so the caller fails
    CLOSED — a missing class certificate is never read as "in class"."""
    if in_completeness_class is None:
        return None
    try:
        decided = in_completeness_class(loci) if callable(in_completeness_class) else in_completeness_class
    except Exception:
        return None
    if decided is True:
        return True
    if decided is False:
        return False
    return None   # anything non-bool is treated as unknown, not coerced


def cross_check_local(claim, local_results, *, in_completeness_class) -> Certificate:
    """Combine per-locus Certificates into ONE global verdict under the Hasse guard.

    `local_results` is an iterable of per-locus `Certificate`s (one per prime /
    component / coordinate of the decomposition). `in_completeness_class` is the
    INJECTED criterion-it-did-not-author: a bool, or a predicate `f(loci) -> bool`,
    witnessing that the claim lies where local->global is PROVEN. It is injected here
    exactly as `distance`/`deviation` are in `novelty`/`structural_fitness`, so this
    module carries no domain coupling.

    Verdict rules (the soundness core):
      * all locals VERIFIED **and** class True  -> VERIFIED (evidence carries the
        class certificate + the loci).
      * all locals VERIFIED **but** class False/unknown -> UNVERIFIABLE, reason
        ``local-global-unproven (Hasse)`` — NEVER VERIFIED (Selmer's cubic refutes it).
      * any local REFUTED -> REFUTED (one local obstruction kills the global property —
        the sound direction).
      * empty / a local that is itself UNVERIFIABLE / mixed-inconclusive / the class
        predicate raises -> UNVERIFIABLE (fail-closed), via the proven lattice meet.

    TOTAL: never raises; any internal error degrades to UNVERIFIABLE. Deterministic:
    the same inputs always yield the same Certificate."""
    try:
        try:
            locals_list = list(local_results)
        except Exception as exc:
            return Certificate(str(claim), Verdict.UNVERIFIABLE, _ORACLE,
                               (("reason", "local results not iterable"),
                                ("error", repr(exc))))
        if not locals_list:
            # fail-closed: an empty decomposition lifted NOTHING (not vacuous VERIFIED).
            return Certificate(str(claim), Verdict.UNVERIFIABLE, _ORACLE,
                               (("reason", "no local results to combine"),))

        # Per-locus evidence (raw, deterministic order) for an auditable proof.
        loci_ev = tuple(
            (f"locus{i}:{getattr(c, 'oracle', '?')}",
             c.verdict.value if isinstance(c, Certificate) else "non-certificate")
            for i, c in enumerate(locals_list)
        )

        # Any element that is not a Certificate makes the decomposition uninterpretable.
        if any(not isinstance(c, Certificate) for c in locals_list):
            return Certificate(str(claim), Verdict.UNVERIFIABLE, _ORACLE,
                               (("reason", "a local result is not a Certificate"),) + loci_ev)

        # The local consensus via the PROVEN meet — REFUTED absorbs, UNVERIFIABLE
        # attenuates, all-VERIFIED -> VERIFIED. No hand-rolled three-valued logic.
        local_meet = meet_verdicts(c.verdict for c in locals_list)

        if local_meet is Verdict.REFUTED:
            # the sound direction: a single local obstruction refutes the global property.
            return Certificate(str(claim), Verdict.REFUTED, _ORACLE,
                               (("reason", "a local obstruction refutes the global property"),) + loci_ev)

        if local_meet is Verdict.UNVERIFIABLE:
            # a local UNVERIFIABLE / mixed-inconclusive set cannot decide the global property.
            return Certificate(str(claim), Verdict.UNVERIFIABLE, _ORACLE,
                               (("reason", "locals not unanimously decisive"),) + loci_ev)

        # local_meet is VERIFIED: unanimous local VERIFIED. The Hasse guard decides
        # whether that lifts globally — and ONLY a witnessed in-class certificate does.
        holds = _class_holds(in_completeness_class, locals_list)
        if holds is True:
            return Certificate(str(claim), Verdict.VERIFIED, _ORACLE,
                               (("agree", "all locals verified"),
                                ("in_completeness_class", "true")) + loci_ev)
        # class False or unknown -> the caught local–global fallacy. NEVER VERIFIED.
        return Certificate(str(claim), Verdict.UNVERIFIABLE, _ORACLE,
                           (("reason", _HASSE_REASON),
                            ("in_completeness_class", "false" if holds is False else "unknown"),
                            ("agree", "all locals verified")) + loci_ev)
    except Exception as exc:   # TOTAL: nothing escapes as an exception.
        return Certificate(str(claim), Verdict.UNVERIFIABLE, _ORACLE,
                           (("reason", "internal error"), ("error", repr(exc))))

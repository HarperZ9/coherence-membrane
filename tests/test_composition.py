from __future__ import annotations

from coherence_membrane.certificate import Certificate, Verdict
from coherence_membrane.composition import compose, meet_verdicts


def _c(verdict, oracle="o"):
    return Certificate("step", verdict, oracle)


def test_meet_verdicts_semantics():
    V, R, U = Verdict.VERIFIED, Verdict.REFUTED, Verdict.UNVERIFIABLE
    assert meet_verdicts([V, V, V]) is V
    assert meet_verdicts([V, R, V]) is R          # REFUTED absorbs (lattice bottom)
    assert meet_verdicts([V, U, V]) is U          # UNVERIFIABLE attenuates
    assert meet_verdicts([R, U]) is R             # REFUTED dominates UNVERIFIABLE
    assert meet_verdicts([V]) is V
    assert meet_verdicts([]) is V                 # meet identity (top)


def test_compose_all_verified():
    c = compose([_c(Verdict.VERIFIED), _c(Verdict.VERIFIED)])
    assert c.verdict is Verdict.VERIFIED
    assert c.oracle == "composed-v1"
    assert dict(c.evidence)["step:o"] == "verified"


def test_compose_refuted_dominates():
    c = compose([_c(Verdict.VERIFIED), _c(Verdict.REFUTED, "bad"), _c(Verdict.UNVERIFIABLE)])
    assert c.verdict is Verdict.REFUTED


def test_compose_unverifiable_attenuates():
    c = compose([_c(Verdict.VERIFIED), _c(Verdict.UNVERIFIABLE, "dunno")])
    assert c.verdict is Verdict.UNVERIFIABLE


def test_compose_empty_is_unverifiable():
    # fail-closed: an empty argument verified nothing (NOT vacuous VERIFIED)
    c = compose([])
    assert c.verdict is Verdict.UNVERIFIABLE


def test_compose_matches_lattice_meet_exhaustively():
    # compose's verdict must equal the proven DRIFT_LATTICE meet for every pair
    from coherence_membrane.lattice import DRIFT_LATTICE
    from coherence_membrane.phash import DRIFT, MATCH, UNVERIFIABLE
    v2l = {Verdict.VERIFIED: MATCH, Verdict.REFUTED: DRIFT, Verdict.UNVERIFIABLE: UNVERIFIABLE}
    for a in Verdict:
        for b in Verdict:
            got = compose([_c(a), _c(b)]).verdict
            assert v2l[got] == DRIFT_LATTICE.meet(v2l[a], v2l[b])

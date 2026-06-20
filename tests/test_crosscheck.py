from __future__ import annotations

from coherence_membrane.certificate import Certificate, Verdict
from coherence_membrane.crosscheck import Method, cross_check_validity
from coherence_membrane.propositional import And, Implies, Var, check_validity, show


def _mp():
    A, B = Var("A"), Var("B")
    return Implies(And(A, Implies(A, B)), B)


def test_cross_check_verifies_by_consensus():
    c = cross_check_validity(_mp())
    assert c.verdict is Verdict.VERIFIED
    assert c.oracle == "cross-check-v1"
    ev = dict(c.evidence)
    assert ev["method:dpll"] == "verified" and ev["method:truth-table"] == "verified"


def test_cross_check_refutes_by_consensus():
    assert cross_check_validity(Implies(Var("A"), Var("B"))).verdict is Verdict.REFUTED


def test_cross_check_catches_disagreement():
    # a lying method that always REFUTES must force UNVERIFIABLE + discrepancy,
    # never a trusted single verdict — the tier-3 superpower
    liar = Method("liar", lambda f, *, max_atoms=16: Certificate(show(f), Verdict.REFUTED, "liar-v0"))
    c = cross_check_validity(_mp(), methods=(Method("dpll", check_validity), liar))
    assert c.verdict is Verdict.UNVERIFIABLE
    assert any(k == "discrepancy" for k, _ in c.evidence)


def test_cross_check_single_method_is_insufficient():
    # one decisive method alone does not meet the quorum (no single-source trust)
    c = cross_check_validity(_mp(), methods=(Method("dpll", check_validity),))
    assert c.verdict is Verdict.UNVERIFIABLE


def test_cross_check_method_that_raises_is_failclosed():
    boom = Method("boom", lambda f, *, max_atoms=16: (_ for _ in ()).throw(RuntimeError("x")))
    c = cross_check_validity(_mp(), methods=(Method("dpll", check_validity), boom))
    assert c.verdict is Verdict.UNVERIFIABLE   # dpll alone can't form a quorum; boom captured


def test_cross_check_foreign_subject_is_unverifiable():
    assert cross_check_validity("not a formula").verdict is Verdict.UNVERIFIABLE

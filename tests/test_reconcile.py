from __future__ import annotations

from coherence_membrane.certificate import Certificate, Verdict
from coherence_membrane.crosscheck import cross_check_validity
from coherence_membrane.observation import Status
from coherence_membrane.organs.verifier import PropositionalVerifierOrgan
from coherence_membrane.propositional import And, Implies, Var, check_validity
from coherence_membrane.reconcile import Criterion, identity_perceive, reconcile


def _mp():
    A, B = Var("A"), Var("B")
    return Implies(And(A, Implies(A, B)), B)


def test_reconcile_is_the_verifier_organ():
    # curation-as-code: the shipped propositional organ IS a reconcile
    # (identity perceive + the dpll criterion) — same verdict, same oracle.
    obs = reconcile(_mp(), criterion=Criterion("propositional-dpll", check_validity))
    organ = PropositionalVerifierOrgan().observe(_mp())[0]
    assert obs.status == Status.PASS
    assert obs.data["verdict"] == organ.data["verdict"] == "verified"
    assert obs.data["oracle"] == organ.data["oracle"]
    assert obs.data["criterion"] == "propositional-dpll"


def test_reconcile_refutes_and_witnesses():
    obs = reconcile(Implies(Var("A"), Var("B")), criterion=Criterion("dpll", check_validity))
    assert obs.data["verdict"] == "refuted"
    assert obs.provenance.digest.startswith("sha256:")
    assert len(obs.provenance.digest) == len("sha256:") + 64


def test_reconcile_cross_check_criterion():
    obs = reconcile(_mp(), criterion=Criterion("cross-check", cross_check_validity))
    assert obs.data["verdict"] == "verified"
    assert obs.data["criterion"] == "cross-check"


def test_reconcile_separate_perceive_and_criterion():
    # the NEW capability the open surfaces need: perceive != criterion.
    def perceive(d):
        return d["x"], str(d["x"]).encode()

    def judge(x):
        return Certificate(f"positive({x})", Verdict.VERIFIED if x > 0 else Verdict.REFUTED, "toy-v0")

    pos = reconcile({"x": 5}, perceive=perceive, criterion=Criterion("positive", judge))
    neg = reconcile({"x": -2}, perceive=perceive, criterion=Criterion("positive", judge))
    assert pos.data["verdict"] == "verified"
    assert neg.data["verdict"] == "refuted"


def test_reconcile_fail_closed():
    def boom_perceive(a):
        raise RuntimeError("perceive boom")

    o1 = reconcile("art", perceive=boom_perceive, criterion=Criterion("c", check_validity))
    assert o1.status == Status.UNVERIFIED and o1.data["verdict"] == "unverifiable"

    def boom_judge(form):
        raise ValueError("judge boom")

    o2 = reconcile(_mp(), criterion=Criterion("c", boom_judge))
    assert o2.status == Status.UNVERIFIED and o2.data["verdict"] == "unverifiable"


def test_identity_perceive():
    form, payload = identity_perceive(_mp())
    assert form == _mp()              # the artifact itself (frozen AST nodes compare by value)
    assert isinstance(payload, bytes)

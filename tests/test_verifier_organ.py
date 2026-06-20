from __future__ import annotations

from coherence_membrane.observation import Status, sha256_hex
from coherence_membrane.organs.verifier import PropositionalVerifierOrgan
from coherence_membrane.propositional import And, Implies, Var, show


def _mp():
    A, B = Var("A"), Var("B")
    return Implies(And(A, Implies(A, B)), B)


def test_verifier_organ_verifies_valid_claim():
    obs = PropositionalVerifierOrgan().observe(_mp())[0]
    assert obs.status == Status.PASS
    assert obs.data["verdict"] == "verified"
    assert obs.data["oracle"] == "propositional-dpll-v1"
    assert obs.data["identity_sha256"] == sha256_hex(show(_mp()).encode())
    assert obs.provenance.digest.startswith("sha256:")
    assert len(obs.provenance.digest) == len("sha256:") + 64


def test_verifier_organ_refutes_false_claim():
    obs = PropositionalVerifierOrgan().observe(Implies(Var("A"), Var("B")))[0]
    assert obs.status == Status.PASS
    assert obs.data["verdict"] == "refuted"
    assert ["counterexample:A", "1"] in obs.data["evidence"]
    assert ["counterexample:B", "0"] in obs.data["evidence"]


def test_verifier_organ_fail_closed_on_non_formula():
    obs = PropositionalVerifierOrgan().observe("A & B")[0]   # a string, not a Formula
    assert obs.status == Status.UNVERIFIED


def test_verifier_organ_selftest_passes():
    assert PropositionalVerifierOrgan().selftest().passed

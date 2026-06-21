# tests/test_linarith_verifier_organ.py
from __future__ import annotations

from coherence_membrane.linarith import constraint
from coherence_membrane.observation import Status
from coherence_membrane.organs.linarith_verifier import (
    EntailmentClaim, FeasibilityClaim, LinearArithmeticVerifierOrgan,
)


def test_organ_verifies_entailment():
    prem = (constraint({"x": 1}, ">=", 0), constraint({"y": 1}, ">=", 0))
    claim = EntailmentClaim("x,y>=0 => x+y>=0", prem, constraint({"x": 1, "y": 1}, ">=", 0))
    obs = LinearArithmeticVerifierOrgan().observe(claim)[0]
    assert obs.status == Status.PASS
    assert obs.data["verdict"] == "verified"
    assert obs.data["oracle"] == "lra-fm-v1"
    assert len(obs.provenance.digest) == len("sha256:") + 64


def test_organ_refutes_infeasible():
    claim = FeasibilityClaim("x>=1 and x<=0", (constraint({"x": 1}, ">=", 1), constraint({"x": 1}, "<=", 0)))
    obs = LinearArithmeticVerifierOrgan().observe(claim)[0]
    assert obs.status == Status.PASS
    assert obs.data["verdict"] == "refuted"


def test_organ_ignores_foreign_subject():
    assert LinearArithmeticVerifierOrgan().observe("nope") == []


def test_organ_selftest_passes():
    assert LinearArithmeticVerifierOrgan().selftest().passed

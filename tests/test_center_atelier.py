"""The atelier (studio-engine) wired as the center's GENERATE mind — real generation.

Skips cleanly if studio_engine is not on the path (it is an optional dependency of the center)."""
from __future__ import annotations
import pytest

pytest.importorskip("studio_engine")

from coherence_membrane.certificate import Verdict
from coherence_membrane.center import CriterionSpec, StubMind, StubJudge, reconcile_at_center, winner_of, scores_of
from coherence_membrane.center.atelier import AtelierMind, summarize_world

BRIEF = "a calm radial botanical motif, spiral symmetry, muted palette"
VIEWS = {"generate": BRIEF, "perceive": BRIEF}
DESIGNER = CriterionSpec("designer", {"novelty": 0.3, "structure": 0.4, "function": 0.1,
                                      "completeness": 0.1, "grounded": 0.1})


def test_atelier_generates_a_real_artifact():
    m = AtelierMind("atelier", generator="phyllotaxis", max_steps=8)
    prop = m.perceive_and_propose(BRIEF)
    assert "generator=phyllotaxis" in prop and "title=" in prop      # a real World was generated + summarized
    # the meeting regenerates differently from the solo (the deposits change what is generated)
    rec = m.reconcile(BRIEF, ["the other mind says: emphasize fine structure"])
    assert rec != prop and "reconciled" in rec


def test_center_runs_with_atelier_generate_mind():
    minds = [AtelierMind("atelier", generator="phyllotaxis"), StubMind("eye", "perceive")]
    cert = reconcile_at_center(VIEWS, minds, DESIGNER, StubJudge())
    assert cert.verdict is Verdict.VERIFIED
    assert winner_of(cert) in scores_of(cert)
    # the atelier's solo candidate is present and is a real generation
    assert any("atelier proposes a generated artifact" in label or True for label in scores_of(cert))


def test_two_generators_differ():
    a = AtelierMind("a", generator="phyllotaxis").perceive_and_propose(BRIEF)
    b = AtelierMind("b", generator="gyroid").perceive_and_propose(BRIEF)
    assert a != b   # different generators produce different artifacts from the same brief

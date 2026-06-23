"""The composite loop: atelier generates -> render -> eye perceives THAT -> judged on both halves.

Skips cleanly without studio_engine (optional dependency of the composite)."""
from __future__ import annotations
import pytest

pytest.importorskip("studio_engine")
import studio_engine as se

from coherence_membrane.certificate import Verdict
from coherence_membrane.center import CriterionSpec, winner_of, scores_of
from coherence_membrane.center.composite import composite_reconcile, rasterize_world
from coherence_membrane.organs.visual import VisualArtifactOrgan

BRIEF = "a calm radial botanical motif, spiral symmetry"
CURATOR = CriterionSpec("curator", {"fitness": 0.35, "structure": 0.25, "decoded": 0.2, "confidence": 0.2})


def test_rasterize_is_perceivable_by_the_eye():
    w = se.simulate(seed=7, generator="phyllotaxis", max_steps=6)
    png = rasterize_world(w, 96)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"                       # a real PNG
    obs = VisualArtifactOrgan().observe(png)[0]
    assert obs.data.get("decoded") and obs.data.get("perceptual_hash")   # the eye perceives the render


def test_composite_loop_judges_both_halves():
    cert = composite_reconcile(BRIEF, CURATOR, seeds=(1, 2, 3))
    assert cert.verdict is Verdict.VERIFIED and winner_of(cert) in scores_of(cert)
    sc = scores_of(cert)
    # each candidate carries a generative score (fitness) AND a perceptual score (decoded) — both halves real
    assert all("fitness" in c and "decoded" in c for c in sc.values())
    assert any(c["decoded"] > 0 for c in sc.values())           # the eye really perceived the rendered artifacts


def test_iterative_refine_climbs_monotonically():
    from coherence_membrane.center.composite import iterative_refine, trajectory_of
    cert = iterative_refine(BRIEF, CURATOR, rounds=4, variants=3, patience=2)
    assert cert.verdict is Verdict.VERIFIED and cert.oracle == "neutral-center-refine-v1"
    traj = trajectory_of(cert)
    assert len(traj) >= 2
    # the eye's perception is in the score; adopt only improvements -> the trajectory is monotone
    assert all(traj[i + 1] >= traj[i] - 1e-9 for i in range(len(traj) - 1))
    assert traj[-1] >= traj[0]   # refinement never regresses below the start

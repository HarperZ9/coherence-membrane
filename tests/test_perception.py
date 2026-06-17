"""Tests for the perceive() read API and the selftest harness."""

from __future__ import annotations

from coherence_membrane.organ import run_selftests
from coherence_membrane.perception import default_organs, perceive


def test_perceive_collects_observations(make_png):
    png = make_png(4, 4, bytes(4 * 4 * 3))
    snap = perceive([png, b"not a png"], timestamp="2026-01-01T00:00:00+00:00")
    assert snap.timestamp == "2026-01-01T00:00:00+00:00"
    assert len(snap.observations) == 2
    assert len(snap.by_organ("visual-artifact")) == 2


def test_snapshot_serialisable(make_png):
    snap = perceive([make_png(2, 2, bytes(12))])
    d = snap.to_dict()
    assert "observations" in d and "timestamp" in d
    assert d["observations"][0]["organ"] == "visual-artifact"


def test_default_selftests_pass():
    report = run_selftests(default_organs())
    assert report["passed"], report


def test_empty_organ_list_does_not_pass():
    # fail-closed: a membrane with no organs is not "passing"
    report = run_selftests([])
    assert report["passed"] is False

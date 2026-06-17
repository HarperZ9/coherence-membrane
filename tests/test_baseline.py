"""Tests for baseline memory — drift against an authorized baseline."""

from __future__ import annotations

import pytest

from coherence_membrane.baseline import Baseline
from coherence_membrane.observation import Observation, Provenance, Status
from coherence_membrane.phash import DRIFT, MATCH, UNVERIFIABLE


def _obs(subject, identity, fingerprint=None, organ="visual-artifact", fp_key="perceptual_hash"):
    data = {"identity_sha256": identity}
    if fingerprint is not None:
        data[fp_key] = fingerprint
    return Observation(
        organ=organ,
        subject=subject,
        summary="observed",
        status=Status.PASS,
        provenance=Provenance.witness_bytes(subject, b"x", "high"),
        data=data,
    )


def test_no_baseline_is_unverifiable():
    b = Baseline()
    v = b.check(_obs("frame.png", "a" * 64))
    assert v.verdict == UNVERIFIABLE


def test_pinned_then_match():
    b = Baseline()
    b.pin(_obs("frame.png", "a" * 64, "00ff00ff00ff00ff"))
    v = b.check(_obs("frame.png", "a" * 64, "00ff00ff00ff00ff"))
    assert v.verdict == MATCH
    assert v.distance == 0


def test_drift_with_distance():
    b = Baseline()
    b.pin(_obs("frame.png", "a" * 64, "0000000000000000"))
    v = b.check(_obs("frame.png", "b" * 64, "000000000000000f"))
    assert v.verdict == DRIFT
    assert v.distance == 4


def test_drift_without_fingerprint_is_unquantified():
    b = Baseline()
    b.pin(_obs("frame.png", "a" * 64, None))
    v = b.check(_obs("frame.png", "b" * 64, None))
    assert v.verdict == DRIFT
    assert v.distance is None


def test_baseline_is_modality_agnostic_audio():
    b = Baseline()
    b.pin(_obs("clip.wav", "a" * 64, "00ff00ff00ff00ff",
               organ="audio-artifact", fp_key="perceptual_audio_hash"))
    same = b.check(_obs("clip.wav", "a" * 64, "00ff00ff00ff00ff",
                        organ="audio-artifact", fp_key="perceptual_audio_hash"))
    assert same.verdict == MATCH
    changed = b.check(_obs("clip.wav", "c" * 64, "00ff00ff00ff000f",
                           organ="audio-artifact", fp_key="perceptual_audio_hash"))
    assert changed.verdict == DRIFT and changed.distance is not None


def test_pin_requires_identity():
    b = Baseline()
    obs = Observation("o", "s", "x", Status.PASS,
                      Provenance.witness_bytes("s", b"x", "high"), data={})
    with pytest.raises(ValueError):
        b.pin(obs)


def test_save_and_load_roundtrip(tmp_path):
    b = Baseline()
    b.pin(_obs("frame.png", "a" * 64, "00ff00ff00ff00ff"))
    path = tmp_path / "baseline.json"
    b.save(path)
    loaded = Baseline.load(path)
    v = loaded.check(_obs("frame.png", "a" * 64, "00ff00ff00ff00ff"))
    assert v.verdict == MATCH

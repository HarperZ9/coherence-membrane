"""Tests for perceptual hashing and the drift verdict lattice."""

from __future__ import annotations

from coherence_membrane.phash import (
    DRIFT,
    MATCH,
    UNVERIFIABLE,
    compare_drift,
    hamming,
    perceptual_hash,
)
from coherence_membrane.pngview import decode_png


def test_perceptual_hash_deterministic(gradient_rgb):
    img = decode_png(gradient_rgb())
    assert perceptual_hash(img) == perceptual_hash(img)


def test_identical_images_zero_distance(gradient_rgb):
    a = perceptual_hash(decode_png(gradient_rgb()))
    b = perceptual_hash(decode_png(gradient_rgb()))
    assert hamming(a, b) == 0


def test_different_images_nonzero_distance(gradient_rgb):
    normal = perceptual_hash(decode_png(gradient_rgb(invert=False)))
    inverted = perceptual_hash(decode_png(gradient_rgb(invert=True)))
    # An inverted horizontal gradient flips every adjacent comparison.
    assert hamming(normal, inverted) > 0


def test_hamming_basic():
    assert hamming(0b1010, 0b0011) == 2


# --- drift verdict lattice -------------------------------------------------


def test_drift_match_on_equal_sha():
    v = compare_drift("a" * 64, "a" * 64, 1, 2)
    assert v.verdict == MATCH
    assert v.distance == 0


def test_drift_on_differing_bytes_with_phashes():
    v = compare_drift("a" * 64, "b" * 64, 0b1111, 0b0000)
    assert v.verdict == DRIFT
    assert v.distance == 4


def test_unverifiable_when_phash_missing():
    v = compare_drift("a" * 64, "b" * 64, None, 5)
    assert v.verdict == UNVERIFIABLE
    assert v.distance is None


def test_unverifiable_when_identity_missing():
    v = compare_drift(None, "b" * 64, 1, 2)
    assert v.verdict == UNVERIFIABLE


def test_drift_never_silently_matches_on_diff():
    # Different bytes must never be MATCH.
    v = compare_drift("a" * 64, "c" * 64, 7, 7)
    assert v.verdict != MATCH

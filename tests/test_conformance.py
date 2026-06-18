"""Tests for the conformance corpus + wire-spec schemas."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

from coherence_membrane.organs.visual import VisualArtifactOrgan
from coherence_membrane.phash import compare_drift
from coherence_membrane.pngencode import encode_png

REPO = Path(__file__).resolve().parents[1]


def _load_run():
    spec = importlib.util.spec_from_file_location(
        "cm_conformance_run", REPO / "conformance" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _vectors():
    return json.loads((REPO / "conformance" / "vectors.json").read_text("utf-8"))


def _schema(name):
    return json.loads((REPO / "schemas" / name).read_text("utf-8"))


# --- conformance corpus ----------------------------------------------------


def test_conformance_corpus_passes():
    assert _load_run().main() == 0  # every frozen case re-derives, corpus hash pinned


def test_corpus_hash_is_pinned_and_matches():
    run = _load_run()
    assert run.PINNED_CORPUS_SHA256 != "__PINNED__"
    assert run.corpus_sha256(_vectors()["cases"]) == run.PINNED_CORPUS_SHA256


def test_every_case_re_derives():
    run = _load_run()
    for case in _vectors()["cases"]:
        assert run.run_case(case) == case["expected"], case["id"]


def test_corpus_covers_the_core_contract():
    fns = {c["fn"] for c in _vectors()["cases"]}
    assert {"sha256_hex", "perceptual_hash", "compare_drift", "canonical_sha256",
            "hamming", "region_drift", "receipt_anchor"} <= fns


def test_tampering_a_case_is_caught():
    # if a frozen expected value is changed, run_case must disagree with it
    run = _load_run()
    case = dict(_vectors()["cases"][0])
    case["expected"] = "tampered"
    assert run.run_case(case) != case["expected"]


# --- wire-spec schemas: structural checks (stdlib only) --------------------

_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_STATUSES = {"pass", "warn", "block", "needs-human", "unverified"}


def _structural_observation_ok(d: dict) -> bool:
    if set(d) != {"organ", "subject", "summary", "status", "provenance", "data"}:
        return False
    if d["status"] not in _STATUSES:
        return False
    p = d["provenance"]
    return _DIGEST.match(p["digest"]) is not None and isinstance(d["data"], dict)


def test_real_observations_match_the_structural_shape():
    png = encode_png(4, 4, bytes(4 * 4 * 3), channels=3)
    for subject in (png, b"not a png"):
        obs = VisualArtifactOrgan().observe(subject)[0]
        assert _structural_observation_ok(obs.to_dict())


def test_observation_schema_required_fields_match_dataclass():
    schema = _schema("observation.schema.json")
    assert set(schema["required"]) == {
        "organ", "subject", "summary", "status", "provenance", "data"}
    assert set(schema["properties"]["status"]["enum"]) == _STATUSES


# --- full JSON-Schema validation when jsonschema is available --------------


def test_observation_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = _schema("observation.schema.json")
    png = encode_png(4, 4, bytes(4 * 4 * 3), channels=3)
    for subject in (png, b"not a png"):
        obs = VisualArtifactOrgan().observe(subject)[0]
        jsonschema.validate(obs.to_dict(), schema)


def test_drift_verdict_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    v = compare_drift("a" * 64, "b" * 64, 0x0F, 0x00)
    payload = {"verdict": v.verdict, "distance": v.distance, "reason": v.reason}
    jsonschema.validate(payload, _schema("drift-verdict.schema.json"))


def test_schema_rejects_authority_status():
    jsonschema = pytest.importorskip("jsonschema")
    payload = {
        "organ": "x", "subject": "y", "summary": "z", "status": "trusted",
        "provenance": {"source": "y", "digest": "sha256:" + "a" * 64,
                       "timestamp": "t", "confidence": "high"},
        "data": {},
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, _schema("observation.schema.json"))

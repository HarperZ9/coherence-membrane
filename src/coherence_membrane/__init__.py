"""coherence-membrane — an inert, host-adjudicated perception membrane.

A model's structural disability is state-blindness: it reasons on its prior and
on source text, not on what actually happened.  This package is the read-gate
that fixes that — it turns real artifacts into witnessed, re-derivable
Observations a model can ground on, and never grants authority of its own.  Its
write-gate complement is proof-surface's pre-execution gate.

Increment 1: a stdlib-only PNG perception path (identity + dimensions +
perceptual hash + drift), the inert organ + selftest contract, the perceive()
read API, and the membrane bridge that turns perceived state into a mediated
gate request.  Live capture (the D3D11 inert-interception adapter) is a later
increment.

Membrane doctrine, encoded not asserted: externalized, witnessed-not-inferred,
independently-checkable; an organ without a passing selftest is net-negative.
"""

from .capture import (
    CallableFrameSource,
    CaptureSource,
    DirectoryFrameSource,
    Frame,
    FrameDescriptor,
    IterableFrameSource,
)
from .continuity import ContinuityEvent, ResourceBudget, run_continuity
from .live import LiveDecision, LiveMembrane
from .membrane import build_gate_request, decide
from .native_capture import (
    CaptureUnavailable,
    ScreenCaptureSource,
    capture_available,
    grab_png,
)
from .baseline import Baseline, BaselineEntry, BaselineVerdict
from .observation import Observation, Provenance, Status, sha256_hex
from .organs.audio import AudioArtifactOrgan, audio_envelope_hash
from .pngencode import encode_png
from .scope import DEFAULT_CONSEQUENTIAL, ConsequenceScope, creative_profile
from .organ import Check, Organ, SelftestResult, run_selftests
from .organs.visual import VisualArtifactOrgan
from .perception import PerceptionSnapshot, all_organs, default_organs, perceive
from .phash import (
    DRIFT,
    DRIFT_VERDICTS,
    MATCH,
    UNVERIFIABLE,
    DriftVerdict,
    compare_drift,
    hamming,
    perceptual_hash,
)
from .pngview import DecodedImage, PngDecodeError, decode_png, is_png, read_ihdr

__all__ = [
    # contract
    "Observation",
    "Provenance",
    "Status",
    "sha256_hex",
    # organ + selftest
    "Organ",
    "Check",
    "SelftestResult",
    "run_selftests",
    "VisualArtifactOrgan",
    "AudioArtifactOrgan",
    "audio_envelope_hash",
    # perception (read-gate)
    "PerceptionSnapshot",
    "perceive",
    "default_organs",
    "all_organs",
    # baseline memory (drift against an authorized baseline, across modalities)
    "Baseline",
    "BaselineEntry",
    "BaselineVerdict",
    # write-gate bridge
    "build_gate_request",
    "decide",
    # live capture (frame-handoff contract + sources)
    "FrameDescriptor",
    "Frame",
    "CaptureSource",
    "DirectoryFrameSource",
    "CallableFrameSource",
    "IterableFrameSource",
    # continuity (change-proportional, self-throttling perception loop)
    "ResourceBudget",
    "ContinuityEvent",
    "run_continuity",
    # native, universal capture of the composited output (no shims)
    "capture_available",
    "grab_png",
    "ScreenCaptureSource",
    "CaptureUnavailable",
    "encode_png",
    # consequence scope (mediate consequence, never activity)
    "ConsequenceScope",
    "creative_profile",
    "DEFAULT_CONSEQUENTIAL",
    # the living loop (perceive + remember + mediate consequence)
    "LiveMembrane",
    "LiveDecision",
    # png + perceptual hashing
    "DecodedImage",
    "PngDecodeError",
    "decode_png",
    "is_png",
    "read_ihdr",
    "perceptual_hash",
    "hamming",
    "compare_drift",
    "DriftVerdict",
    "MATCH",
    "DRIFT",
    "UNVERIFIABLE",
    "DRIFT_VERDICTS",
]
__version__ = "0.1.0"

"""Tests for native, universal capture.

The pure logic (encode, convert, dispatch, graceful degradation) is tested
everywhere. The live grab is exercised only where a native backend is actually
available — otherwise it must raise CaptureUnavailable, never another error.
"""

from __future__ import annotations

from coherence_membrane.capture import IterableFrameSource
from coherence_membrane.continuity import ResourceBudget, run_continuity
from coherence_membrane.native_capture import (
    CaptureUnavailable,
    ScreenCaptureSource,
    capture_available,
    grab_png,
)
from coherence_membrane.phash import DRIFT, MATCH
from coherence_membrane.pngview import decode_png


def test_capture_available_returns_bool():
    assert isinstance(capture_available(), bool)


def test_grab_is_either_live_or_cleanly_unavailable():
    if capture_available():
        png, w, h = grab_png(region=(0, 0, 4, 4))
        img = decode_png(png)  # the whole native pipeline must produce valid PNG
        assert (img.width, img.height) == (4, 4)
        assert img.channels == 3
    else:
        # On a platform without a backend, the failure mode is a clean, typed one.
        try:
            grab_png(region=(0, 0, 4, 4))
        except CaptureUnavailable:
            pass
        else:
            raise AssertionError("expected CaptureUnavailable on a backend-less platform")


def test_non_positive_region_is_unavailable():
    if not capture_available():
        return  # the dispatch raises before dimension checks; covered above
    try:
        grab_png(region=(0, 0, 0, 0))
    except CaptureUnavailable:
        pass
    else:
        raise AssertionError("expected CaptureUnavailable for a zero-size region")


def test_screen_source_drives_continuity_when_available():
    if not capture_available():
        return
    source = ScreenCaptureSource(region=(0, 0, 16, 16))
    events = list(run_continuity(source, budget=ResourceBudget(), max_frames=2))
    assert len(events) == 2
    # Every event's verdict is in the closed lattice.
    assert all(e.verdict in {MATCH, DRIFT, "UNVERIFIABLE"} for e in events)
    assert events[0].verdict == DRIFT  # first capture establishes the baseline


def test_screen_source_frames_are_witnessable():
    if not capture_available():
        return
    source = ScreenCaptureSource(region=(0, 0, 8, 8))
    frame = next(iter(source.frames()))
    img = decode_png(frame.read())
    assert (img.width, img.height) == (8, 8)
    assert frame.descriptor.pixel_format == "png"

"""CLI: `python -m coherence_membrane selftest` and `... perceive <path...>`.

selftest runs every default organ's self-derivation checks and exits non-zero
on any failure — the membrane refuses to be trusted unverified.
"""

from __future__ import annotations

import json
import sys

from .continuity import ResourceBudget, run_continuity
from .native_capture import CaptureUnavailable, ScreenCaptureSource, capture_available, grab_png
from .organ import run_selftests
from .perception import all_organs, default_organs, perceive


def _selftest() -> int:
    report = run_selftests(all_organs())  # every sense proves itself
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


def _perceive(paths: list[str]) -> int:
    snapshot = perceive(paths)
    print(json.dumps(snapshot.to_dict(), indent=2))
    # Advisory exit: non-zero if anything could not be positively verified.
    from .observation import Status

    unverified = any(o.status == Status.UNVERIFIED for o in snapshot.observations)
    return 1 if unverified else 0


def _capture(out_path: str) -> int:
    if not capture_available():
        print(json.dumps({"capture_available": False, "platform": sys.platform}))
        return 2
    try:
        png, w, h = grab_png()
        with open(out_path, "wb") as f:
            f.write(png)
        print(json.dumps({"captured": out_path, "width": w, "height": h, "bytes": len(png)}))
        return 0
    except CaptureUnavailable as exc:
        print(json.dumps({"capture_available": True, "error": str(exc)}))
        return 2


def _watch(frames: int) -> int:
    if not capture_available():
        print(json.dumps({"capture_available": False, "platform": sys.platform}))
        return 2
    source = ScreenCaptureSource()
    # Modest cadence + a full-observation cap keep an always-on watch cheap.
    budget = ResourceBudget(min_interval_s=0.5, max_full_observations=frames)
    for event in run_continuity(source, budget=budget, max_frames=frames):
        print(json.dumps({
            "frame": event.frame_index, "verdict": event.verdict,
            "distance": event.distance, "throttled": event.throttled, "note": event.note,
        }))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print("usage: python -m coherence_membrane "
              "{selftest | perceive <path>... | capture <out.png> | watch [frames]}")
        return 0
    cmd, rest = args[0], args[1:]
    if cmd == "selftest":
        return _selftest()
    if cmd == "perceive":
        if not rest:
            print("perceive requires at least one path", file=sys.stderr)
            return 2
        return _perceive(rest)
    if cmd == "capture":
        if not rest:
            print("capture requires an output path", file=sys.stderr)
            return 2
        return _capture(rest[0])
    if cmd == "watch":
        frames = int(rest[0]) if rest else 10
        return _watch(frames)
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

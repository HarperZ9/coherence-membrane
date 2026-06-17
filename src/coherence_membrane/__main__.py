"""CLI: `python -m coherence_membrane selftest` and `... perceive <path...>`.

selftest runs every default organ's self-derivation checks and exits non-zero
on any failure — the membrane refuses to be trusted unverified.
"""

from __future__ import annotations

import json
import sys

from .organ import run_selftests
from .perception import default_organs, perceive


def _selftest() -> int:
    report = run_selftests(default_organs())
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


def _perceive(paths: list[str]) -> int:
    snapshot = perceive(paths)
    print(json.dumps(snapshot.to_dict(), indent=2))
    # Advisory exit: non-zero if anything could not be positively verified.
    from .observation import Status

    unverified = any(o.status == Status.UNVERIFIED for o in snapshot.observations)
    return 1 if unverified else 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print("usage: python -m coherence_membrane {selftest | perceive <path>...}")
        return 0
    cmd, rest = args[0], args[1:]
    if cmd == "selftest":
        return _selftest()
    if cmd == "perceive":
        if not rest:
            print("perceive requires at least one path", file=sys.stderr)
            return 2
        return _perceive(rest)
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

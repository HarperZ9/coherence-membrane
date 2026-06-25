"""distill: verified compression of code (and later prose), as graders on refine.

Compression is criterion-preserving: a candidate is accepted only when the
declared criterion survives. The model proposes; these deterministic graders
verify. No model in the checking step.
"""
from __future__ import annotations

_COMFORT_WIDTH = 100   # columns past which a line reads as crammed
_TAB = "    "


def _indent_depth(line: str) -> int:
    stripped = line.lstrip(" \t")
    lead = line[: len(line) - len(stripped)]
    return lead.replace("\t", _TAB).count(" ") // 4


def readability_cost(text: str) -> float:
    """A deterministic reconstruction-time proxy. Lower is easier to read.
    Penalizes over-density (lines past a comfortable width, flat structure)
    so a code-golfed candidate (few but crammed and unindented lines) does not
    score lower than a clear multi-line one. Indentation depth signals structure
    that aids reading, so it reduces the per-line weight via a structure factor.
    Language-agnostic; refined per language later."""
    lines = text.splitlines()
    if not lines:
        return 0.0
    n_lines = len(lines)
    over_width = sum(max(0, len(ln) - _COMFORT_WIDTH) for ln in lines)
    max_depth = max((_indent_depth(ln) for ln in lines), default=0)
    structure_factor = 1.0 / (1.0 + max_depth)
    return n_lines * structure_factor + 0.05 * over_width

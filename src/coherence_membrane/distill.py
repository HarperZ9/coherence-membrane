"""distill: verified compression of code (and later prose), as graders on refine.

Compression is criterion-preserving: a candidate is accepted only when the
declared criterion survives. The model proposes; these deterministic graders
verify. No model in the checking step.
"""
from __future__ import annotations


def readability_cost(text: str) -> float:
    """A deterministic reconstruction-time proxy. Lower is easier to read.

    The cost is the sum of each line's length SQUARED. Squaring makes a long,
    crammed line cost far more than the same characters split across clear lines:
    splitting an 80-column line into two 40-column lines drops the cost (rewarded),
    joining them back raises it (penalized). So a code-golfed candidate (logic
    crammed onto few long lines) scores worse than a clear multi-line one, while a
    short concise line is not punished. Indentation contributes mildly through line
    length, with no perverse reward for nesting. Language-agnostic; refined later.
    """
    return float(sum(len(line) ** 2 for line in text.splitlines()))

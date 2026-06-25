"""distill: verified compression of code (and later prose), as graders on refine.

Compression is criterion-preserving: a candidate is accepted only when the
declared criterion survives. The model proposes; these deterministic graders
verify. No model in the checking step.
"""
from __future__ import annotations

from .refine import GradedCriterion


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


def _ratio_deviation(numerator_of_candidate, original_value: float):
    """A deviation = candidate_value / original_value. >=0; ideal < 1; >= 1 fails
    at tolerance 1.0. Fail-closed: a zero or negative original yields inf (refine's
    grade then reads it as unmeasurable, never a false pass)."""
    def deviation(candidate_text: str) -> float:
        if original_value <= 0:
            return float("inf")
        return numerator_of_candidate(candidate_text) / original_value
    return deviation


def density_grader(original_bytes: int) -> GradedCriterion:
    return GradedCriterion(
        "density", "objective",
        _ratio_deviation(lambda t: len(t.encode("utf-8")), float(original_bytes)),
        1.0,
    )


def readability_grader(original_cost: float) -> GradedCriterion:
    return GradedCriterion(
        "readability", "objective",
        _ratio_deviation(readability_cost, original_cost),
        1.0,
    )

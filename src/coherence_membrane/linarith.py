"""Native quantifier-free linear rational arithmetic (QF-LRA), conjunctive fragment,
with PROOF-CARRYING verdicts.

Propositional logic cannot reason over `2x + 3y <= 5`. This decides conjunctions of
linear constraints by Fourier-Motzkin elimination — but does NOT trust the solver:
every verdict carries a WITNESS a tiny independent checker re-verifies. Feasible -> a
rational model (checked by substitution); infeasible -> a Farkas certificate (a
nonnegative/signed combination collapsing the system to `0 (op) negative`, checked by
arithmetic). VERIFIED only if the witness checks, so a bug anywhere in elimination
yields an invalid witness -> UNVERIFIABLE, never a false VERIFIED. The trusted base is
the checker, not the solver. Rational-exact (fractions.Fraction)."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .certificate import Certificate, Verdict
from .composition import compose

_ORACLE = "lra-fm-v1"
_ROW_CAP = 4000


@dataclass(frozen=True)
class LinearConstraint:
    """sum(coeff*var) op rhs, op in {"<=","<","="}; terms sorted, nonzero, Fraction."""

    terms: tuple
    op: str
    rhs: Fraction

    def coeff(self, var: str) -> Fraction:
        for v, c in self.terms:
            if v == var:
                return c
        return Fraction(0)

    @property
    def variables(self) -> tuple:
        return tuple(v for v, _ in self.terms)

    def evaluate(self, point: dict) -> bool:
        lhs = sum((c * Fraction(point[v]) for v, c in self.terms), Fraction(0))
        if self.op == "<=":
            return lhs <= self.rhs
        if self.op == "<":
            return lhs < self.rhs
        return lhs == self.rhs


def constraint(coeffs: dict, op: str, rhs) -> LinearConstraint:
    """Normalized builder: >=/> are flipped to <=/< (x-1); zero coeffs dropped; sorted."""
    rhs = Fraction(rhs)
    items = {v: Fraction(c) for v, c in coeffs.items() if Fraction(c) != 0}
    if op in (">=", ">"):
        items = {v: -c for v, c in items.items()}
        rhs = -rhs
        op = "<=" if op == ">=" else "<"
    if op not in ("<=", "<", "="):
        raise ValueError(f"bad op {op!r}")
    return LinearConstraint(tuple(sorted(items.items())), op, rhs)


def negate(c: LinearConstraint):
    """Single-constraint negation, or None for '=' (its negation is a disjunction)."""
    coeffs = {v: cc for v, cc in c.terms}
    if c.op == "<=":
        return constraint(coeffs, ">", c.rhs)
    if c.op == "<":
        return constraint(coeffs, ">=", c.rhs)
    return None

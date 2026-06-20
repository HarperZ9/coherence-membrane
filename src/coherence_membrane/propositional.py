"""Native propositional logic: formula AST, evaluation, DPLL, Certificate checks.

Sound + complete + decidable for propositional logic. The deductive oracle (tier 1)
of the verifier ladder; soundness is enforced (never a false VERIFIED)."""
from __future__ import annotations

from dataclasses import dataclass

from .certificate import Certificate, Verdict


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Const:
    value: bool


@dataclass(frozen=True)
class Not:
    x: object


@dataclass(frozen=True)
class And:
    a: object
    b: object


@dataclass(frozen=True)
class Or:
    a: object
    b: object


@dataclass(frozen=True)
class Implies:
    a: object
    b: object


@dataclass(frozen=True)
class Iff:
    a: object
    b: object


_BINARY = (And, Or, Implies, Iff)
_FORMULA_TYPES = (Var, Const, Not, And, Or, Implies, Iff)


def is_formula(x) -> bool:
    return isinstance(x, _FORMULA_TYPES)


def atoms(f) -> set[str]:
    if isinstance(f, Const):
        return set()
    if isinstance(f, Var):
        return {f.name}
    if isinstance(f, Not):
        return atoms(f.x)
    if isinstance(f, _BINARY):
        return atoms(f.a) | atoms(f.b)
    raise TypeError(f"not a formula: {f!r}")


def evaluate(f, a: dict) -> bool:
    """Evaluate under a TOTAL assignment (every atom present)."""
    if isinstance(f, Const):
        return f.value
    if isinstance(f, Var):
        return a[f.name]
    if isinstance(f, Not):
        return not evaluate(f.x, a)
    if isinstance(f, And):
        return evaluate(f.a, a) and evaluate(f.b, a)
    if isinstance(f, Or):
        return evaluate(f.a, a) or evaluate(f.b, a)
    if isinstance(f, Implies):
        return (not evaluate(f.a, a)) or evaluate(f.b, a)
    if isinstance(f, Iff):
        return evaluate(f.a, a) == evaluate(f.b, a)
    raise TypeError(f"not a formula: {f!r}")


def show(f) -> str:
    if isinstance(f, Const):
        return "T" if f.value else "F"
    if isinstance(f, Var):
        return f.name
    if isinstance(f, Not):
        return f"~{show(f.x)}"
    if isinstance(f, And):
        return f"({show(f.a)} & {show(f.b)})"
    if isinstance(f, Or):
        return f"({show(f.a)} | {show(f.b)})"
    if isinstance(f, Implies):
        return f"({show(f.a)} -> {show(f.b)})"
    if isinstance(f, Iff):
        return f"({show(f.a)} <-> {show(f.b)})"
    raise TypeError(f"not a formula: {f!r}")

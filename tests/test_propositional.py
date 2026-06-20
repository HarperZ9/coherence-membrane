from __future__ import annotations

from coherence_membrane.propositional import (
    And, Const, Iff, Implies, Not, Or, Var,
    atoms, evaluate, is_formula, show,
    OverCap, solve,
)


def _mp():  # modus ponens:  (A & (A -> B)) -> B
    A, B = Var("A"), Var("B")
    return Implies(And(A, Implies(A, B)), B)


def test_atoms_and_is_formula():
    assert atoms(_mp()) == {"A", "B"}
    assert is_formula(_mp()) is True
    assert is_formula("A & B") is False
    assert atoms(Const(True)) == set()


def test_evaluate_truth_table():
    # modus ponens is true under every assignment
    for a in (True, False):
        for b in (True, False):
            assert evaluate(_mp(), {"A": a, "B": b}) is True
    # A -> B is false only at A=1,B=0
    f = Implies(Var("A"), Var("B"))
    assert evaluate(f, {"A": True, "B": False}) is False
    assert evaluate(f, {"A": False, "B": False}) is True


def test_show_is_deterministic():
    assert show(_mp()) == "((A & (A -> B)) -> B)"
    assert show(Not(Var("A"))) == "~A"
    assert show(Const(True)) == "T"


def test_solve_sat_unsat():
    A, B = Var("A"), Var("B")
    # satisfiable: A & ~B  -> model A=1,B=0
    m = solve(And(A, Not(B)))
    assert m == {"A": True, "B": False}
    # unsatisfiable: A & ~A -> None
    assert solve(And(A, Not(A))) is None
    # negation of a tautology is unsat
    assert solve(Not(Or(A, Not(A)))) is None


def test_solve_over_cap():
    import pytest
    f = Or(Or(Var("A"), Var("B")), Var("C"))   # 3 atoms
    with pytest.raises(OverCap):
        solve(f, max_atoms=2)

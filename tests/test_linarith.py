from __future__ import annotations

from fractions import Fraction

from coherence_membrane.linarith import LinearConstraint, constraint, negate


def test_constraint_normalizes_ge_gt():
    c = constraint({"x": 1}, ">=", 3)          # x >= 3  ->  -x <= -3
    assert c.op == "<=" and c.coeff("x") == Fraction(-1) and c.rhs == Fraction(-3)
    g = constraint({"x": 2}, ">", 1)           # 2x > 1  ->  -2x < -1
    assert g.op == "<" and g.coeff("x") == Fraction(-2) and g.rhs == Fraction(-1)


def test_constraint_drops_zero_and_sorts():
    c = constraint({"y": 0, "b": 1, "a": 2}, "<=", 5)
    assert c.terms == (("a", Fraction(2)), ("b", Fraction(1)))
    assert c.variables == ("a", "b")


def test_evaluate():
    c = constraint({"x": 1, "y": 1}, "<=", 5)
    assert c.evaluate({"x": 2, "y": 3}) is True
    assert c.evaluate({"x": 4, "y": 3}) is False
    assert constraint({"x": 1}, "=", 2).evaluate({"x": 2}) is True
    assert constraint({"x": 1}, "<", 2).evaluate({"x": 2}) is False


def test_negate():
    assert negate(constraint({"x": 1}, "<=", 3)).op == "<"   # ¬(x<=3) is (x>3) -> -x < -3
    assert negate(constraint({"x": 1}, "<=", 3)).coeff("x") == Fraction(-1)
    assert negate(constraint({"x": 1}, "<", 3)).op == "<="   # ¬(x<3) is (x>=3) -> -x <= -3
    assert negate(constraint({"x": 1}, "=", 3)) is None      # disjunction

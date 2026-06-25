from coherence_membrane.distill import readability_cost


def test_readability_cost_penalizes_code_golf_over_clear():
    clear = "def f(x):\n    y = x + 1\n    return y\n"
    golf = "def f(x):\n return (lambda y:y)(x+1) if x else (x+1)+0+0+0+0+0+0+0+0+0+0+0+0\n"
    # the golfed line is shorter in lines but crammed; clear must score lower (better)
    assert readability_cost(clear) < readability_cost(golf)


def test_readability_cost_is_deterministic():
    t = "a = 1\n    b = 2\n"
    assert readability_cost(t) == readability_cost(t)


def test_readability_cost_empty_is_zero_floor():
    assert readability_cost("") == 0.0

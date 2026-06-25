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


# Task 2: density and readability graders
from coherence_membrane.distill import density_grader, readability_grader, readability_cost
from coherence_membrane.refine import grade


def test_density_grader_rewards_smaller_rejects_bigger():
    orig = "x = 1\n" * 10                       # 60 bytes
    dg = density_grader(len(orig.encode("utf-8")))
    smaller = grade(dg, "x = 1\n" * 5)          # 30 bytes -> ratio 0.5 -> margin 0.5
    bigger = grade(dg, "x = 1\n" * 20)          # ratio 2.0 -> margin -1.0
    assert smaller.ok and smaller.margin > 0
    assert not bigger.ok


def test_readability_grader_rejects_worse_readability():
    orig = "a = 1\nb = 2\n"
    rg = readability_grader(readability_cost(orig))
    worse = grade(rg, "a=1;b=2;" + "z"*200 + "\n")   # one crammed line -> cost up -> margin < 0
    assert not worse.ok

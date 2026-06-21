from __future__ import annotations

import math

from coherence_membrane.phyllotaxis import GOLDEN_ANGLE, golden_angle_deviation


def _golden_spiral(n, direction=1):
    return [(math.sqrt(i) * math.cos(math.radians(i * GOLDEN_ANGLE * direction)),
             math.sqrt(i) * math.sin(math.radians(i * GOLDEN_ANGLE * direction))) for i in range(n)]


def test_golden_angle_value():
    assert abs(GOLDEN_ANGLE - 137.50776405) < 1e-6


def test_golden_spiral_near_zero():
    assert golden_angle_deviation(_golden_spiral(400)) < 2.0   # it IS the signature


def test_direction_agnostic():
    # both chiralities are golden spirals: clockwise (360 - g) scores as low as ccw
    assert golden_angle_deviation(_golden_spiral(400, direction=-1)) < 2.0


def test_grid_is_far():
    grid = [(x, y) for x in range(10) for y in range(10)]
    assert golden_angle_deviation(grid) > 20.0


def test_wrong_angle_spiral_is_far():
    # a spiral at the WRONG turn (90 deg) is structured but NOT golden -> far
    sq = [(math.sqrt(i) * math.cos(math.radians(i * 90.0)),
           math.sqrt(i) * math.sin(math.radians(i * 90.0))) for i in range(300)]
    assert golden_angle_deviation(sq) > 20.0


def test_too_few_points_is_infinite():
    assert math.isinf(golden_angle_deviation([(0.0, 0.0), (1.0, 1.0)]))
    assert math.isinf(golden_angle_deviation([]))

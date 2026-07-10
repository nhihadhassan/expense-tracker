#!/usr/bin/env python3
"""Deterministic fixtures for the dashboard's treasury analytics formulas."""

from math import isclose, sqrt


def normalized_total(raw, observed_days, days_in_month):
    return raw * days_in_month / max(1, observed_days)


def population_stddev(values):
    mean = sum(values) / len(values)
    return sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def test_partial_month_normalization():
    assert isclose(normalized_total(500, 10, 30), 1500)
    assert isclose(normalized_total(500, 30, 30), 500)


def test_uncertainty_band():
    history = [800, 1200, 1000]
    spread = population_stddev(history)
    projected = 950
    assert isclose(spread, sqrt(80000 / 3))
    assert isclose(projected - spread, 786.7006838, rel_tol=1e-7)
    assert isclose(projected + spread, 1113.2993162, rel_tol=1e-7)


def test_budget_gap():
    normalized = 1500
    monthly_plan = 1200
    gap = normalized - monthly_plan
    assert gap == 300
    assert gap / monthly_plan * 100 == 25


if __name__ == "__main__":
    test_partial_month_normalization()
    test_uncertainty_band()
    test_budget_gap()
    print("PASS - analytics fixtures: normalization, uncertainty, budget gap")

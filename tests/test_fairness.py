"""
test_fairness.py  (tests for Module 6 — the differentiator)
Confirms low-value over-spenders get tightened while high-value teams are spared.
"""

from app.fairness import compute_identity_policies, fair_share_envelopes, value_per_dollar


def test_equal_fair_share():
    env = fair_share_envelopes(["a", "b", "c", "d"], 100.0)
    assert all(abs(v - 25.0) < 1e-6 for v in env.values())


def test_value_per_dollar():
    assert value_per_dollar(100, 10.0) == 10.0
    assert value_per_dollar(5, 0.0) == 0.0  # no divide-by-zero crash


def test_low_value_overspender_is_tightened_high_value_protected():
    per = {
        "valuable_team": {"spend": 8.0, "successes": 160, "requests": 170},  # high value/$
        "waster":        {"spend": 9.0, "successes": 20, "requests": 180},   # low value/$
        "light_user":    {"spend": 1.0, "successes": 18, "requests": 20},    # under pace
    }
    pol = compute_identity_policies(per, global_budget=30, period_fraction_elapsed=0.5)
    assert pol["waster"]["action"] == "tighten"
    assert pol["valuable_team"]["action"] == "protected_high_value"
    assert pol["light_user"]["action"] == "normal"

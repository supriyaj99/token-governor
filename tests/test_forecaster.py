"""
test_forecaster.py  (tests for Module 5)
Confirms the forecaster spots overspending and the controller reacts.
"""

from app.forecaster import decide_control_mode, forecast_exhaustion


def test_on_track_budget_stays_normal():
    # $1/day against a $30 / 30-day budget lasts the whole period.
    fc = forecast_exhaustion([1.0] * 10, budget=30, period_days=30)
    assert fc["on_track"] is True
    assert decide_control_mode(fc)["mode"] == "normal"


def test_overspending_triggers_tightening():
    # $3/day against the same budget runs out around day 10.
    fc = forecast_exhaustion([3.0] * 10, budget=30, period_days=30)
    assert fc["on_track"] is False
    assert fc["projected_exhaustion_day"] <= 15
    assert decide_control_mode(fc)["mode"] in ("tighten", "emergency")


def test_no_spend_does_not_crash():
    fc = forecast_exhaustion([], budget=30, period_days=30)
    assert fc["on_track"] is True
    assert decide_control_mode(fc)["mode"] == "normal"

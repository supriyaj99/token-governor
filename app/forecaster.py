"""
forecaster.py  (Module 5 — budget forecaster + autonomous controller)
---------------------------------------------------------------------
Two jobs:

1) FORECAST: look at how spending has been trending and predict WHEN the budget
   will run out. We use a simple, explainable method — fit a straight line to
   cumulative spend over time (least-squares linear regression) to estimate the
   average daily burn rate, then project it forward. (Prophet or ARIMA are the
   fancier upgrades; a linear run-rate is a perfectly good, transparent start
   and easy to defend in an interview.)

2) CONTROL: if we're on track to run out BEFORE the budget period ends, the
   controller automatically picks a tighter spending mode so the router leans
   on cheaper models — *before* the money is gone, not after. This "predict then
   act on its own" loop is the part most off-the-shelf tools don't do.

No third-party libraries needed — this is pure Python.
"""

from typing import Dict, List, Optional


def _linear_fit(xs: List[float], ys: List[float]) -> (float, float):
    """
    Fit y = slope*x + intercept by least squares. Returns (slope, intercept).
    Slope here = average dollars spent per day (the burn rate).
    """
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return 0.0, mean_y
    slope = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n)) / denom
    intercept = mean_y - slope * mean_x
    return slope, intercept


def forecast_exhaustion(
    daily_spend: List[float],
    budget: float,
    period_days: int,
) -> Dict:
    """
    Given spend-per-day so far, a total budget, and how long the budget period
    is, predict when the budget will be exhausted.

    Returns a dict with:
      - burn_rate_per_day: estimated average daily spend
      - spent_so_far: total spent to date
      - projected_exhaustion_day: day number the budget is projected to hit 0
        (counting from the start of the period); None if not within the period
      - days_into_period: how many days of data we have
      - on_track: True if the budget is projected to LAST the whole period
    """
    days_into_period = len(daily_spend)
    spent_so_far = sum(daily_spend)

    # Build cumulative spend series and fit a line to estimate burn rate.
    cumulative = []
    running = 0.0
    for d in daily_spend:
        running += d
        cumulative.append(running)
    xs = list(range(1, days_into_period + 1))
    slope, intercept = _linear_fit(xs, cumulative)
    burn_rate = max(slope, 0.0)

    # Project forward: on what day does cumulative spend cross the budget?
    projected_day: Optional[int] = None
    if burn_rate > 0:
        # cumulative(day) = slope*day + intercept ; solve for budget.
        day_cross = (budget - intercept) / slope
        if day_cross >= 1:
            projected_day = int(round(day_cross))

    on_track = projected_day is None or projected_day >= period_days

    return {
        "burn_rate_per_day": round(burn_rate, 6),
        "spent_so_far": round(spent_so_far, 6),
        "budget": budget,
        "period_days": period_days,
        "days_into_period": days_into_period,
        "projected_exhaustion_day": projected_day,
        "on_track": on_track,
    }


# The spending modes the controller can choose, and how aggressively each one
# pushes the router toward cheaper models. Lower "confidence" means the router
# accepts cheaper tiers more readily (spends less, trades a little quality).
CONTROL_MODES = {
    "normal":    {"router_confidence": 0.60, "note": "healthy budget; optimize normally"},
    "tighten":   {"router_confidence": 0.45, "note": "projected to overspend; favor cheaper models"},
    "emergency": {"router_confidence": 0.30, "note": "severe overspend risk; cheapest viable models"},
}


def decide_control_mode(forecast: Dict) -> Dict:
    """
    Turn a forecast into an action. The sooner we're projected to run out
    relative to the end of the period, the more aggressively we tighten.

    Returns {"mode": ..., "router_confidence": ..., "reason": ...}.
    """
    period = forecast["period_days"]
    proj = forecast["projected_exhaustion_day"]

    if proj is None or proj >= period:
        mode = "normal"
        reason = "On track to stay within budget for the full period."
    else:
        # How early are we projected to run out? (fraction of the period)
        earliness = (period - proj) / period
        if earliness >= 0.25:
            mode = "emergency"
            reason = f"Projected to exhaust budget on day {proj} of {period} — far too early."
        else:
            mode = "tighten"
            reason = f"Projected to exhaust budget on day {proj} of {period} — ahead of plan."

    return {
        "mode": mode,
        "router_confidence": CONTROL_MODES[mode]["router_confidence"],
        "reason": reason,
    }

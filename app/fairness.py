"""
fairness.py  (Module 6 — value-weighted fair-share layer)  ** the differentiator **
-----------------------------------------------------------------------------------
This is the part that goes further than off-the-shelf gateways.

Normal budget tools, when money runs low, tighten EVERYONE equally, or just
hard-block whoever hits their cap. Two problems with that:
  - It treats a user whose spend produces great results the same as a user whose
    spend mostly produces junk.
  - It splits the budget by a fixed rule with no notion of VALUE.

Our idea: give each identity (user / team / project) a fair SHARE of the budget,
and when someone is on track to blow their share, tighten the LOW-VALUE spenders
first — where "value" is grounded in MEASURED outcomes (quality per dollar from
Module 3), not a self-declared "I'm important" label (which everyone games).

So: heavy spending that produces good answers is protected; heavy spending that
produces poor answers gets throttled first. That's the novel, defensible slice.

Everything here is simple, explainable Python.
"""

from typing import Dict, List, Optional


def fair_share_envelopes(
    identities: List[str],
    global_budget: float,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    Split the global budget into a per-identity 'envelope' (their fair share).

    - If no weights are given, split EQUALLY (simplest defensible version).
    - weights let you make it proportional to headcount, a priority tier, or a
      value score. envelope_i = global_budget * weight_i / sum(weights).
    """
    if not identities:
        return {}
    if weights is None:
        weights = {i: 1.0 for i in identities}
    total_w = sum(weights.get(i, 0.0) for i in identities) or 1.0
    return {i: round(global_budget * weights.get(i, 0.0) / total_w, 6) for i in identities}


def value_per_dollar(successful_requests: int, dollars_spent: float) -> float:
    """
    Our VALUE signal: how many successful (quality-passing) answers did this
    identity get per dollar? Higher = more value. Grounded in measured outcomes,
    so it can't be gamed by self-reporting importance.
    """
    if dollars_spent <= 0:
        return 0.0
    return round(successful_requests / dollars_spent, 4)


def compute_identity_policies(
    per_identity: Dict[str, Dict],
    global_budget: float,
    period_fraction_elapsed: float,
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Dict]:
    """
    Decide, per identity, whether to tighten its routing.

    Inputs:
      per_identity[id] = {"spend": float, "successes": int, "requests": int}
      global_budget         : total budget for the period
      period_fraction_elapsed: 0..1, how far through the budget period we are
      weights               : optional fair-share weights (see above)

    Logic:
      1. Compute each identity's fair-share envelope.
      2. An identity is "over pace" if it has already spent a bigger fraction of
         its envelope than the fraction of the period that has elapsed.
      3. Among the over-pace identities, tighten the ones with the LOWEST
         value-per-dollar first (least bang for the buck).

    Returns per_identity_policy[id] = {
        "envelope", "spend", "pace_ratio", "value_per_dollar",
        "over_pace", "action"   # "normal" or "tighten"
    }
    """
    ids = list(per_identity.keys())
    envelopes = fair_share_envelopes(ids, global_budget, weights)

    out: Dict[str, Dict] = {}
    for i in ids:
        info = per_identity[i]
        spend = float(info.get("spend", 0.0))
        env = envelopes.get(i, 0.0)
        # pace_ratio > 1 means spending faster than the budget period is passing.
        used_frac = (spend / env) if env > 0 else 999.0
        pace_ratio = (used_frac / period_fraction_elapsed) if period_fraction_elapsed > 0 else 999.0
        vpd = value_per_dollar(int(info.get("successes", 0)), spend)
        out[i] = {
            "envelope": round(env, 6),
            "spend": round(spend, 6),
            "pace_ratio": round(pace_ratio, 3),
            "value_per_dollar": vpd,
            "over_pace": pace_ratio > 1.0,
            "action": "normal",  # may be upgraded to "tighten" below
        }

    # The value-weighting: among over-pace identities, tighten the LOW-VALUE
    # ones and PROTECT the high-value ones. We use the average value-per-dollar
    # across active identities as the dividing line — an over-pace identity is
    # tightened only if its value-per-dollar is below that average. So a team
    # that spends a lot but produces lots of good answers is spared, while a
    # team that burns money for poor results is throttled first.
    active = [i for i in ids if out[i]["spend"] > 0]
    avg_vpd = (sum(out[i]["value_per_dollar"] for i in active) / len(active)) if active else 0.0

    over = [i for i in ids if out[i]["over_pace"]]
    over.sort(key=lambda i: out[i]["value_per_dollar"])  # lowest value first
    for i in over:
        if out[i]["value_per_dollar"] < avg_vpd:
            out[i]["action"] = "tighten"
        else:
            out[i]["action"] = "protected_high_value"

    for i in ids:
        out[i]["avg_value_per_dollar"] = round(avg_vpd, 4)

    return out

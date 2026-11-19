"""
tiers.py
--------
We group the models the router can choose from into three "tiers" by
capability and price:

    nano  -> cheapest, least capable   (good for easy requests)
    mid   -> middle ground
    full  -> most capable, most expensive (needed for hard requests)

The router's whole job is to pick the CHEAPEST tier that is still good enough
for a given request. This file defines the tiers in one place: which concrete
model each maps to, and a rough "skill" level used by the offline simulator.
"""

from app.pricing import compute_cost

# Each tier maps to a concrete model name and a skill level in 0..1.
# "skill" is ONLY used by the offline simulator (simulate.py) to decide how
# likely a tier is to answer a request well. In real mode, real models answer
# and the quality module scores them — skill is not used.
TIERS = {
    "nano": {"model": "gpt-4o-mini",        "skill": 0.55},
    "mid":  {"model": "claude-3-5-haiku",   "skill": 0.78},
    "full": {"model": "gpt-4o",             "skill": 0.95},
}

# The order from cheapest to most expensive. The router uses this to pick the
# cheapest acceptable tier.
TIER_ORDER = ["nano", "mid", "full"]


def tier_model(tier: str) -> str:
    """Return the concrete model name for a tier, e.g. 'nano' -> 'gpt-4o-mini'."""
    return TIERS[tier]["model"]


def tier_skill(tier: str) -> float:
    """Return the simulator skill level for a tier."""
    return TIERS[tier]["skill"]


def _representative_cost(tier: str) -> float:
    """
    A single comparable price for a tier, assuming a typical request of ~500
    input + ~300 output tokens. Used only to rank tiers cheapest-first.
    """
    return compute_cost(tier_model(tier), 500, 300)


# Precompute the cost ranking once (cheapest tier first).
TIERS_BY_COST = sorted(TIER_ORDER, key=_representative_cost)

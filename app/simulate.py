"""
simulate.py
-----------
An OFFLINE SIMULATOR so the whole system — routing, forecasting, benchmarking —
runs and produces meaningful numbers with NO API key and NO internet.

Why this exists (and why it's a good interview talking point): to evaluate a
router you need to know "what quality would tier X have produced for this
request?" You can't know that for every tier without paying to call all of
them. So, like reinforcement-learning researchers do, we build a synthetic
"world" where each request has a hidden difficulty and each tier has a skill
level; a tier answers well when its skill exceeds the difficulty. This lets us
test and benchmark the router cheaply and repeatably. Flip MOCK_MODE off and the
exact same router logic drives real model calls instead.

The model is deliberately simple and explainable:
    difficulty = f(complexity of the request)
    expected_quality(tier) = centered on (skill_of_tier - difficulty)
    actual_quality         = expected_quality + a little random noise
"""

import random
from typing import Dict

from app.tiers import tier_skill


def request_difficulty(features: Dict) -> float:
    """
    Turn the classifier's features into a hidden 'difficulty' in 0..1.
    Complexity is the main driver; code tasks get a small bump.
    """
    base = 0.15 + 0.70 * float(features.get("complexity", 0.3))
    if features.get("has_code"):
        base += 0.05
    return max(0.0, min(base, 1.0))


def simulate_quality(tier: str, features: Dict, rng: random.Random = None) -> float:
    """
    Produce a synthetic quality score (0..1) for answering `features` with `tier`.
    Higher-skill tiers reliably beat harder requests; weak tiers struggle on
    hard ones. Small Gaussian noise makes it realistic (and gives the bandit
    something to average over).
    """
    rng = rng or random
    d = request_difficulty(features)
    skill = tier_skill(tier)
    # Center quality on how much the tier's skill exceeds the difficulty.
    mean_q = 0.6 + (skill - d) * 0.9
    q = rng.gauss(mean_q, 0.06)
    return max(0.0, min(q, 1.0))


def simulate_tokens(features: Dict, rng: random.Random = None) -> Dict[str, int]:
    """
    Produce believable input/output token counts for a simulated request.
    Bigger/more complex requests use more tokens. Token use is roughly the same
    across tiers (it's the per-token PRICE that differs between tiers).
    """
    rng = rng or random
    est_in = int(features.get("est_prompt_tokens", 100))
    est_in = max(20, est_in + rng.randint(-10, 20))
    # Output length grows a bit with complexity.
    est_out = int(40 + 400 * float(features.get("complexity", 0.3)) + rng.randint(-10, 30))
    est_out = max(10, est_out)
    return {"prompt_tokens": est_in, "completion_tokens": est_out}

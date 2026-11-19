"""
router.py  (Module 4 — the learning router)
-------------------------------------------
This is the "brain" and the most impressive piece to talk about in interviews.

The problem: for each request, which model tier (nano / mid / full) should we
use? We want the CHEAPEST tier that still clears a quality bar. But we don't
know in advance which tier is good enough for which kind of request — so we
LEARN it from outcomes, and keep improving.

The technique: a **Thompson-sampling contextual bandit.**
- "Bandit" = an algorithm that repeatedly chooses among options ("arms") and
  learns from the reward each choice gives. The name comes from slot machines
  ("one-armed bandits").
- "Contextual" = the best choice depends on context — here, the kind of request
  (task type + how complex). We learn a separate policy per context.
- "Thompson sampling" = for each arm we keep a Beta distribution describing our
  belief about "how often does this tier meet the quality bar for this context?"
  To choose, we draw a random sample from each arm's belief and act on the draw.
  Early on, beliefs are wide, so we naturally EXPLORE; as evidence accumulates,
  beliefs narrow and we EXPLOIT the best option. This balances explore/exploit
  automatically — better than a fixed exploration rate.

Decision rule each request:
  1. Sample each tier's probability of meeting the bar.
  2. Among tiers whose sampled probability is "confident enough", pick the
     CHEAPEST one.
  3. If none look good enough, fall back to the most capable tier (full).

Reward: after the call we observe the quality. "Success" = quality >= bar. We
nudge the chosen tier's belief up on success, down on failure.

State is saved to a small JSON file so learning survives restarts — no database
schema change needed.
"""

import json
import os
import random
from typing import Dict, List, Optional

from app.tiers import TIERS_BY_COST, TIER_ORDER

# Where the learned beliefs are stored between runs.
_DEFAULT_STATE_PATH = os.getenv("BANDIT_STATE_PATH", "bandit_state.json")


def complexity_bucket(complexity: float) -> str:
    """Group a 0..1 complexity score into low / med / high for the context key."""
    if complexity < 0.34:
        return "low"
    if complexity < 0.67:
        return "med"
    return "high"


def context_key(features: Dict) -> str:
    """Build the context label the bandit learns per, e.g. 'code:high'."""
    task = features.get("task_type", "chat")
    return f"{task}:{complexity_bucket(float(features.get('complexity', 0.3)))}"


class ThompsonRouter:
    """A Thompson-sampling contextual bandit over model tiers."""

    def __init__(self, quality_bar: float = 0.7, confidence: float = 0.6, seed: Optional[int] = None):
        # quality_bar: the minimum quality we consider a "success".
        # confidence: how sure (0..1) we must be a tier meets the bar to allow
        #             picking it as the cheap option.
        self.quality_bar = quality_bar
        self.confidence = confidence
        self.rng = random.Random(seed)
        # beliefs[context][tier] = [alpha, beta] for a Beta distribution.
        # alpha ~ remembered successes (+1), beta ~ remembered failures (+1).
        self.beliefs: Dict[str, Dict[str, List[float]]] = {}

    def _arms_for(self, ctx: str) -> Dict[str, List[float]]:
        """Get (or create) the belief table for a context, starting optimistic-ish."""
        if ctx not in self.beliefs:
            # Start every arm at Beta(1,1) = "no idea yet" (uniform).
            self.beliefs[ctx] = {tier: [1.0, 1.0] for tier in TIER_ORDER}
        return self.beliefs[ctx]

    def choose(self, features: Dict) -> str:
        """Pick a tier for this request and return its name ('nano'/'mid'/'full')."""
        ctx = context_key(features)
        arms = self._arms_for(ctx)

        # Step 1: Thompson sample each tier's P(meets bar).
        sampled = {
            tier: self.rng.betavariate(arms[tier][0], arms[tier][1])
            for tier in TIER_ORDER
        }

        # Step 2: among tiers we're confident enough about, choose the cheapest.
        for tier in TIERS_BY_COST:  # cheapest first
            if sampled[tier] >= self.confidence:
                return tier

        # Step 3: nobody looks good enough — use the arm with the best sample
        # (typically 'full'), so hard requests still get a capable model.
        return max(sampled, key=sampled.get)

    def update(self, features: Dict, tier: str, quality: float) -> None:
        """Record what happened: nudge the chosen tier's belief up or down."""
        ctx = context_key(features)
        arms = self._arms_for(ctx)
        if quality >= self.quality_bar:
            arms[tier][0] += 1.0   # a success
        else:
            arms[tier][1] += 1.0   # a failure

    # ---- persistence so learning survives restarts ----
    def to_dict(self) -> Dict:
        return {
            "quality_bar": self.quality_bar,
            "confidence": self.confidence,
            "beliefs": self.beliefs,
        }

    def load_dict(self, data: Dict) -> None:
        self.quality_bar = data.get("quality_bar", self.quality_bar)
        self.confidence = data.get("confidence", self.confidence)
        self.beliefs = data.get("beliefs", {})

    def save(self, path: str = _DEFAULT_STATE_PATH) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str = _DEFAULT_STATE_PATH) -> "ThompsonRouter":
        r = cls()
        if os.path.exists(path):
            try:
                with open(path) as f:
                    r.load_dict(json.load(f))
            except Exception:
                pass  # corrupt/missing file -> start fresh
        return r

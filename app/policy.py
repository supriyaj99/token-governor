"""
policy.py  (shared governance state)
------------------------------------
This is the small shared "control panel" the forecaster (Module 5) and the
fairness layer (Module 6) write to, and that the router (Module 4) reads from
when it makes each decision.

- global_mode comes from the forecaster: normal / tighten / emergency. It sets
  a baseline router confidence for everyone (lower confidence = cheaper models).
- identity_actions comes from the fairness layer: for specific identities that
  are over their fair share AND low-value, we tighten them further.

Keeping this in one place means routing decisions always reflect the latest
governance decisions, and it's easy to inspect what the system is currently
doing and why.
"""

from app.forecaster import CONTROL_MODES

# How much extra to lower confidence for an identity the fairness layer flags.
_IDENTITY_TIGHTEN_PENALTY = 0.15


class GovernancePolicy:
    def __init__(self, base_confidence: float = 0.60):
        self.base_confidence = base_confidence
        self.global_mode = "normal"
        self.global_confidence = base_confidence
        # identity -> "normal" | "tighten" | "protected_high_value"
        self.identity_actions = {}
        self.last_forecast = {}
        self.last_fairness = {}

    def set_global_mode(self, mode: str) -> None:
        """Called by the controller after each forecast."""
        self.global_mode = mode
        self.global_confidence = CONTROL_MODES.get(mode, {}).get("router_confidence", self.base_confidence)

    def set_identity_actions(self, actions: dict) -> None:
        """Called by the fairness layer after it decides per-identity actions."""
        self.identity_actions = {i: a.get("action", "normal") for i, a in actions.items()}

    def effective_confidence(self, identity: str) -> float:
        """
        The router confidence to use for THIS identity right now = the global
        confidence, lowered a bit more if this identity was flagged to tighten.
        Lower confidence makes the router accept cheaper models more readily.
        """
        conf = self.global_confidence
        if self.identity_actions.get(identity) == "tighten":
            conf = max(0.2, conf - _IDENTITY_TIGHTEN_PENALTY)
        return conf

    def snapshot(self) -> dict:
        """A readable summary of the current governance state (for the API/dashboard)."""
        return {
            "global_mode": self.global_mode,
            "global_confidence": round(self.global_confidence, 3),
            "identity_actions": self.identity_actions,
            "last_forecast": self.last_forecast,
        }


# A single shared instance the whole app uses.
policy = GovernancePolicy()

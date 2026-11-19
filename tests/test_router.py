"""
test_router.py  (tests for Module 4 — the learning router)
Confirms the bandit learns to prefer the cheap tier when it's good enough, and
the expensive tier when the cheap one keeps failing.
"""

from app.router import ThompsonRouter, complexity_bucket, context_key


def test_context_key_and_buckets():
    assert complexity_bucket(0.1) == "low"
    assert complexity_bucket(0.5) == "med"
    assert complexity_bucket(0.9) == "high"
    assert context_key({"task_type": "code", "complexity": 0.9}) == "code:high"


def test_router_learns_to_prefer_cheap_when_it_succeeds():
    """If nano always meets the bar for a context, the router should learn to use it."""
    r = ThompsonRouter(quality_bar=0.7, seed=0)
    feats = {"task_type": "qa", "complexity": 0.1}
    # Teach it: nano always succeeds here.
    for _ in range(200):
        tier = r.choose(feats)
        quality = 0.95 if tier == "nano" else 0.95  # everything works; nano is cheapest
        r.update(feats, tier, quality)
    # After learning, it should pick nano (the cheapest good-enough tier) most of the time.
    picks = [r.choose(feats) for _ in range(100)]
    assert picks.count("nano") > 70


def test_router_avoids_cheap_when_it_fails():
    """If nano always fails for a hard context, the router should move up."""
    r = ThompsonRouter(quality_bar=0.7, seed=0)
    feats = {"task_type": "reasoning", "complexity": 0.95}
    for _ in range(300):
        tier = r.choose(feats)
        # nano fails hard requests; full succeeds.
        quality = {"nano": 0.3, "mid": 0.5, "full": 0.9}[tier]
        r.update(feats, tier, quality)
    picks = [r.choose(feats) for _ in range(100)]
    assert picks.count("nano") < 30  # it learned nano is a bad idea here


def test_save_and_load(tmp_path):
    r = ThompsonRouter(seed=1)
    feats = {"task_type": "qa", "complexity": 0.2}
    r.update(feats, "nano", 0.9)
    path = tmp_path / "state.json"
    r.save(str(path))
    r2 = ThompsonRouter.load(str(path))
    assert r2.beliefs == r.beliefs

"""
run_benchmark.py  — the rigorous evaluation that produces your headline number
------------------------------------------------------------------------------
Run it from the project root with:   python -m benchmark.run_benchmark

What it does (all offline, no API key, using the simulator in app/simulate.py):

  1. Generates a realistic, mixed workload of requests (different task types and
     complexities), using a FIXED random seed so results are reproducible.
  2. Runs several routing policies on the SAME requests and compares them:
        - always_full : use the most capable (most expensive) model every time
        - always_nano : use the cheapest model every time
        - random      : pick a tier at random
        - static_rules: a sensible hand-written rule (complexity -> tier)
        - LEARNING    : our Thompson-sampling router (Module 4), learning online
        - ORACLE      : the best possible choice in hindsight (upper bound)
  3. Reports, for each policy: total cost and quality pass-rate (% of requests
     meeting the quality bar), plus the learning router's savings vs always_full.
  4. Sweeps the router's confidence knob to print the cost/quality TRADE-OFF
     curve (the Pareto frontier) — this is what makes the result credible rather
     than cherry-picked.
  5. Shows a learning curve so you can SEE the router improving over time.

Why these choices matter in an interview: baselines + an oracle upper bound +
a trade-off curve + a fixed seed is exactly how you show a result is honest.
"""

import random
import statistics

from app.pricing import compute_cost
from app.router import ThompsonRouter
from app.simulate import simulate_quality, simulate_tokens
from app.tiers import TIER_ORDER, TIERS_BY_COST, tier_model

BAR = 0.70
SEED = 7
N = 6000

TASK_TYPES = ["qa", "chat", "summarization", "reasoning", "code", "extraction"]


def make_workload(n, seed):
    """A fixed, reproducible list of requests (as classifier-style feature dicts)."""
    rng = random.Random(seed)
    reqs = []
    for _ in range(n):
        task = rng.choice(TASK_TYPES)
        # Reasoning/code skew harder; qa/chat skew easier — like real traffic.
        if task in ("reasoning", "code"):
            complexity = min(1.0, rng.betavariate(5, 3))
        elif task in ("qa", "chat"):
            complexity = min(1.0, rng.betavariate(2, 5))
        else:
            complexity = rng.random()
        reqs.append({
            "task_type": task,
            "complexity": round(complexity, 3),
            "has_code": task == "code",
            "est_prompt_tokens": rng.randint(50, 400),
        })
    return reqs


def cost_for(tier, features, rng):
    toks = simulate_tokens(features, rng)
    return compute_cost(tier_model(tier), toks["prompt_tokens"], toks["completion_tokens"])


def eval_fixed_policy(choose_fn, workload, seed):
    """Run a non-learning policy (choose_fn(features)->tier) over the workload."""
    rng = random.Random(seed)
    total_cost, passes = 0.0, 0
    for f in workload:
        tier = choose_fn(f)
        q = simulate_quality(tier, f, rng)
        total_cost += cost_for(tier, f, rng)
        passes += (q >= BAR)
    return total_cost, passes / len(workload)


def static_rule(features):
    """A reasonable hand-written baseline: route by complexity."""
    c = features["complexity"]
    if c < 0.34:
        return "nano"
    if c < 0.67:
        return "mid"
    return "full"


def oracle_choice(features):
    """
    Best possible choice in hindsight: the cheapest tier whose EXPECTED quality
    clears the bar (uses the simulator's hidden skill — only possible because
    this is a simulation). This is the upper bound no real router can beat.
    """
    from app.simulate import request_difficulty
    from app.tiers import tier_skill
    d = request_difficulty(features)
    for tier in TIERS_BY_COST:  # cheapest first
        expected_q = 0.6 + (tier_skill(tier) - d) * 0.9
        if expected_q >= BAR:
            return tier
    return "full"


def eval_learning_router(workload, seed, confidence):
    """Run our Thompson-sampling router, learning online as requests arrive."""
    rng = random.Random(seed)
    r = ThompsonRouter(quality_bar=BAR, confidence=confidence, seed=seed)
    total_cost, passes = 0.0, 0
    curve = []  # (index, rolling_cost, rolling_pass) every 500 reqs
    window_cost, window_pass = 0.0, 0
    for i, f in enumerate(workload, 1):
        tier = r.choose(f)
        q = simulate_quality(tier, f, rng)
        r.update(f, tier, q)
        c = cost_for(tier, f, rng)
        total_cost += c
        passes += (q >= BAR)
        window_cost += c
        window_pass += (q >= BAR)
        if i % 500 == 0:
            curve.append((i, round(window_cost, 3), round(window_pass / 500, 3)))
            window_cost, window_pass = 0.0, 0
    return total_cost, passes / len(workload), curve, r


def main():
    print(f"TokenGovernor benchmark — {N} requests, quality bar = {BAR}, seed = {SEED}")
    print("(reproducible: same seed => same numbers)\n")

    workload = make_workload(N, SEED)

    # --- Baselines + oracle ---
    results = {}
    results["always_full"] = eval_fixed_policy(lambda f: "full", workload, SEED)
    results["always_nano"] = eval_fixed_policy(lambda f: "nano", workload, SEED)
    results["random"] = eval_fixed_policy(
        lambda f: random.Random(hash(str(f)) & 0xFFFF).choice(TIER_ORDER), workload, SEED
    )
    results["static_rules"] = eval_fixed_policy(static_rule, workload, SEED)
    results["ORACLE(best)"] = eval_fixed_policy(oracle_choice, workload, SEED)

    # --- Our learning router (default confidence 0.6) ---
    lr_cost, lr_pass, curve, trained = eval_learning_router(workload, SEED, confidence=0.6)
    results["LEARNING(ours)"] = (lr_cost, lr_pass)

    full_cost, full_pass = results["always_full"]

    print(f"{'policy':<17}{'total_cost($)':>14}{'quality_pass':>14}{'vs_full_cost':>14}")
    print("-" * 59)
    for name, (cost, qpass) in results.items():
        delta = f"{(1 - cost / full_cost) * 100:+.1f}%" if full_cost else "n/a"
        print(f"{name:<17}{cost:>14.4f}{qpass:>13.1%}{delta:>14}")

    print("\nHEADLINE (learning router vs always-full):")
    print(f"  {(1 - lr_cost / full_cost) * 100:.1f}% cheaper, "
          f"quality {lr_pass:.1%} vs {full_pass:.1%} "
          f"(within {(full_pass - lr_pass) * 100:.1f} points of the quality ceiling)")

    # --- Pareto: cost/quality trade-off as we change the confidence knob ---
    print("\nCost / quality trade-off (higher confidence = more quality, less savings):")
    print(f"  {'confidence':>10}{'cost($)':>12}{'quality':>10}{'savings_vs_full':>18}")
    for conf in (0.30, 0.45, 0.60, 0.75, 0.90):
        c, p, _, _ = eval_learning_router(workload, SEED, confidence=conf)
        print(f"  {conf:>10.2f}{c:>12.4f}{p:>9.1%}{(1 - c / full_cost) * 100:>16.1f}%")

    # --- Learning curve: router improving over time ---
    print("\nLearning curve (per 500-request window):")
    print(f"  {'after_n':>8}{'window_cost($)':>16}{'window_quality':>16}")
    for idx, wc, wp in curve:
        print(f"  {idx:>8}{wc:>16.3f}{wp:>15.1%}")

    print(f"\nOracle (best possible) cost was ${results['ORACLE(best)'][0]:.4f} "
          f"at {results['ORACLE(best)'][1]:.1%} quality — the ceiling our router approaches.")


if __name__ == "__main__":
    main()

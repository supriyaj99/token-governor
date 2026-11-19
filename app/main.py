"""
main.py  (the gateway, now wiring ALL six modules together)
-----------------------------------------------------------
Flow for each request to /v1/chat/completions:

  1. Module 2 (classifier) describes the request (task type, complexity).
  2. If the caller asked for model "auto", Module 4 (router) picks the cheapest
     tier it believes will meet the quality bar — using the confidence level the
     governance layer currently allows for this identity.
  3. We call the model. In mock mode we SIMULATE the outcome (Module simulate);
     otherwise we call the real model via LiteLLM.
  4. Module 3 (quality) scores the response (or the simulator provides quality).
  5. We log everything (cost, tokens, latency, tier, quality, identity).
  6. If we routed automatically, Module 4 LEARNS from the observed quality.

Governance endpoints:
  GET /governance  -> run Module 5 (forecast + controller) and Module 6
                      (value-weighted fairness) over the logged data, APPLY the
                      decisions to the live policy, and return them.
  GET /forecast    -> just the budget forecast.
  GET /router      -> what the router has learned so far.
"""

import os
import time
from collections import defaultdict

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import config
from app.classifier import classify
from app.database import get_db, init_db
from app.fairness import compute_identity_policies
from app.forecaster import decide_control_mode, forecast_exhaustion
from app.llm_client import call_model
from app.models import RequestLog
from app.policy import policy
from app.pricing import compute_cost
from app.quality import estimate_quality
from app.router import ThompsonRouter
from app.schemas import ChatRequest, ChatResponse
from app.simulate import simulate_quality, simulate_tokens
from app.tiers import TIERS, tier_model

app = FastAPI(title="TokenGovernor Gateway", version="1.0.0 (Modules 1-6)")

# The single, shared, learning router for the whole app. Loaded from disk so it
# remembers what it learned across restarts.
router = ThompsonRouter.load(config.BANDIT_STATE_PATH)
router.quality_bar = config.QUALITY_BAR

# Reverse lookup: given a concrete model name, which tier is it? Used when a
# caller asks for a specific model in simulation mode.
_MODEL_TO_TIER = {info["model"]: tier for tier, info in TIERS.items()}

# Save the router's learning to disk every N auto-routed requests.
_SAVE_EVERY = 25
_auto_counter = 0


@app.on_event("startup")
def _startup() -> None:
    init_db()


# Serve the web UI. The folder app/static holds index.html; we expose it at the
# root URL so visiting http://localhost:8000/ shows the dashboard/front-end.
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/")
def home() -> FileResponse:
    """The front-end: a single polished page served by the gateway itself."""
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mock_mode": config.MOCK_MODE, "simulate": config.SIMULATE}


@app.post("/v1/chat/completions", response_model=ChatResponse)
def chat_completions(req: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    global _auto_counter
    identity = req.identity or "anonymous"
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    # Module 2: classify before doing anything expensive.
    features = classify(messages)

    # Module 4: decide which model to use.
    routed_tier = None
    if req.model.lower() == "auto":
        # Governance (Modules 5 & 6) sets how cheap we're allowed to lean today.
        router.confidence = policy.effective_confidence(identity)
        routed_tier = router.choose(features)
        model_name = tier_model(routed_tier)
    else:
        model_name = req.model
        routed_tier = _MODEL_TO_TIER.get(model_name)  # may be None for unknown

    # Steps 3 & 4: get the response + quality, either simulated or real.
    start = time.perf_counter()
    status = "ok"
    error_text = None

    if config.SIMULATE:
        # Offline path: no API call. Simulate tokens and quality so the whole
        # system produces meaningful numbers for free.
        sim_tier = routed_tier or "full"
        toks = simulate_tokens(features)
        prompt_tokens = toks["prompt_tokens"]
        completion_tokens = toks["completion_tokens"]
        quality_score = round(simulate_quality(sim_tier, features), 3)
        content = f"[SIMULATED {sim_tier} response] (quality={quality_score})"
    else:
        # Real path: call the model and score the reply with Module 3.
        try:
            result = call_model(model_name, messages)
            content = result["content"]
            prompt_tokens = result["prompt_tokens"]
            completion_tokens = result["completion_tokens"]
            prompt_text = " ".join(m["content"] for m in messages)
            quality_score = estimate_quality(
                prompt_text, content, task_type=features["task_type"], status="ok"
            )["score"]
        except Exception as exc:
            status = "error"
            error_text = str(exc)
            content, prompt_tokens, completion_tokens, quality_score = "", 0, 0, 0.0

    latency_ms = (time.perf_counter() - start) * 1000.0
    total_tokens = prompt_tokens + completion_tokens
    cost_usd = compute_cost(model_name, prompt_tokens, completion_tokens)

    # Step 5: record the row.
    log = RequestLog(
        identity=identity,
        model=model_name,
        routed_tier=routed_tier,
        task_type=features["task_type"],
        complexity=features["complexity"],
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_usd=cost_usd,
        quality=quality_score,
        latency_ms=latency_ms,
        status=status,
        error=error_text,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    # Step 6: if we routed automatically, LEARN from what happened.
    if req.model.lower() == "auto" and status == "ok":
        router.update(features, routed_tier, quality_score)
        _auto_counter += 1
        if _auto_counter % _SAVE_EVERY == 0:
            router.save(config.BANDIT_STATE_PATH)

    return ChatResponse(
        id=log.id,
        model=model_name,
        content=content,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_usd=cost_usd,
        quality=quality_score,
        latency_ms=round(latency_ms, 2),
        status=status,
    )


@app.get("/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    row = db.query(
        func.count(RequestLog.id),
        func.coalesce(func.sum(RequestLog.total_tokens), 0),
        func.coalesce(func.sum(RequestLog.cost_usd), 0.0),
        func.coalesce(func.avg(RequestLog.latency_ms), 0.0),
        func.coalesce(func.avg(RequestLog.quality), 0.0),
    ).one()
    n, tokens, cost, lat, qual = row
    return {
        "total_requests": int(n),
        "total_tokens": int(tokens),
        "total_cost_usd": round(float(cost), 6),
        "avg_latency_ms": round(float(lat), 2),
        "avg_quality": round(float(qual), 3),
        "budget_usd": config.BUDGET_USD,
        "budget_remaining_usd": round(config.BUDGET_USD - float(cost), 6),
    }


@app.get("/logs")
def logs(limit: int = 20, db: Session = Depends(get_db)) -> dict:
    rows = (
        db.query(RequestLog).order_by(RequestLog.created_at.desc()).limit(limit).all()
    )
    return {"count": len(rows), "logs": [r.as_dict() for r in rows]}


def _daily_spend(db: Session) -> list:
    """Total spend grouped by calendar day, oldest first (for the forecaster)."""
    rows = db.query(RequestLog.created_at, RequestLog.cost_usd).all()
    by_day = defaultdict(float)
    for created_at, cost in rows:
        day = created_at.date() if created_at else None
        if day is not None:
            by_day[day] += float(cost or 0.0)
    return [by_day[d] for d in sorted(by_day.keys())]


def _per_identity(db: Session, bar: float) -> dict:
    """Spend / successes / requests per identity (for the fairness layer)."""
    rows = db.query(
        RequestLog.identity, RequestLog.cost_usd, RequestLog.quality
    ).all()
    agg = defaultdict(lambda: {"spend": 0.0, "successes": 0, "requests": 0})
    for ident, cost, qual in rows:
        a = agg[ident]
        a["spend"] += float(cost or 0.0)
        a["requests"] += 1
        if (qual or 0.0) >= bar:
            a["successes"] += 1
    return dict(agg)


@app.get("/forecast")
def forecast(db: Session = Depends(get_db)) -> dict:
    """Module 5: predict budget exhaustion from the spend trend."""
    daily = _daily_spend(db)
    fc = forecast_exhaustion(daily, config.BUDGET_USD, config.PERIOD_DAYS)
    fc["control"] = decide_control_mode(fc)
    return fc


@app.get("/governance")
def governance(db: Session = Depends(get_db)) -> dict:
    """
    Run the whole closed loop: forecast (Module 5) + value-weighted fairness
    (Module 6), APPLY the decisions to the live routing policy, and return them.
    This is the endpoint that makes the system 'govern itself'.
    """
    # --- Module 5: forecast + controller ---
    daily = _daily_spend(db)
    fc = forecast_exhaustion(daily, config.BUDGET_USD, config.PERIOD_DAYS)
    control = decide_control_mode(fc)
    policy.set_global_mode(control["mode"])
    policy.last_forecast = fc

    # --- Module 6: value-weighted fairness ---
    per_id = _per_identity(db, config.QUALITY_BAR)
    days_elapsed = max(len(daily), 1)
    period_fraction = min(days_elapsed / config.PERIOD_DAYS, 1.0)
    id_policies = compute_identity_policies(
        per_id, config.BUDGET_USD, period_fraction
    )
    policy.set_identity_actions(id_policies)

    return {
        "forecast": fc,
        "control": control,
        "identity_policies": id_policies,
        "applied_policy": policy.snapshot(),
    }


@app.get("/router")
def router_state() -> dict:
    """Module 4: a readable summary of what the router has learned per context."""
    summary = {}
    for ctx, arms in router.beliefs.items():
        summary[ctx] = {
            tier: {
                "successes": int(a - 1),
                "failures": int(b - 1),
                "est_meets_bar": round(a / (a + b), 3),
            }
            for tier, (a, b) in arms.items()
        }
    return {"quality_bar": router.quality_bar, "confidence": router.confidence, "learned": summary}

"""
models.py
---------
This file describes the SHAPE of our data — i.e. the columns in our database
table — as a Python class. SQLAlchemy reads this class and creates a matching
table called 'request_logs'.

Module 1 is purely a "recording layer": every request that passes through the
gateway becomes one row in this table. Later modules (classifier, router,
forecaster) will READ these rows to make decisions. So getting this record
right is the foundation for the whole project.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.database import Base


def _uuid() -> str:
    """Generate a random unique id as text, e.g. '3f2c...'. Used as the row id."""
    return str(uuid.uuid4())


def _now() -> datetime:
    """Current time in UTC. We always store time in UTC to avoid timezone bugs."""
    return datetime.now(timezone.utc)


class RequestLog(Base):
    """One row = one AI request that passed through the gateway."""

    __tablename__ = "request_logs"

    # A unique id for this log row.
    id = Column(String, primary_key=True, default=_uuid)

    # WHEN the request happened. This is the "time" column Timescale organizes by.
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False, index=True)

    # WHO made the request (a user id, team, or project name). This single field
    # is what makes the future Module 6 (per-identity fairness) possible, so we
    # capture it from the very start even though Module 1 doesn't use it yet.
    identity = Column(String, nullable=False, default="anonymous", index=True)

    # WHICH model was used, e.g. 'gpt-4o-mini' or 'mock-echo'.
    model = Column(String, nullable=False, index=True)

    # WHICH tier the router chose ('nano'/'mid'/'full'), when routing was 'auto'.
    # Null if the caller asked for a specific model instead of letting us route.
    routed_tier = Column(String, nullable=True, index=True)

    # Filled in by the classifier (Module 2): the kind of task, e.g. 'code',
    # 'qa', 'reasoning', and a 0..1 complexity score. The router (Module 4)
    # reads these to decide which model is cheap enough for this request.
    task_type = Column(String, nullable=True, index=True)
    complexity = Column(Float, nullable=True)

    # HOW MANY tokens were used. "Tokens" are the chunks of text an AI model
    # reads and writes; you pay per token. Input = the prompt you sent,
    # output = the model's reply.
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)

    # HOW MUCH it cost, in US dollars, computed from tokens and the model's price.
    cost_usd = Column(Float, nullable=False, default=0.0)

    # Cheap quality score (0..1) from Module 3. This is the signal the router
    # uses to judge whether a cheaper model was "good enough".
    quality = Column(Float, nullable=True)

    # HOW LONG the model call took, in milliseconds (1000 ms = 1 second).
    latency_ms = Column(Float, nullable=False, default=0.0)

    # Did it succeed? 'ok' or 'error'.
    status = Column(String, nullable=False, default="ok")

    # If it failed, the error message goes here (otherwise null).
    error = Column(Text, nullable=True)

    def as_dict(self) -> dict:
        """Convert the row into a plain dictionary so we can return it as JSON."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "identity": self.identity,
            "model": self.model,
            "routed_tier": self.routed_tier,
            "task_type": self.task_type,
            "complexity": self.complexity,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "quality": self.quality,
            "latency_ms": round(self.latency_ms, 2),
            "status": self.status,
            "error": self.error,
        }

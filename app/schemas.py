"""
schemas.py
----------
"Schemas" describe the shape of the JSON that comes IN to our API and goes OUT.

We use Pydantic, a library that checks incoming data automatically. If someone
sends a request missing a required field, Pydantic rejects it with a clear
error before our code even runs — so we never deal with half-formed data.

JSON is just text in the form {"key": "value"} — the universal way programs
send structured data to each other over the web.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """One message in a conversation, e.g. {"role": "user", "content": "Hi"}."""

    role: str = Field(..., description="Who is speaking: 'system', 'user', or 'assistant'.")
    content: str = Field(..., description="The text of the message.")


class ChatRequest(BaseModel):
    """
    The body a client sends to our gateway. It mirrors the shape used by
    OpenAI/Anthropic-style APIs, so existing tools can point at our gateway
    with almost no changes.
    """

    model: str = Field(..., description="Which model to use, e.g. 'gpt-4o-mini'.")
    messages: List[ChatMessage] = Field(..., description="The conversation so far.")
    # Optional: who is making this request. Defaults to 'anonymous' if omitted.
    identity: Optional[str] = Field(
        default="anonymous",
        description="User/team/project id — used later for per-identity budgeting.",
    )


class ChatResponse(BaseModel):
    """What our gateway sends back: the model's reply plus the usage/cost we logged."""

    id: str
    model: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    quality: float
    latency_ms: float
    status: str

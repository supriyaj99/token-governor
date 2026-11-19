"""
test_gateway.py
---------------
Automated tests for Module 1.

"Testing" means: we run the app in a fake, throwaway way and check it behaves
correctly, WITHOUT needing a real server or database. If any check fails, the
test turns red and tells us exactly what broke. In an interview, "I wrote tests"
is a strong signal — it shows you can prove your code works, not just hope so.

We use:
- pytest: the tool that finds and runs test functions (any function named test_*).
- FastAPI's TestClient: a fake browser that calls our endpoints in-memory.
- A temporary SQLite database file, deleted after the test, so tests never
  touch your real data.
"""

import os

# IMPORTANT: set config BEFORE importing the app, because config reads these
# environment variables at import time. We force mock mode (no API key) and a
# local throwaway SQLite database.
os.environ["MOCK_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./test_tokengov.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402

# Make sure the table exists before we start hitting the API.
init_db()
client = TestClient(app)


def test_health():
    """The /health endpoint should return status ok and confirm mock mode."""
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["mock_mode"] is True


def test_chat_completion_records_a_log():
    """
    Sending a chat request should:
      - succeed (HTTP 200)
      - come back with a mock reply and non-zero token counts
      - actually create a row we can see via /logs
    """
    payload = {
        "model": "gpt-4o-mini",
        "identity": "riya",
        "messages": [{"role": "user", "content": "Explain what a token is in one sentence."}],
    }
    r = client.post("/v1/chat/completions", json=payload)
    assert r.status_code == 200

    body = r.json()
    assert body["status"] == "ok"
    assert "[MOCK RESPONSE]" in body["content"]
    assert body["prompt_tokens"] > 0
    assert body["completion_tokens"] > 0
    assert body["total_tokens"] == body["prompt_tokens"] + body["completion_tokens"]
    # gpt-4o-mini has a real (non-zero) price, so cost should be > 0.
    assert body["cost_usd"] > 0

    # The request should now appear in the logs.
    logs = client.get("/logs").json()
    assert logs["count"] >= 1
    assert logs["logs"][0]["identity"] == "riya"


def test_stats_accumulate():
    """After at least one request, /stats should report totals greater than zero."""
    s = client.get("/stats").json()
    assert s["total_requests"] >= 1
    assert s["total_tokens"] > 0
    assert s["total_cost_usd"] >= 0

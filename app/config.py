"""
config.py
---------
Central place for all the settings the app needs to run.

Instead of scattering values like the database address or "are we in mock
mode?" all over the code, we read them ONCE here from environment variables
(with sensible defaults) and let the rest of the app import them from here.

An "environment variable" is just a named value that lives outside your code —
in your terminal or in a .env file — so you can change how the app behaves
without editing Python. That's how real production apps are configured.
"""

import os

from dotenv import load_dotenv

# Look for a file named ".env" in the project folder and load any values from
# it into the environment. This lets you keep secrets/settings out of the code.
load_dotenv()


def _as_bool(value: str) -> bool:
    """Turn a text value like 'true'/'1'/'yes' into a real True/False."""
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


# Where the database lives. Default points at the Postgres container that
# docker-compose starts for you. When testing locally without Docker, we
# override this with a simple file-based SQLite database instead.
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://tokengov:tokengov@localhost:5432/tokengov",
)

# When MOCK_MODE is on, the gateway does NOT call a real AI model or need any
# API key. It returns a canned response instead. This lets you build and test
# the whole recording pipeline for free before touching a paid API.
MOCK_MODE: bool = _as_bool(os.getenv("MOCK_MODE", "true"))

# The port the web server listens on. 8000 is a common default.
APP_PORT: int = int(os.getenv("APP_PORT", "8000"))

# --- Governance settings (Modules 5 & 6) ---
# The total budget for the current period, in US dollars, and how many days the
# period lasts. The forecaster checks spend against these.
BUDGET_USD: float = float(os.getenv("BUDGET_USD", "50"))
PERIOD_DAYS: int = int(os.getenv("PERIOD_DAYS", "30"))

# The quality bar: a response scoring at or above this counts as "good enough".
QUALITY_BAR: float = float(os.getenv("QUALITY_BAR", "0.7"))

# In mock mode we also SIMULATE quality/tokens (see simulate.py) so the router,
# forecaster, and benchmark produce meaningful numbers with no API key.
SIMULATE: bool = MOCK_MODE

# Where the router saves what it has learned, so it survives restarts.
BANDIT_STATE_PATH: str = os.getenv("BANDIT_STATE_PATH", "bandit_state.json")

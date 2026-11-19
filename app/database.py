"""
database.py
-----------
Everything about *connecting* to the database lives here.

Key ideas in plain words:
- "engine": the actual connection to the database. Think of it as the pipe
  between your Python code and Postgres.
- "session": one short conversation with the database (open it, do some
  reads/writes, close it). We open a fresh session per web request.
- We use SQLAlchemy, a library that lets us describe tables as Python classes
  and talk to the database without writing raw SQL by hand.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

# SQLite (the local test database) needs one special flag so it can be used
# from a web server that handles more than one request at a time. Postgres
# does not need this. We detect which one we're using and adjust.
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# The engine is created once and reused for the life of the app.
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)

# A factory that hands out new database sessions when we ask for one.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Base is the parent class every table model inherits from. SQLAlchemy uses it
# to keep track of all our tables so it can create them.
Base = declarative_base()


def get_db():
    """
    FastAPI calls this for each request to get a database session, and
    automatically closes it when the request is done. This 'open then always
    close' pattern prevents leaking connections.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Create our table(s) if they don't already exist.

    If we're on Postgres AND the TimescaleDB extension is available, we also
    turn the log table into a 'hypertable' — a Timescale feature that makes
    time-based data (like a stream of request logs) much faster to store and
    query. If Timescale isn't there (e.g. plain Postgres or SQLite during
    testing), we simply skip that step and everything still works.
    """
    # Import here (not at the top) to avoid a circular import: models.py needs
    # Base from this file, and this file needs the models to create them.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    if DATABASE_URL.startswith("postgresql"):
        with engine.begin() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb;"))
                # create_hypertable is safe to call repeatedly thanks to
                # if_not_exists => true. migrate_data moves any existing rows.
                conn.execute(
                    text(
                        "SELECT create_hypertable('request_logs', 'created_at', "
                        "if_not_exists => TRUE, migrate_data => TRUE);"
                    )
                )
            except Exception:
                # No Timescale available — that's fine, plain Postgres works.
                pass

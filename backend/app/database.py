import os
import time

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://uptime:uptime@localhost:5432/uptime"
)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# pool_pre_ping recycles dead connections (e.g. after Postgres restarts) so the
# scheduler doesn't blow up on a stale socket between checks.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_db(max_retries: int = 15, delay: float = 2.0) -> None:
    """Block until Postgres accepts connections.

    depends_on: service_healthy handles most of this, but the app can still
    win the race on a cold start, so we retry the first connection ourselves.
    """
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect():
                return
        except OperationalError:
            if attempt == max_retries:
                raise
            time.sleep(delay)

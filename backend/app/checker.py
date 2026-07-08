import logging
import time
from datetime import datetime
from typing import Optional, Tuple

import httpx

from .database import SessionLocal
from . import models

logger = logging.getLogger("uptime.checker")

REQUEST_TIMEOUT_SECONDS = 10.0


def check_one(client: httpx.Client, url: str) -> Tuple[Optional[int], float, bool]:
    """Ping a single URL and return (status_code, response_time_ms, is_up).

    We measure latency with perf_counter around the request so that failures
    (which have no HTTP response) still get a meaningful "time to failure".
    A URL is considered UP when it responds with a status code < 400.
    """
    start = time.perf_counter()
    try:
        resp = client.get(url, follow_redirects=True, timeout=REQUEST_TIMEOUT_SECONDS)
        elapsed_ms = (time.perf_counter() - start) * 1000
        is_up = resp.status_code < 400
        return resp.status_code, round(elapsed_ms, 2), is_up
    except httpx.RequestError as exc:
        # DNS failure, connection refused, timeout, TLS error, etc.
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info("check failed for %s: %s", url, exc.__class__.__name__)
        return None, round(elapsed_ms, 2), False


def run_checks() -> None:
    """Ping every registered URL once and persist a health_check row for each.

    Runs inside the scheduler thread, so it opens and closes its own DB
    session rather than borrowing a request-scoped one.
    """
    db = SessionLocal()
    try:
        urls = db.query(models.URL).all()
        if not urls:
            return

        with httpx.Client() as client:
            for u in urls:
                status_code, response_time_ms, is_up = check_one(client, u.url)
                db.add(
                    models.HealthCheck(
                        url_id=u.id,
                        status_code=status_code,
                        response_time_ms=response_time_ms,
                        is_up=is_up,
                        checked_at=datetime.utcnow(),
                    )
                )
        db.commit()
        logger.info("ran health checks for %d url(s)", len(urls))
    finally:
        db.close()

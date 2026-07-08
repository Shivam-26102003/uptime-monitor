import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from .checker import run_checks

logger = logging.getLogger("uptime.scheduler")

# BackgroundScheduler (thread-based, not asyncio) so the sync httpx.Client and
# sync SQLAlchemy session in run_checks() run cleanly off the FastAPI event loop.
scheduler = BackgroundScheduler()


def start_scheduler(interval_seconds: int = 60) -> None:
    scheduler.add_job(
        run_checks,
        trigger="interval",
        seconds=interval_seconds,
        id="health_checks",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        # Fire once immediately so the dashboard isn't blank for the first minute.
        next_run_time=datetime.utcnow(),
    )
    scheduler.start()
    logger.info("scheduler started (interval=%ss)", interval_seconds)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)

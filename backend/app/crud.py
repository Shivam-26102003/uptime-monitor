from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import models, schemas


def create_url(db: Session, url: str) -> models.URL:
    obj = models.URL(url=url)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_url_by_value(db: Session, url: str) -> Optional[models.URL]:
    return db.query(models.URL).filter(models.URL.url == url).first()


def get_url(db: Session, url_id: int) -> Optional[models.URL]:
    return db.query(models.URL).filter(models.URL.id == url_id).first()


def list_urls(db: Session) -> List[models.URL]:
    return db.query(models.URL).order_by(models.URL.created_at.desc()).all()


def delete_url(db: Session, url: models.URL) -> None:
    db.delete(url)
    db.commit()


def get_history(db: Session, url_id: int, limit: int = 50) -> List[models.HealthCheck]:
    return (
        db.query(models.HealthCheck)
        .filter(models.HealthCheck.url_id == url_id)
        .order_by(models.HealthCheck.checked_at.desc())
        .limit(limit)
        .all()
    )


def get_latest_status(db: Session) -> List[schemas.URLStatus]:
    """Return each URL joined with its most recent health check.

    Uses a correlated subquery to pick the max(checked_at) per url_id, then
    joins that back to the health_checks row. Fine for the assignment's scale
    (a few dozen URLs); would swap for a window function at larger scale.
    """
    latest_sub = (
        db.query(
            models.HealthCheck.url_id,
            func.max(models.HealthCheck.checked_at).label("max_checked"),
        )
        .group_by(models.HealthCheck.url_id)
        .subquery()
    )

    rows = (
        db.query(models.URL, models.HealthCheck)
        .outerjoin(latest_sub, latest_sub.c.url_id == models.URL.id)
        .outerjoin(
            models.HealthCheck,
            (models.HealthCheck.url_id == latest_sub.c.url_id)
            & (models.HealthCheck.checked_at == latest_sub.c.max_checked),
        )
        .order_by(models.URL.created_at.desc())
        .all()
    )

    result: List[schemas.URLStatus] = []
    for url_obj, check in rows:
        result.append(
            schemas.URLStatus(
                id=url_obj.id,
                url=url_obj.url,
                is_up=check.is_up if check else None,
                status_code=check.status_code if check else None,
                response_time_ms=check.response_time_ms if check else None,
                last_checked=check.checked_at if check else None,
            )
        )
    return result

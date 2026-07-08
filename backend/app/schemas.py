from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


class URLCreate(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def normalize_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("url must not be empty")
        # Be lenient: accept "example.com" and default to https.
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v


class URLOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    created_at: datetime


class HealthCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status_code: Optional[int]
    response_time_ms: Optional[float]
    is_up: bool
    checked_at: datetime


class URLStatus(BaseModel):
    """Latest known state of a single monitored URL (for the dashboard)."""

    id: int
    url: str
    is_up: Optional[bool] = None
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    last_checked: Optional[datetime] = None

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from .database import Base


class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    checks = relationship(
        "HealthCheck",
        back_populates="url_ref",
        cascade="all, delete-orphan",
    )


class HealthCheck(Base):
    __tablename__ = "health_checks"

    id = Column(Integer, primary_key=True, index=True)
    url_id = Column(
        Integer, ForeignKey("urls.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # status_code / response_time are nullable: a connection failure (DNS,
    # timeout, refused) has no HTTP status but is still a recorded "down" check.
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    is_up = Column(Boolean, default=False, nullable=False)
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)

    url_ref = relationship("URL", back_populates="checks")

import logging
import os
from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .checker import run_checks
from .database import engine, get_db, wait_for_db
from .scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)

CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_db()
    models.Base.metadata.create_all(bind=engine)
    start_scheduler(interval_seconds=CHECK_INTERVAL_SECONDS)
    yield
    stop_scheduler()


app = FastAPI(title="Uptime Monitor", version="1.0.0", lifespan=lifespan)

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = (
    [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
    if allowed_origins_env != "*"
    else ["*"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True if allowed_origins != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi import APIRouter, Depends, FastAPI, HTTPException

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/urls", response_model=schemas.URLOut, status_code=201)
def register_url(payload: schemas.URLCreate, db: Session = Depends(get_db)):
    existing = crud.get_url_by_value(db, payload.url)
    if existing:
        raise HTTPException(status_code=409, detail="URL already registered")
    return crud.create_url(db, payload.url)


@router.get("/urls", response_model=List[schemas.URLOut])
def list_urls(db: Session = Depends(get_db)):
    return crud.list_urls(db)


@router.delete("/urls/{url_id}", status_code=204)
def delete_url(url_id: int, db: Session = Depends(get_db)):
    url = crud.get_url(db, url_id)
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    crud.delete_url(db, url)


@router.get("/status", response_model=List[schemas.URLStatus])
def status(db: Session = Depends(get_db)):
    return crud.get_latest_status(db)


@router.get("/history/{url_id}", response_model=List[schemas.HealthCheckOut])
def history(url_id: int, db: Session = Depends(get_db)):
    url = crud.get_url(db, url_id)
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    return crud.get_history(db, url_id)


@router.post("/check-now", status_code=202)
def check_now():
    """Trigger an immediate round of checks (handy for demoing up/down flips)."""
    run_checks()
    return {"status": "checks triggered"}


app.include_router(router)
app.include_router(router, prefix="/api")


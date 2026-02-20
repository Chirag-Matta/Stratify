# api/routes.py

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import os
from db.models import create_tables
from services.segment_svc import SegmentService
from services.experiment_svc import ExperimentService

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

SessionLocal = create_tables(DATABASE_URL)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/segments")
def create_segment(payload: dict, db: Session = Depends(get_db)):
    service = SegmentService(db)
    return service.create_segment(
        payload["name"],
        payload.get("description"),
        payload["rules"]
    )


@app.post("/experiments")
def create_experiment(payload: dict, db: Session = Depends(get_db)):
    service = ExperimentService(db)
    return service.create_experiment(
        payload["name"],
        payload["variants"],
        payload["segment_ids"]
    )


@app.get("/users/{user_id}/experiments")
def get_user_experiments(user_id: str, db: Session = Depends(get_db)):
    seg_service = SegmentService(db)
    seg_service.refresh_user_segments(user_id)

    exp_service = ExperimentService(db)
    experiments = exp_service.get_user_experiments(user_id)

    return {
        "user_id": user_id,
        "experiments": experiments
    }
# api/routes.py

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import os
from db.models import create_tables
from services.segment_svc import SegmentService
from services.experiment_svc import ExperimentService
from dotenv import load_dotenv
from db.models import Order
from services.producer import publish_event
from services.cache import get_user_experiments_cache, set_user_experiments_cache
from db.models import User, Order

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

SessionLocal = create_tables(DATABASE_URL)

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/users")
def register_user(payload: dict, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.user_id == payload["user_id"]).first()
    if existing:
        return {"status": "already_exists", "user_id": payload["user_id"]}
    
    user = User(user_id=payload["user_id"])
    db.add(user)
    db.commit()
    return {"status": "registered", "user_id": payload["user_id"]}

@app.get("/users/{user_id}/experiments")
def get_user_experiments(user_id: str, db: Session = Depends(get_db)):
    # check cache first
    cached = get_user_experiments_cache(user_id)
    if cached is not None:
        return {"user_id": user_id, "experiments": cached, "source": "cache"}

    # cache miss — compute from Postgres
    seg_service = SegmentService(db)
    seg_service.refresh_user_segments(user_id)

    exp_service = ExperimentService(db)
    experiments = exp_service.get_user_experiments(user_id)

    # store in cache
    set_user_experiments_cache(user_id, experiments)

    return {"user_id": user_id, "experiments": experiments, "source": "db"}




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
        payload["segmentIDs"]
    )

@app.post("/orders")
def place_order(payload: dict, db: Session = Depends(get_db)):
    order = Order(
        user_id=payload["user_id"],
        amount=payload["amount"],
        city=payload.get("city")
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # publish event to kafka
    publish_event("order_placed", {
        "user_id": payload["user_id"],
        "orderID": order.orderID,
        "amount": payload["amount"],
        "city": payload.get("city")
    })

    return {"orderID": order.orderID, "status": "placed"}

# @app.get("/users/{user_id}/experiments")
# def get_user_experiments(user_id: str, db: Session = Depends(get_db)):
#     seg_service = SegmentService(db)
#     seg_service.refresh_user_segments(user_id)

#     exp_service = ExperimentService(db)
#     experiments = exp_service.get_user_experiments(user_id)

#     return {
#         "user_id": user_id,
#         "experiments": experiments
#     }
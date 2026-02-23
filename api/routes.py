# api/routes.py

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import os
from db.models import create_tables
from services.segment_svc import SegmentService
from services.experiment_svc import ExperimentService
from services.banner_mixture import invalidate_banner_mixture  # NEW IMPORT
from dotenv import load_dotenv
from db.models import Order, User
from services.producer import publish_event
from services.cache import get_user_experiments_cache, set_user_experiments_cache, invalidate_user_cache

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
    exp_service = ExperimentService(db)
    seg_service = SegmentService(db)

    # Cache check
    cached = get_user_experiments_cache(user_id)
    if cached is not None:
        banner_mixture = exp_service.generate_user_banner_mixture(user_id)
        response = {"user_id": user_id, "experiments": cached, "source": "cache"}
        if banner_mixture:
            response["banner_mixture"] = banner_mixture
        return response

    # If Cache miss — only refresh segments if this user
    # has never had segments computed (e.g. brand new user)
    # For all other users, trust that the consumer/cron keeps segments fresh
    if not seg_service.has_segment_memberships(user_id):
        seg_service.refresh_user_segments(user_id)

    experiments = exp_service.get_user_experiments(user_id)
    banner_mixture = exp_service.generate_user_banner_mixture(user_id)

    set_user_experiments_cache(user_id, experiments)

    response = {"user_id": user_id, "experiments": experiments, "source": "db"}
    if banner_mixture:
        response["banner_mixture"] = banner_mixture
    return response



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

    # Invalidate caches on new order
    invalidate_user_cache(payload["user_id"])
    invalidate_banner_mixture(payload["user_id"])  # NEW

    # publish event to kafka
    publish_event("order_placed", {
        "user_id": payload["user_id"],
        "orderID": order.orderID,
        "amount": payload["amount"],
        "city": payload.get("city")
    })

    
    return {"orderID": order.orderID, "status": "placed"}


# NEW ENDPOINT: Direct banner mixture access (optional, for debugging)
@app.get("/users/{user_id}/banner_mixture")
def get_banner_mixture(user_id: str, db: Session = Depends(get_db)):
    """Get current banner mixture for user."""
    exp_service = ExperimentService(db)
    mixture = exp_service.generate_user_banner_mixture(user_id)
    
    if mixture is None:
        return {"user_id": user_id, "banner_mixture": None, "message": "No banner experiments for user"}
    
    return {
        "user_id": user_id,
        "banner_mixture": mixture
    }


# NEW ENDPOINT: Manual cache invalidation (admin)
@app.delete("/users/{user_id}/cache")
def invalidate_user_caches(user_id: str):
    """Manually clear experiment and banner mixture caches for a user."""
    invalidate_user_cache(user_id)
    invalidate_banner_mixture(user_id)
    
    return {
        "status": "invalidated",
        "user_id": user_id,
        "caches_cleared": ["experiments", "banner_mixture"]
    }


# Keeping old commented endpoint for reference
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
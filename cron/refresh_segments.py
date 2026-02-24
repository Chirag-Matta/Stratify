import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timedelta
from sqlalchemy import func, text
from db.models import create_tables, Order
from services.segment_svc import SegmentService
from services.cache import invalidate_user_cache
from services.banner_mixture import invalidate_banner_mixture  # NEW IMPORT

SessionLocal = create_tables(os.getenv("DATABASE_URL"))

def get_potentially_dormant_users(db):
    cutoff = datetime.utcnow() - timedelta(days=14)

    # users who have orders but none in the last 14 days
    active_recently = db.query(Order.user_id)\
        .filter(Order.created_at >= cutoff)\
        .distinct()

    dormant = db.query(Order.user_id)\
        .filter(Order.created_at < cutoff)\
        .filter(Order.user_id.notin_(active_recently))\
        .distinct()\
        .all()

    return [row.user_id for row in dormant]

def run():
    print(f"[Cron] Starting segment refresh at {datetime.utcnow()}")
    db = SessionLocal()

    try:
        user_ids = get_potentially_dormant_users(db)
        print(f"[Cron] Found {len(user_ids)} users to re-evaluate")

        for user_id in user_ids:
            try:
                service = SegmentService(db)
                matched = service.refresh_user_segments(user_id)
                
                # Invalidate both caches
                invalidate_user_cache(user_id)
                invalidate_banner_mixture(user_id)  # NEW
                
                print(f"[Cron] Refreshed user {user_id} → segments: {matched}")
            except Exception as e:
                print(f"[Cron] Error for user {user_id}: {e}")

    finally:
        db.close()

    print(f"[Cron] Done at {datetime.utcnow()}")

if __name__ == "__main__":
    run()
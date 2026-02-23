import os
from datetime import datetime
from db.models import create_tables, Order
from services.segment_svc import SegmentService
from services.cache import invalidate_user_cache
from services.banner_mixture import invalidate_banner_mixture

SessionLocal = create_tables(os.getenv("DATABASE_URL"))


def check_user_dormancy(user_id: str, order_placed_at: str):
    """
    Fired by APScheduler exactly 14 days after an order.
    Checks if user has ordered since — if not, refreshes segments.
    """
    print(f"[Dormancy] Checking {user_id} — original order at {order_placed_at}")

    db = SessionLocal()
    try:
        original_order_time = datetime.fromisoformat(order_placed_at)

        # Has user placed any order after the one that scheduled this check?
        subsequent_order = db.query(Order)\
            .filter(Order.user_id == user_id)\
            .filter(Order.created_at > original_order_time)\
            .first()

        if subsequent_order:
            print(f"[Dormancy] {user_id} is active — skipping")
            return

        print(f"[Dormancy] {user_id} is dormant — refreshing segments")
        seg_service = SegmentService(db)
        matched = seg_service.refresh_user_segments(user_id)

        invalidate_user_cache(user_id)
        invalidate_banner_mixture(user_id)

        print(f"[Dormancy] {user_id} segments updated → {matched}")

    except Exception as e:
        print(f"[Dormancy] Error for {user_id}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
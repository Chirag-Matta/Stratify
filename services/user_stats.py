from datetime import datetime, timedelta
from sqlalchemy import func
from db.models import Order


class UserStatsService:
    def __init__(self, db):
        self.db = db

    def get_stats(self, user_id: str) -> dict:
        now = datetime.utcnow()

        # Total orders ever
        total_orders = self.db.query(func.count(Order.orderID))\
            .filter(Order.user_id == user_id)\
            .scalar() or 0

        # Orders in last 15 days
        cutoff_15 = now - timedelta(days=15)
        orders_last_15 = self.db.query(func.count(Order.orderID))\
            .filter(Order.user_id == user_id, Order.created_at >= cutoff_15)\
            .scalar() or 0

        # Orders in last 23 days
        cutoff_23 = now - timedelta(days=23)
        orders_last_23 = self.db.query(func.count(Order.orderID))\
            .filter(Order.user_id == user_id, Order.created_at >= cutoff_23)\
            .scalar() or 0

        # Orders in last 12 days
        cutoff_12 = now - timedelta(days=12)
        orders_last_12 = self.db.query(func.count(Order.orderID))\
            .filter(Order.user_id == user_id, Order.created_at >= cutoff_12)\
            .scalar() or 0

        # Lifetime value (sum of all order amounts)
        ltv = self.db.query(func.sum(Order.amount))\
            .filter(Order.user_id == user_id)\
            .scalar() or 0

        # Last order date (for dormancy check)
        last_order = self.db.query(func.max(Order.created_at))\
            .filter(Order.user_id == user_id)\
            .scalar()

        # days_since_last_order = (now - last_order).days if last_order else 9999

        seconds_since_last_order = (now - last_order).total_seconds() if last_order else 999999

        # City from most recent order
        latest_order = self.db.query(Order)\
            .filter(Order.user_id == user_id)\
            .order_by(Order.created_at.desc())\
            .first()

        city = latest_order.city if latest_order else None

        return {
            "total_orders": total_orders,
            "order_count_last_15_days": orders_last_15,
            "order_count_last_23_days": orders_last_23,
            "order_count_last_12_days": orders_last_12,
            "ltv": float(ltv),
            # "days_since_last_order": days_since_last_order,
            "seconds_since_last_order": seconds_since_last_order,
            "city": city,
            "is_new_user": total_orders == 0,
        }
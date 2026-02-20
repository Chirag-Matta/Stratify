# services/user_stats.py

class UserStatsService:
    def __init__(self, db):
        self.db = db

    def get_stats(self, user_id: str) -> dict:
        # 🔴 For POC: hardcoded mock
        return {
            "total_orders": 10,
            "order_count_last_15_days": 8,
            "ltv": 1200,
            "city": "HSR",
            "is_new_user": False
        }
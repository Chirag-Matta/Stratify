from dotenv import load_dotenv
load_dotenv()

import os
from db.models import create_tables
from services.user_stats import UserStatsService

SessionLocal = create_tables(os.getenv("DATABASE_URL"))
db = SessionLocal()

stats = UserStatsService(db).get_stats("user_123")
print(stats)
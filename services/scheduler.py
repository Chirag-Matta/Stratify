from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore
import os

# Store jobs in Redis so they survive an app restart
jobstores = {
    "default": RedisJobStore(
        jobs_key="apscheduler:jobs",
        run_times_key="apscheduler:run_times",
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
    )
}

scheduler = BackgroundScheduler(jobstores=jobstores)
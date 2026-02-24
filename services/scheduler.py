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

job_defaults = {
    "misfire_grace_time": 3600,  # run the job even if up to 1 hour late
    "coalesce": True,            # if multiple misfires stacked up, run only once
}

scheduler = BackgroundScheduler(jobstores=jobstores, job_defaults=job_defaults)
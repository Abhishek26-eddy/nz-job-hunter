from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "job_agent",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.jobs"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "crawl-jobs-every-4-hours": {
            "task": "app.tasks.jobs.run_crawler_batch",
            "schedule": 14400.0,  # seconds
        },
    },
)

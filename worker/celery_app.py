from celery import Celery

from core.config import settings

celery_app = Celery(
    "own_ide",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Emit STARTED so /status can show running state in real time.
    task_track_started=True,
    # Fetch one task per worker slot to keep Docker concurrency bounded.
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

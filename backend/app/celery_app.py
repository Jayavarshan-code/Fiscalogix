from celery import Celery

# Initialize Celery app connecting to the local Docker Redis instance
# 0 is the logical database number in Redis
celery_app = Celery(
    "fiscalogix_workers",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Celery settings for heavy math models
    worker_prefetch_multiplier=1, # Don't hoard tasks
    task_acks_late=True # Only acknowledge after complete mathematical success
)

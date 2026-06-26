import os
from celery import Celery

# Setup Celery with Redis as the broker and backend
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "ai_chatbot",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "tasks.background_tasks"
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Configure task routing (optional, but good for prioritization)
    task_routes={
        "tasks.background_tasks.crawl_task": {"queue": "crawling"},
        "tasks.background_tasks.memory_task": {"queue": "memory"},
    }
)

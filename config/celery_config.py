# Celery Configuration
# Orchestrate task queue with Redis broker

from celery import Celery
from kombu import Queue
from config.settings import settings
import os

# Initialize Celery app
celery_app = Celery(
    "nexus_chat_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_send_sent_event=settings.CELERY_TASK_SEND_SENT_EVENT,
    task_time_limit=settings.CELERY_TASK_TIMEOUT,
    task_soft_time_limit=settings.CELERY_TASK_TIMEOUT - 30,
    
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    
    # Queue routing
    task_routes={
        "modules.chat.tasks.process_chat_intent": {
            "queue": "chat_intent",
            "routing_key": "chat_intent.process_intent",
        },
    },
    
    # Queue configuration
    task_queues=[
        Queue("default", routing_key="default"),
        Queue("chat_intent", routing_key="chat_intent.#"),
    ],
)

# Task auto-discovery
celery_app.autodiscover_tasks(
    ["modules.chat"],
    related_name="tasks"
)


@celery_app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")

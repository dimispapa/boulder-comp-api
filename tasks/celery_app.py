from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

celery_app = Celery('boulder_comp_tasks',
                    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"))

# Optional configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Auto-discover tasks in the 'tasks' directory
celery_app.autodiscover_tasks(['tasks'], force=True)

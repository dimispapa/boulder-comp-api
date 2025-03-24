from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

# Get Redis URL - Heroku sets this as REDIS_URL
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Heroku Redis URLs start with redis://, but we need to support both
if redis_url.startswith('redis://'):
    broker_url = redis_url
    backend_url = redis_url
else:
    broker_url = redis_url
    backend_url = redis_url

celery_app = Celery(
    'boulder_comp_tasks',
    broker=broker_url,
    backend=backend_url
)

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

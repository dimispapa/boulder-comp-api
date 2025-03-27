"""
Celery app configuration.
"""
from celery import Celery
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Celery app
celery_app = Celery('boulder_comp_api',
                    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
                    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
                    include=['tasks.scraper_tasks', 'tasks.scoring_tasks'])

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    worker_max_tasks_per_child=100,
    broker_connection_retry_on_startup=True,
    task_publish_retry=True,
    worker_log_color=True,
    worker_redirect_stdouts=True,
    worker_redirect_stdouts_level='INFO',
)

# Auto-discover tasks in the 'tasks' directory
celery_app.autodiscover_tasks(['tasks'], force=True)

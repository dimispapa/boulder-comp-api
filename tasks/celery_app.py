"""
Celery app configuration.
"""
from celery import Celery
import os
from dotenv import load_dotenv
import ssl

# Load environment variables
load_dotenv()

# Get Redis URL from environment
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Check if we're in development environment
is_dev = os.getenv("DEV_ENV", "False").lower() == "true"

# Create Celery app with conditional SSL configuration
if is_dev:
    # Dev environment - no SSL configuration
    celery_app = Celery('boulder_comp_api',
                        broker=redis_url,
                        backend=redis_url,
                        include=['tasks.scraper_tasks', 'tasks.scoring_tasks'])
else:
    # Production environment - use SSL configuration
    celery_app = Celery('boulder_comp_api',
                        broker=redis_url,
                        backend=redis_url,
                        include=['tasks.scraper_tasks', 'tasks.scoring_tasks'],
                        broker_use_ssl={'ssl_cert_reqs': ssl.CERT_NONE},
                        redis_backend_use_ssl={'ssl_cert_reqs': ssl.CERT_NONE})

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
    # Don't hijack the root logger
    worker_hijack_root_logger=False,
    # Don't redirect stdout/stderr to the logger
    worker_redirect_stdouts=False,
    worker_log_format='%(asctime)s - %(levelname)s - %(message)s',
    worker_task_log_format='%(asctime)s - %(levelname)s - %(message)s',
)

# Auto-discover tasks in the 'tasks' directory
celery_app.autodiscover_tasks(['tasks'], force=True)

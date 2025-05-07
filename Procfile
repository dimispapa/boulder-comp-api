web: uvicorn main:app --host=0.0.0.0 --port=${PORT:-8000}
worker: celery -A tasks worker --loglevel=info --concurrency=2 --prefetch-multiplier=1 --max-memory-per-child=350000
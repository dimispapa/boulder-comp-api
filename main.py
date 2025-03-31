from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import pytz
from celery.signals import setup_logging

# Import routers
from api.routes import scraper, scoring, media

# Set default timezone for datetime operations
pytz.timezone('UTC')

# Load environment variables
load_dotenv()
api_prefix = os.getenv("API_PREFIX", "/api")
api_host = os.getenv("API_HOST", "0.0.0.0")
api_port = os.getenv("API_PORT", "8000")
api_version = os.getenv("API_VERSION", "1.0.0")

# Initialize FastAPI app
app = FastAPI(
    title="Boulder Competition API",
    description="API for Boulder Competition scoring and data scraping",
    version=api_version)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(scraper.router,
                   prefix=f"{api_prefix}/scraper",
                   tags=["scraper"])
app.include_router(scoring.router,
                   prefix=f"{api_prefix}/scoring",
                   tags=["scoring"])
app.include_router(media.router, prefix=f"{api_prefix}/media", tags=["media"])


@setup_logging.connect
def config_loggers(*args, **kwargs):
    # This prevents Celery from configuring its own loggers
    pass


@app.get("/", tags=["root"])
async def root():
    """Root endpoint to verify API is running."""
    return {"message": "Boulder Competition API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=api_host, port=int(api_port), reload=True)

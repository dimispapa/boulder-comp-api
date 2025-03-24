from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Import routers
from api.routes import scraper, scoring

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Boulder Competition API",
    description="API for Boulder Competition scoring and data scraping",
    version="0.1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(scraper.router, prefix="/api/scraper", tags=["scraper"])
app.include_router(scoring.router, prefix="/api/scoring", tags=["scoring"])


@app.get("/", tags=["root"])
async def root():
    """Root endpoint to verify API is running."""
    return {"message": "Boulder Competition API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app",
                host=os.getenv("API_HOST", "0.0.0.0"),
                port=int(os.getenv("API_PORT", "8000")),
                reload=True)

"""
Celery tasks for calculating competition scores.
"""
from tasks.celery_app import celery_app
from scoring.core import ScoreCalculator
from supabase import create_client
import os
from dotenv import load_dotenv
import logging
from typing import Dict, Any, List

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Initialize score calculator
score_calculator = ScoreCalculator(supabase)


@celery_app.task(bind=True, name="scoring.calculate_scores")
async def calculate_scores(self, comp_id: str):
    """
    Celery task to calculate scores for a competition.
    
    Args:
        comp_id (str): ID of the competition
        
    Returns:
        dict: Status and result of the score calculation
    """
    try:
        # Calculate scores
        rankings = await score_calculator.calculate_scores(comp_id)

        return {"status": "success", "rankings": rankings}

    except Exception as e:
        logger.error(f"Error in score calculation task: {str(e)}")
        # Use Celery's retry mechanism
        self.retry(exc=e, countdown=30, max_retries=2)
        return {"status": "error", "detail": str(e)}

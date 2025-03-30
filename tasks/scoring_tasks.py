"""
Celery tasks for calculating competition scores.
"""
from tasks.celery_app import celery_app
from scoring.core import ScoreCalculator
from dotenv import load_dotenv
from typing import Optional

from utils.supabase import get_supabase_client
from utils.loggers import logger

# Load environment variables
load_dotenv()

# Initialize Supabase client
supabase = get_supabase_client()

# Initialize score calculator
score_calculator = ScoreCalculator(supabase)


@celery_app.task(bind=True, name="scoring.calculate_scores")
async def calculate_scores(self, comp_id: str, category: Optional[str] = None):
    """
    Celery task to calculate scores for a competition.

    Args:
        comp_id (str): ID of the competition
        category (str, optional): Filter by category ("marathon" or "boulder_beasts")

    Returns:
        dict: Status and result of the score calculation
    """
    try:
        # Get competition details to validate categories
        comp = await score_calculator._get_competition(comp_id)
        if not comp:
            return {
                "status": "error",
                "detail": f"Competition {comp_id} not found"
            }

        # Validate category if specified
        if category and category not in comp['categories']:
            return {
                "status": "error",
                "detail":
                f"Category {category} not enabled for this competition"
            }

        # Calculate scores
        rankings = await score_calculator.calculate_scores(comp_id)

        # Filter by category if specified
        if category:
            if category == "marathon":
                return {"status": "success", "rankings": rankings["marathon"]}
            elif category == "boulder_beasts":
                return {
                    "status": "success",
                    "rankings": rankings["boulder_beasts"]
                }
            else:
                return {
                    "status": "error",
                    "detail": f"Invalid category: {category}"
                }

        return {"status": "success", "rankings": rankings}

    except Exception as e:
        logger.error(f"Error in score calculation task: {str(e)}")
        # Use Celery's retry mechanism
        self.retry(exc=e, countdown=30, max_retries=2)
        return {"status": "error", "detail": str(e)}

"""
Celery tasks for calculating competition scores.
"""
from tasks.celery_app import celery_app
from scoring.core import ScoreCalculator
from dotenv import load_dotenv
from typing import Optional
import asyncio

from database.management.base import get_db_session
from database.crud.competitions import get_competition_by_id
from utils.loggers import logger
from scoring.data_storage import convert_nested_types

# Load environment variables
load_dotenv()


@celery_app.task(bind=True, name="scoring.calculate_scores")
def calculate_scores(self, comp_id: str, category: Optional[str] = None):
    """
    Celery task to calculate scores for a competition.

    Args:
        comp_id (str): ID of the competition
        category (str, optional): Filter by category
                                  ("marathon" or "boulder_beasts")

    Returns:
        dict: Status and result of the score calculation
    """
    try:
        logger.info(
            f"Starting score calculation task for competition {comp_id}, "
            f"category: {category if category else 'all'}")

        with get_db_session() as session:
            # Get competition details
            logger.debug(f"Retrieving competition {comp_id} details")
            comp = get_competition_by_id(session, comp_id)
            if not comp:
                logger.error(f"Competition {comp_id} not found in database")
                return {
                    "status": "error",
                    "detail": f"Competition {comp_id} not found"
                }

            # Get competition categories
            categories = comp.categories
            category_types = [cat.category_type for cat in categories]

            logger.info(f"Found competition {comp_id}: {comp.name}, "
                        f"categories: {category_types}")

            # Validate category if specified
            if category and category not in category_types:
                logger.error(f"Category {category} not enabled for competition"
                             f" {comp_id}")
                return {
                    "status":
                    "error",
                    "detail":
                    f"Category {category} not enabled for this "
                    f"competition"
                }

            # Initialize score calculator with database session
            logger.debug(
                f"Initializing ScoreCalculator with database session for "
                f"competition {comp_id}")
            score_calculator = ScoreCalculator(session, comp_id)

            # Create event loop for async calculation
            logger.debug("Creating new event loop for async calculations")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Run the async calculation
            logger.info(f"Starting async score calculation for competition"
                        f" {comp_id}")
            try:
                rankings = loop.run_until_complete(
                    score_calculator.calculate_scores())
                logger.info("Async score calculation completed successfully")
            except Exception as calc_error:
                logger.error(
                    f"Error during score calculation: {str(calc_error)}")
                raise
            finally:
                # Clean up the loop
                logger.debug("Closing async event loop")
                loop.close()

            # Check if the calculation returned results
            if not rankings:
                logger.warning(f"Score calculation returned empty results for "
                               f"competition {comp_id}")

            # Log results summary
            marathon_count = len(rankings.get("marathon", []))
            boulder_count = len(rankings.get("boulder_beasts", []))
            logger.info(
                f"Calculation returned {marathon_count} marathon rankings and "
                f"{boulder_count} boulder beasts rankings")

            # Filter by category if specified
            if category:
                if category == "marathon":
                    logger.info("Returning filtered marathon rankings")
                    return {
                        "status": "success",
                        "rankings": convert_nested_types(rankings["marathon"])
                    }
                elif category == "boulder_beasts":
                    logger.info("Returning filtered boulder beasts rankings")
                    return {
                        "status":
                        "success",
                        "rankings":
                        convert_nested_types(rankings["boulder_beasts"])
                    }
                else:
                    logger.error(f"Invalid category: {category}")
                    return {
                        "status": "error",
                        "detail": f"Invalid category: {category}"
                    }

            logger.info(f"Returning all rankings for competition {comp_id}")
            return {
                "status": "success",
                "rankings": convert_nested_types(rankings)
            }

    except Exception as e:
        logger.error(f"Error in score calculation task: {str(e)}")
        # Use Celery's retry mechanism
        logger.info(f"Retrying score calculation task in 30 seconds, attempt "
                    f"{self.request.retries + 1}/3")
        self.retry(exc=e, countdown=30, max_retries=2)
        return {"status": "error", "detail": str(e)}

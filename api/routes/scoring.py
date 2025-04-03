"""
FastAPI router for the scoring endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Optional
from sqlmodel import Session
from scoring.core import ScoreCalculator
from scoring.models import ScoreCalculationRequest
from celery import shared_task
from dotenv import load_dotenv
from database.base import get_db_session
from database.crud.scoring import (get_all_marathon_rankings,
                                   get_all_boulder_beasts_rankings)
from utils.loggers import logger

# Load environment variables
load_dotenv()

# Initialize router
router = APIRouter()


@shared_task
async def calculate_scores_task(comp_id: str, category: Optional[str] = None):
    """Celery task to calculate competition scores."""
    try:
        logger.info(f"Starting score calculation for competition {comp_id}, "
                    f"category: {category}")

        # Use a session within the task
        with get_db_session() as session:
            # Create score calculator with session
            score_calculator = ScoreCalculator(session)

            # Calculate scores
            rankings = await score_calculator.calculate_scores(comp_id)

            logger.info(
                f"Score calculation completed for competition {comp_id}")

            # Filter by category if specified
            if category:
                if category == "marathon":
                    logger.info("Returning marathon rankings "
                                f"for competition {comp_id}")
                    return {
                        "status": "success",
                        "rankings": rankings["marathon"]
                    }
                elif category == "boulder_beasts":
                    logger.info(f"Returning boulder_beasts rankings for "
                                f"competition {comp_id}")
                    return {
                        "status": "success",
                        "rankings": rankings["boulder_beasts"]
                    }
                else:
                    logger.error(f"Invalid category requested: {category}")
                    return {
                        "status": "error",
                        "detail": f"Invalid category: {category}"
                    }

            return {"status": "success", "rankings": rankings}

    except Exception as e:
        logger.error(f"Error in score calculation task: {str(e)}")
        return {"status": "error", "detail": str(e)}


@router.post("/calculate/{comp_id}")
async def start_score_calculation(comp_id: str,
                                  request: ScoreCalculationRequest,
                                  background_tasks: BackgroundTasks,
                                  session: Session = Depends(get_db_session)):
    """
    Start calculating scores for a competition.

    Args:
        comp_id (str): ID of the competition
        request (ScoreCalculationRequest): Request parameters
        background_tasks (BackgroundTasks): FastAPI background tasks
        session (Session): Database session

    Returns:
        dict: Status of the calculation task
    """
    try:
        logger.info(
            f"Received score calculation request for competition {comp_id}, "
            f"category: {request.category}")

        # Create score calculator with session
        score_calculator = ScoreCalculator(session)

        # Get competition details to validate categories
        comp = await score_calculator._get_competition(comp_id)
        if not comp:
            logger.error(f"Competition {comp_id} not found")
            raise HTTPException(status_code=404,
                                detail=f"Competition {comp_id} not found")

        # Validate category if specified
        if request.category and request.category not in comp['categories']:
            logger.error(f"Category {request.category} not enabled for "
                         f"competition {comp_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Category {request.category} not enabled for "
                f"this competition")

        # Queue the calculation task
        task = calculate_scores_task.delay(comp_id, request.category)
        logger.info(f"Score calculation task queued with ID: {task.id}")

        return {
            "status": "success",
            "message": "Score calculation started",
            "task_id": task.id
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to start calculation: {str(e)}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to start calculation: {str(e)}")


@router.get("/status/{task_id}")
async def get_calculation_status(task_id: str):
    """
    Get the status of a score calculation task.

    Args:
        task_id (str): ID of the task to check

    Returns:
        dict: Current status of the task
    """
    try:
        logger.info(f"Checking status of calculation task {task_id}")
        task = calculate_scores_task.AsyncResult(task_id)

        if task.ready():
            if task.successful():
                logger.info(f"Task {task_id} completed successfully")
                return {"status": "completed", "result": task.result}
            else:
                logger.error(f"Task {task_id} failed: {str(task.result)}")
                return {"status": "failed", "error": str(task.result)}
        else:
            logger.info(f"Task {task_id} still in progress")
            return {"status": "in_progress"}

    except Exception as e:
        logger.error(f"Failed to get task status: {str(e)}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to get task status: {str(e)}")


@router.get("/rankings/{comp_id}")
async def get_competition_rankings(comp_id: str,
                                   category: Optional[str] = None,
                                   session: Session = Depends(get_db_session)):
    """
    Get the latest rankings for a competition.

    Args:
        comp_id (str): ID of the competition
        category (str, optional): Filter by category
        ("marathon" or "boulder_beasts")
        session (Session): Database session

    Returns:
        dict: Latest competition rankings
    """
    try:
        logger.info(f"Fetching rankings for competition {comp_id}, "
                    f"category: {category}")

        # Create score calculator with session for competition validation
        score_calculator = ScoreCalculator(session)

        # Get competition details to validate categories
        comp = await score_calculator._get_competition(comp_id)
        if not comp:
            logger.error(f"Competition {comp_id} not found")
            raise HTTPException(status_code=404,
                                detail=f"Competition {comp_id} not found")

        # Validate category if specified
        if category and category not in comp['categories']:
            logger.error(f"Category {category} not enabled for "
                         f"competition {comp_id}")
            raise HTTPException(status_code=400,
                                detail=f"Category {category} not enabled for "
                                f"this competition")

        if category:
            if category == "marathon":
                # Get marathon rankings
                rankings = get_all_marathon_rankings(session)
                # Filter by competition ID
                # NOTE: We need to adapt the model to include competition_id
                comp_id_uuid = comp_id  # Assuming comp_id is already a UUID
                rankings = [
                    r for r in rankings
                    if getattr(r, 'competition_id', None) == comp_id_uuid
                ]

                if not rankings:
                    logger.error(
                        f"No marathon rankings found for competition {comp_id}"
                    )
                    raise HTTPException(
                        status_code=404,
                        detail=f"No marathon rankings found for "
                        f"competition {comp_id}")

                # Convert to dictionary format
                rankings_data = []
                for rank in rankings:
                    rankings_data.append({
                        "id": str(rank.id),
                        "team_id": str(rank.team_id),
                        "base_score": rank.base_score,
                        "volume_score": rank.volume_score,
                        "unique_ascent_score": rank.unique_ascent_score,
                        "team_ascent_bonus": rank.team_ascent_bonus,
                        "master_grade_bonus": rank.master_grade_bonus,
                        "total_score": rank.total_score,
                        "rank": rank.rank
                    })

                logger.info(
                    f"Returning marathon rankings for competition {comp_id}")
                return {"status": "success", "rankings": rankings_data}

            elif category == "boulder_beasts":
                # Get boulder beasts rankings
                rankings = get_all_boulder_beasts_rankings(session)
                # Filter by competition ID
                # NOTE: We need to adapt the model to include competition_id
                comp_id_uuid = comp_id  # Assuming comp_id is already a UUID
                rankings = [
                    r for r in rankings
                    if getattr(r, 'competition_id', None) == comp_id_uuid
                ]

                if not rankings:
                    logger.error(f"No boulder beasts rankings found for "
                                 f"competition {comp_id}")
                    raise HTTPException(
                        status_code=404,
                        detail=f"No boulder beasts rankings found for "
                        f"competition {comp_id}")

                # Convert to dictionary format
                rankings_data = []
                for rank in rankings:
                    rankings_data.append({
                        "id":
                        str(rank.id),
                        "participant_id":
                        str(rank.participant_id),
                        "top_grades":
                        rank.top_grades_dict,
                        "total_score":
                        rank.total_score,
                        "rank":
                        rank.rank
                    })

                logger.info(
                    f"Returning boulder beasts rankings for comp {comp_id}")
                return {"status": "success", "rankings": rankings_data}

            else:
                logger.error(f"Invalid category requested: {category}")
                raise HTTPException(status_code=400,
                                    detail=f"Invalid category: {category}")
        else:
            # Get both categories
            marathon_rankings = get_all_marathon_rankings(session)
            boulder_beasts_rankings = get_all_boulder_beasts_rankings(session)

            # Filter by competition ID
            comp_id_uuid = comp_id  # Assuming comp_id is already a UUID
            marathon_rankings = [
                r for r in marathon_rankings
                if getattr(r, 'competition_id', None) == comp_id_uuid
            ]
            boulder_beasts_rankings = [
                r for r in boulder_beasts_rankings
                if getattr(r, 'competition_id', None) == comp_id_uuid
            ]

            if not marathon_rankings and not boulder_beasts_rankings:
                logger.error(f"No rankings found for competition {comp_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"No rankings found for competition {comp_id}")

            # Convert to dictionary format
            marathon_data = []
            for rank in marathon_rankings:
                marathon_data.append({
                    "id": str(rank.id),
                    "team_id": str(rank.team_id),
                    "base_score": rank.base_score,
                    "volume_score": rank.volume_score,
                    "unique_ascent_score": rank.unique_ascent_score,
                    "team_ascent_bonus": rank.team_ascent_bonus,
                    "master_grade_bonus": rank.master_grade_bonus,
                    "total_score": rank.total_score,
                    "rank": rank.rank
                })

            boulder_beasts_data = []
            for rank in boulder_beasts_rankings:
                boulder_beasts_data.append({
                    "id":
                    str(rank.id),
                    "participant_id":
                    str(rank.participant_id),
                    "top_grades":
                    rank.top_grades_dict,
                    "total_score":
                    rank.total_score,
                    "rank":
                    rank.rank
                })

            logger.info(f"Returning both categories for competition {comp_id}")
            return {
                "status": "success",
                "marathon": marathon_data,
                "boulder_beasts": boulder_beasts_data
            }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to get rankings: {str(e)}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to get rankings: {str(e)}")

"""
FastAPI router for the scoring endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from tasks.scoring_tasks import calculate_scores
import logging
from supabase import create_client
import os
from scoring.core import ScoreCalculator
from celery import shared_task
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()

# Initialize Supabase client
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# Initialize score calculator
score_calculator = ScoreCalculator(supabase)


# Request models
class ScoreCalculationRequest(BaseModel):
    competition_id: str
    update_leaderboard: bool = True
    category: Optional[str] = None  # "marathon", "boulder_beasts", or None for both


# Response models
class ScoreCalculationResponse(BaseModel):
    task_id: str
    status: str
    message: str


@shared_task
async def calculate_scores_task(comp_id: str, category: Optional[str] = None):
    """Celery task to calculate competition scores."""
    try:
        # Calculate scores
        rankings = await score_calculator.calculate_scores(comp_id)

        # Filter by category if specified
        if category:
            if category == "marathon":
                return {"status": "success", "rankings": rankings["marathon"]}
            elif category == "boulder_beasts":
                return {"status": "success", "rankings": rankings["boulder_beasts"]}
            else:
                return {"status": "error", "detail": f"Invalid category: {category}"}

        return {"status": "success", "rankings": rankings}

    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/calculate/{comp_id}")
async def start_score_calculation(comp_id: str,
                                request: ScoreCalculationRequest,
                                background_tasks: BackgroundTasks):
    """
    Start calculating scores for a competition.
    
    Args:
        comp_id (str): ID of the competition
        request (ScoreCalculationRequest): Request parameters
        background_tasks (BackgroundTasks): FastAPI background tasks
        
    Returns:
        dict: Status of the calculation task
    """
    try:
        # Get competition details to validate categories
        comp = await score_calculator._get_competition(comp_id)
        if not comp:
            raise HTTPException(status_code=404,
                              detail=f"Competition {comp_id} not found")

        # Validate category if specified
        if request.category and request.category not in comp['categories']:
            raise HTTPException(
                status_code=400,
                detail=f"Category {request.category} not enabled for this competition"
            )

        # Queue the calculation task
        task = calculate_scores_task.delay(comp_id, request.category)

        return {
            "status": "success",
            "message": "Score calculation started",
            "task_id": task.id
        }

    except HTTPException as e:
        raise e
    except Exception as e:
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
        task = calculate_scores_task.AsyncResult(task_id)

        if task.ready():
            if task.successful():
                return {"status": "completed", "result": task.result}
            else:
                return {"status": "failed", "error": str(task.result)}
        else:
            return {"status": "in_progress"}

    except Exception as e:
        raise HTTPException(status_code=500,
                          detail=f"Failed to get task status: {str(e)}")


@router.get("/rankings/{comp_id}")
async def get_competition_rankings(comp_id: str,
                                 category: Optional[str] = None):
    """
    Get the latest rankings for a competition.
    
    Args:
        comp_id (str): ID of the competition
        category (str, optional): Filter by category ("marathon" or "boulder_beasts")
        
    Returns:
        dict: Latest competition rankings
    """
    try:
        # Get competition details to validate categories
        comp = await score_calculator._get_competition(comp_id)
        if not comp:
            raise HTTPException(status_code=404,
                              detail=f"Competition {comp_id} not found")

        # Validate category if specified
        if category and category not in comp['categories']:
            raise HTTPException(
                status_code=400,
                detail=f"Category {category} not enabled for this competition"
            )

        if category:
            if category == "marathon":
                table = "marathon_rankings"
            elif category == "boulder_beasts":
                table = "boulder_beasts_rankings"
            else:
                raise HTTPException(status_code=400,
                                  detail=f"Invalid category: {category}")
        else:
            # Get both categories
            marathon_result = supabase.table("marathon_rankings").select(
                "*").eq("competition_id", comp_id).order("rank").execute()

            boulder_beasts_result = supabase.table(
                "boulder_beasts_rankings").select("*").eq(
                    "competition_id", comp_id).order("rank").execute()

            if not marathon_result.data and not boulder_beasts_result.data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No rankings found for competition {comp_id}")

            return {
                "status": "success",
                "marathon": marathon_result.data,
                "boulder_beasts": boulder_beasts_result.data
            }

        # Get single category
        result = supabase.table(table).select("*").eq(
            "competition_id", comp_id).order("rank").execute()

        if not result.data:
            raise HTTPException(
                status_code=404,
                detail=f"No {category} rankings found for competition {comp_id}"
            )

        return {"status": "success", "rankings": result.data}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500,
                          detail=f"Failed to get rankings: {str(e)}")


@router.get("/leaderboard/{competition_id}")
async def get_leaderboard(competition_id: str,
                         category: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the current leaderboard for a specific competition.
    
    Args:
        competition_id (str): ID of the competition
        category (str, optional): Filter by category ("marathon" or "boulder_beasts")
        
    Returns:
        dict: Current leaderboard data
    """
    try:
        # Get competition details to validate categories
        comp = await score_calculator._get_competition(competition_id)
        if not comp:
            raise HTTPException(status_code=404,
                              detail=f"Competition {competition_id} not found")

        # Validate category if specified
        if category and category not in comp['categories']:
            raise HTTPException(
                status_code=400,
                detail=f"Category {category} not enabled for this competition"
            )

        if category:
            if category == "marathon":
                result = supabase.table("marathon_rankings").select(
                    "marathon_rankings.*, teams.name as team_name").eq(
                        "competition_id",
                        competition_id).order("rank").execute()

                leaderboard = {
                    "competition_id": competition_id,
                    "category": "marathon",
                    "teams": [{
                        "team_id": rank["team_id"],
                        "name": rank["team_name"],
                        "score": rank["total_score"],
                        "rank": rank["rank"]
                    } for rank in result.data]
                }

            elif category == "boulder_beasts":
                result = supabase.table("boulder_beasts_rankings").select(
                    "boulder_beasts_rankings.*, participants.first_name, "
                    "participants.last_name").eq(
                        "competition_id",
                        competition_id).order("rank").execute()

                leaderboard = {
                    "competition_id": competition_id,
                    "category": "boulder_beasts",
                    "participants": [{
                        "participant_id": rank["participant_id"],
                        "name": f"{rank['first_name']} {rank['last_name']}",
                        "score": rank["total_score"],
                        "rank": rank["rank"],
                        "top_grades": rank["top_grades"]
                    } for rank in result.data]
                }

            else:
                raise HTTPException(status_code=400,
                                  detail=f"Invalid category: {category}")
        else:
            # Get both categories
            marathon_result = supabase.table("marathon_rankings").select(
                "marathon_rankings.*, teams.name as team_name").eq(
                    "competition_id", competition_id).order("rank").execute()

            boulder_beasts_result = supabase.table(
                "boulder_beasts_rankings").select(
                    "boulder_beasts_rankings.*, participants.first_name, "
                    "participants.last_name").eq(
                        "competition_id",
                        competition_id).order("rank").execute()

            leaderboard = {
                "competition_id": competition_id,
                "marathon": {
                    "teams": [{
                        "team_id": rank["team_id"],
                        "name": rank["team_name"],
                        "score": rank["total_score"],
                        "rank": rank["rank"]
                    } for rank in marathon_result.data]
                },
                "boulder_beasts": {
                    "participants": [{
                        "participant_id": rank["participant_id"],
                        "name": f"{rank['first_name']} {rank['last_name']}",
                        "score": rank["total_score"],
                        "rank": rank["rank"],
                        "top_grades": rank["top_grades"]
                    } for rank in boulder_beasts_result.data]
                }
            }

        if not leaderboard.get("teams", []) and not leaderboard.get(
                "participants", []):
            raise HTTPException(
                status_code=404,
                detail=f"No leaderboard found for competition {competition_id}"
            )

        leaderboard["last_updated"] = datetime.now().isoformat()
        return {"status": "success", "data": leaderboard}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {str(e)}")
        raise HTTPException(status_code=500,
                          detail=f"Failed to fetch leaderboard: {str(e)}")

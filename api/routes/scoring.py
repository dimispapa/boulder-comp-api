from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from tasks.scoring_tasks import calculate_scores
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter()


# Request models
class ScoreCalculationRequest(BaseModel):
    competition_id: str
    update_leaderboard: bool = True
    format_type: Optional[str] = "standard"  # "standard", "marathon", etc.


# Response models
class ScoreCalculationResponse(BaseModel):
    task_id: str
    status: str
    message: str


@router.post("/calculate", response_model=ScoreCalculationResponse)
async def start_score_calculation(
        request: ScoreCalculationRequest,
        background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Start a score calculation task for a competition.
    
    This will calculate scores based on logged ascents and optionally
    update the leaderboard.
    """
    try:
        # Queue the task
        task = calculate_scores.delay(request.competition_id,
                                      request.update_leaderboard)

        logger.info(
            f"Score calculation initiated for competition {request.competition_id} "
            f"with task ID: {task.id}")

        return {
            "task_id":
            task.id,
            "status":
            "initiated",
            "message":
            f"Score calculation for competition {request.competition_id} started"
        }

    except Exception as e:
        logger.error(f"Error starting score calculation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start score calculation: {str(e)}")


@router.get("/task/{task_id}", response_model=Dict[str, Any])
async def get_calculation_status(task_id: str) -> Dict[str, Any]:
    """
    Check the status of a score calculation task by task ID.
    """
    try:
        # Get task result
        task = calculate_scores.AsyncResult(task_id)

        if task.state == 'PENDING':
            response = {
                "task_id": task_id,
                "status": "pending",
                "message": "Task is pending execution"
            }
        elif task.state == 'STARTED':
            response = {
                "task_id": task_id,
                "status": "in_progress",
                "message": "Task is currently in progress"
            }
        elif task.state == 'SUCCESS':
            response = {
                "task_id": task_id,
                "status": "completed",
                "message": "Task completed successfully",
                "result": task.result
            }
        elif task.state == 'FAILURE':
            response = {
                "task_id": task_id,
                "status": "failed",
                "message": f"Task failed: {str(task.result)}",
            }
        else:
            response = {
                "task_id": task_id,
                "status": task.state,
                "message": "Task status unknown"
            }

        return response

    except Exception as e:
        logger.error(f"Error checking calculation status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get calculation status: {str(e)}")


@router.get("/leaderboard/{competition_id}", response_model=Dict[str, Any])
async def get_leaderboard(competition_id: str) -> Dict[str, Any]:
    """
    Get the current leaderboard for a specific competition.
    
    This endpoint fetches the leaderboard directly from the database
    without recalculating scores.
    """
    try:
        # TODO: Implement the actual database query
        # This will be implemented when you integrate with Supabase

        # Placeholder implementation
        leaderboard = {
            "competition_id":
            competition_id,
            "name":
            "Sample Competition",
            "teams": [
                {
                    "team_id": "team1",
                    "name": "Team Crimpers",
                    "score": 250,
                    "rank": 1
                },
                {
                    "team_id": "team2",
                    "name": "Boulder Crushers",
                    "score": 180,
                    "rank": 2
                },
                {
                    "team_id": "team3",
                    "name": "Chalk Monkeys",
                    "score": 175,
                    "rank": 3
                },
            ],
            "last_updated":
            "2023-04-24T16:45:00Z"
        }

        return {"status": "success", "data": leaderboard}

    except Exception as e:
        logger.error(f"Error fetching leaderboard: {str(e)}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to fetch leaderboard: {str(e)}")

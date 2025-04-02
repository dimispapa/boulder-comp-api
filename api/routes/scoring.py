"""
FastAPI router for the scoring endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional
from scoring.core import ScoreCalculator
from scoring.models import (ScoreCalculationRequest, LeaderboardResponse,
                            MarathonLeaderboard, BoulderBeastsLeaderboard,
                            MarathonTeamRanking,
                            BoulderBeastsParticipantRanking,
                            MarathonScoreComponents)
from celery import shared_task
from dotenv import load_dotenv
from utils.supabase import get_admin_supabase_client
from utils.loggers import logger

# Load environment variables
load_dotenv()

# Initialize router
router = APIRouter()

# Initialize Supabase client
supabase = get_admin_supabase_client()

# Initialize score calculator
score_calculator = ScoreCalculator(supabase)


@shared_task
async def calculate_scores_task(comp_id: str, category: Optional[str] = None):
    """Celery task to calculate competition scores."""
    try:
        logger.info(f"Starting score calculation for competition {comp_id}, "
                    f"category: {category}")

        # Calculate scores
        rankings = await score_calculator.calculate_scores(comp_id)

        logger.info(f"Score calculation completed for competition {comp_id}")

        # Filter by category if specified
        if category:
            if category == "marathon":
                logger.info(
                    f"Returning marathon rankings for competition {comp_id}")
                return {"status": "success", "rankings": rankings["marathon"]}
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
        logger.info(
            f"Received score calculation request for competition {comp_id}, "
            f"category: {request.category}")

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
                                   category: Optional[str] = None):
    """
    Get the latest rankings for a competition.

    Args:
        comp_id (str): ID of the competition
        category (str, optional): Filter by category
        ("marathon" or "boulder_beasts")

    Returns:
        dict: Latest competition rankings
    """
    try:
        logger.info(f"Fetching rankings for competition {comp_id}, "
                    f"category: {category}")

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
                table = "marathon_rankings"
            elif category == "boulder_beasts":
                table = "boulder_beasts_rankings"
            else:
                logger.error(f"Invalid category requested: {category}")
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
                logger.error(f"No rankings found for competition {comp_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"No rankings found for competition {comp_id}")

            logger.info(f"Returning both categories for competition {comp_id}")
            return {
                "status": "success",
                "marathon": marathon_result.data,
                "boulder_beasts": boulder_beasts_result.data
            }

        # Get single category
        result = supabase.table(table).select("*").eq(
            "competition_id", comp_id).order("rank").execute()

        if not result.data:
            logger.error(
                f"No {category} rankings found for competition {comp_id}")
            raise HTTPException(status_code=404,
                                detail=f"No {category} rankings found for "
                                f"competition {comp_id}")

        logger.info(f"Returning {category} rankings for competition {comp_id}")
        return {"status": "success", "rankings": result.data}

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to get rankings: {str(e)}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to get rankings: {str(e)}")


@router.get("/leaderboard/{competition_id}")
async def get_leaderboard(competition_id: str,
                          category: Optional[str] = None) -> Dict[str, Any]:
    """
    Get the current leaderboard for a specific competition.

    Args:
        competition_id (str): ID of the competition
        category (str, optional): Filter by category
        ("marathon" or "boulder_beasts")

    Returns:
        dict: Current leaderboard data
    """
    try:
        logger.info(f"Fetching leaderboard for competition {competition_id}, "
                    f"category: {category}")

        # Get competition details to validate categories
        comp = await score_calculator._get_competition(competition_id)
        if not comp:
            logger.error(f"Competition {competition_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"Competition {competition_id} not found")

        # Validate category if specified
        if category and category not in comp['categories']:
            logger.error(f"Category {category} not enabled for "
                         f"competition {competition_id}")
            raise HTTPException(status_code=400,
                                detail=f"Category {category} not enabled for "
                                f"this competition")

        if category:
            if category == "marathon":
                result = supabase.table("marathon_rankings").select(
                    "marathon_rankings.*, teams.name as team_name,"
                    " teams.team_size").eq(
                        "competition_id",
                        competition_id).order("rank").execute()

                leaderboard = {
                    "competition_id":
                    competition_id,
                    "category":
                    "marathon",
                    "teams": [{
                        "team_id": rank["team_id"],
                        "name": rank["team_name"],
                        "team_size": rank["team_size"],
                        "score": rank["total_score"],
                        "rank": rank["rank"],
                        "components": {
                            "base_score": rank["base_score"],
                            "volume_score": rank["volume_score"],
                            "unique_ascent_score": rank["unique_ascent_score"],
                            "team_ascent_bonus": rank["team_ascent_bonus"],
                            "master_grade_bonus": rank["master_grade_bonus"]
                        }
                    } for rank in result.data]
                }

                logger.info(f"Returning marathon leaderboard for "
                            f"competition {competition_id}")
                return {"status": "success", "leaderboard": leaderboard}

            elif category == "boulder_beasts":
                result = supabase.table("boulder_beasts_rankings").select(
                    "boulder_beasts_rankings.*, participants.first_name,"
                    " participants.last_name").eq(
                        "competition_id",
                        competition_id).order("rank").execute()

                leaderboard = {
                    "competition_id":
                    competition_id,
                    "category":
                    "boulder_beasts",
                    "participants": [{
                        "participant_id": rank["participant_id"],
                        "name": f"{rank['first_name']} {rank['last_name']}",
                        "team_id": rank["team_id"],
                        "is_solo": rank["team_id"] is None,
                        "score": rank["total_score"],
                        "rank": rank["rank"],
                        "top_grades": rank["top_grades"]
                    } for rank in result.data]
                }

                logger.info("Returning boulder_beasts leaderboard for "
                            f"competition {competition_id}")
                return {"status": "success", "leaderboard": leaderboard}
            else:
                logger.error(f"Invalid category requested: {category}")
                raise HTTPException(status_code=400,
                                    detail=f"Invalid category: {category}")
        else:
            # Get marathon leaderboard
            marathon_result = supabase.table("marathon_rankings").select(
                "marathon_rankings.*, teams.name as team_name, teams.team_size"
            ).eq("competition_id", competition_id).order("rank").execute()

            marathon_leaderboard = {
                "competition_id":
                competition_id,
                "category":
                "marathon",
                "teams": [{
                    "team_id": rank["team_id"],
                    "name": rank["team_name"],
                    "team_size": rank["team_size"],
                    "score": rank["total_score"],
                    "rank": rank["rank"],
                    "components": {
                        "base_score": rank["base_score"],
                        "volume_score": rank["volume_score"],
                        "unique_ascent_score": rank["unique_ascent_score"],
                        "team_ascent_bonus": rank["team_ascent_bonus"],
                        "master_grade_bonus": rank["master_grade_bonus"]
                    }
                } for rank in marathon_result.data]
            } if marathon_result.data else None

            # Get boulder beasts leaderboard
            boulder_result = supabase.table("boulder_beasts_rankings").select(
                "boulder_beasts_rankings.*, participants.first_name,"
                " participants.last_name").eq(
                    "competition_id", competition_id).order("rank").execute()

            boulder_leaderboard = {
                "competition_id":
                competition_id,
                "category":
                "boulder_beasts",
                "participants": [{
                    "participant_id": rank["participant_id"],
                    "name": f"{rank['first_name']} {rank['last_name']}",
                    "team_id": rank["team_id"],
                    "is_solo": rank["team_id"] is None,
                    "score": rank["total_score"],
                    "rank": rank["rank"],
                    "top_grades": rank["top_grades"]
                } for rank in boulder_result.data]
            } if boulder_result.data else None

            if not marathon_leaderboard and not boulder_leaderboard:
                logger.error(
                    f"No rankings found for competition {competition_id}")
                raise HTTPException(status_code=404,
                                    detail=f"No rankings found for "
                                    f"competition {competition_id}")

            logger.info(f"Returning combined leaderboard for "
                        f"competition {competition_id}")
            return {
                "status": "success",
                "marathon": marathon_leaderboard,
                "boulder_beasts": boulder_leaderboard
            }

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to get leaderboard: {str(e)}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to get leaderboard: {str(e)}")


@router.get("/leaderboard-with-models/{competition_id}",
            response_model=LeaderboardResponse)
async def get_leaderboard_with_models(
        competition_id: str,
        category: Optional[str] = None) -> LeaderboardResponse:
    """
    Get the current leaderboard for a specific competition
    using Pydantic models.

    Args:
        competition_id (str): ID of the competition
        category (str, optional): Filter by category
        ("marathon" or "boulder_beasts")

    Returns:
        LeaderboardResponse: Structured leaderboard data
    """
    try:
        logger.info(
            f"Fetching model leaderboard for competition {competition_id}, "
            f"category: {category}")

        # Get competition details to validate categories
        comp = await score_calculator._get_competition(competition_id)
        if not comp:
            logger.error(f"Competition {competition_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"Competition {competition_id} not found")

        # Validate category if specified
        if category and category not in comp['categories']:
            logger.error(f"Category {category} not enabled for "
                         f"competition {competition_id}")
            raise HTTPException(status_code=400,
                                detail=f"Category {category} not enabled for "
                                f"this competition")

        if category == "marathon" or not category:
            # Get marathon leaderboard
            result = supabase.table("marathon_rankings").select(
                "marathon_rankings.*, teams.name as team_name, teams.team_size"
            ).eq("competition_id", competition_id).order("rank").execute()

            if result.data and (category == "marathon" or not category):
                teams = []
                for rank in result.data:
                    teams.append(
                        MarathonTeamRanking(
                            team_id=rank["team_id"],
                            name=rank["team_name"],
                            team_size=rank["team_size"],
                            score=rank["total_score"],
                            rank=rank["rank"],
                            components=MarathonScoreComponents(
                                base_score=rank["base_score"],
                                volume_score=rank["volume_score"],
                                unique_ascent_score=rank[
                                    "unique_ascent_score"],
                                team_ascent_bonus=rank["team_ascent_bonus"],
                                master_grade_bonus=rank["master_grade_bonus"]))
                    )

                if category == "marathon":
                    marathon_leaderboard = MarathonLeaderboard(
                        competition_id=competition_id,
                        category="marathon",
                        teams=teams)
                    logger.info(f"Returning marathon model leaderboard for "
                                f"competition {competition_id}")
                    return LeaderboardResponse(
                        status="success", leaderboard=marathon_leaderboard)

        if category == "boulder_beasts" or not category:
            # Get boulder beasts leaderboard
            result = supabase.table("boulder_beasts_rankings").select(
                "boulder_beasts_rankings.*, "
                "participants.first_name, participants.last_name").eq(
                    "competition_id", competition_id).order("rank").execute()

            if result.data and (category == "boulder_beasts" or not category):
                participants = []
                for rank in result.data:
                    participants.append(
                        BoulderBeastsParticipantRanking(
                            participant_id=rank["participant_id"],
                            name=f"{rank['first_name']} {rank['last_name']}",
                            team_id=rank["team_id"],
                            is_solo=rank["team_id"] is None,
                            score=rank["total_score"],
                            rank=rank["rank"],
                            top_grades=rank["top_grades"]))

                if category == "boulder_beasts":
                    boulder_leaderboard = BoulderBeastsLeaderboard(
                        competition_id=competition_id,
                        category="boulder_beasts",
                        participants=participants)
                    logger.info(
                        f"Returning boulder_beasts model leaderboard for "
                        f"competition {competition_id}")
                    return LeaderboardResponse(status="success",
                                               leaderboard=boulder_leaderboard)

        # If we got here and category is specified, we didn't find data
        if category:
            logger.error(f"No {category} rankings found for "
                         f"competition {competition_id}")
            raise HTTPException(status_code=404,
                                detail=f"No {category} rankings found for "
                                f"competition {competition_id}")

        # If no category specified, return based on what data we found
        if category is None:
            if not result.data:
                logger.error(
                    f"No rankings found for competition {competition_id}")
                raise HTTPException(status_code=404,
                                    detail=f"No rankings found for "
                                    f"competition {competition_id}")

            # Return the category we have data for
            if "boulder_beasts" in locals() and boulder_leaderboard:
                return LeaderboardResponse(status="success",
                                           leaderboard=boulder_leaderboard)
            elif "marathon_leaderboard" in locals() and marathon_leaderboard:
                return LeaderboardResponse(status="success",
                                           leaderboard=marathon_leaderboard)

        # Should not get here, but just in case
        raise HTTPException(status_code=404,
                            detail="No leaderboard data found")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to get model leaderboard: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get model leaderboard: {str(e)}")

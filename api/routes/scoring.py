"""
FastAPI router for the scoring endpoints.
"""
import csv
import io
import zipfile
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from typing import Optional
from sqlmodel import Session, select
from scoring.models import ScoreCalculationRequest
from dotenv import load_dotenv
from database.management.base import get_db
from database.crud.scoring import (get_all_marathon_rankings,
                                   get_all_boulder_beasts_rankings)
from database.crud.competitions import (get_competition_by_id,
                                        get_all_competitions)
from utils.loggers import logger
from tasks.scoring_tasks import calculate_scores
from database.models.competitions import (MarathonSubCategory, Team,
                                          Participant)
from database.models.accounts import User
from database.models.scoring import (MarathonRanking, BoulderBeastsRanking)

# Load environment variables
load_dotenv()

# Initialize router
router = APIRouter()


@router.post("/calculate")
async def start_score_calculation(request: ScoreCalculationRequest,
                                  background_tasks: BackgroundTasks,
                                  session: Session = Depends(get_db)):
    """
    Start calculating scores for a competition.

    Args:
        request (ScoreCalculationRequest): Request parameters including
                                           competition_id

    Returns:
        dict: Status of the calculation task
    """
    try:
        comp_id = request.competition_id
        logger.info(
            f"Received score calculation request for competition {comp_id}, "
            f"category: {request.category}")

        # Get competition details
        comp = get_competition_by_id(session, comp_id)
        if not comp:
            logger.error(f"Competition {comp_id} not found")
            raise HTTPException(status_code=404,
                                detail=f"Competition {comp_id} not found")

        # Get competition categories
        categories = comp.categories
        category_types = [cat.category_type for cat in categories]

        # Validate category if specified
        if request.category and request.category not in category_types:
            logger.error(f"Category {request.category} not enabled for "
                         f"competition {comp_id}")
            raise HTTPException(
                status_code=400,
                detail=f"Category {request.category} not enabled for "
                f"this competition")

        # Queue the calculation task using the imported task
        task = calculate_scores.delay(comp_id, request.category)
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
        task = calculate_scores.AsyncResult(task_id)

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
                                   subcategory: Optional[str] = None,
                                   session: Session = Depends(get_db)):
    """
    Get the latest rankings for a competition.

    Args:
        comp_id (str): ID of the competition
        category (str, optional): Filter by category
        ("marathon" or "boulder_beasts")
        subcategory (str, optional): Filter by marathon subcategory
        ("lt_6B" or "gte_6B")
        session (Session): Database session

    Returns:
        dict: Latest competition rankings
    """
    try:
        logger.info(f"Fetching rankings for competition {comp_id}, "
                    f"category: {category}, subcategory: {subcategory}")

        # Get competition
        comp = get_competition_by_id(session, comp_id)
        if not comp:
            logger.error(f"Competition {comp_id} not found")
            raise HTTPException(status_code=404,
                                detail=f"Competition {comp_id} not found")

        # Get active competition categories
        categories = comp.categories
        category_types = [cat.category_type for cat in categories]

        # Validate category if specified
        if category and category not in category_types:
            logger.error(f"Category {category} not enabled for "
                         f"competition {comp_id}")
            raise HTTPException(status_code=400,
                                detail=f"Category {category} not enabled for "
                                f"this competition")

        # Validate subcategory if specified
        if subcategory:
            try:
                # Use the enum to validate
                # this will raise ValueError if not valid
                MarathonSubCategory[subcategory]
            except (KeyError, ValueError):
                logger.error(f"Invalid subcategory: {subcategory}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid subcategory: {subcategory}")

        if category:
            if category == "marathon":
                # Get marathon rankings
                rankings = get_all_marathon_rankings(session)
                # Filter by competition ID
                comp_id_uuid = comp_id  # Assuming comp_id is already a UUID
                rankings = [
                    r for r in rankings if r.competition_id == comp_id_uuid
                ]

                if not rankings:
                    logger.error(
                        f"No marathon rankings found for competition {comp_id}"
                    )
                    raise HTTPException(
                        status_code=404,
                        detail=f"No marathon rankings found for "
                        f"competition {comp_id}")

                # Filter by subcategory if specified
                if subcategory:
                    # Get the actual display value from the enum
                    display_subcategory = MarathonSubCategory[
                        subcategory].value
                    rankings = [
                        r for r in rankings
                        if r.marathon_subcategory == display_subcategory
                    ]

                # Group by subcategory using enum keys
                subcategory_rankings = {
                    key: []
                    for key in MarathonSubCategory.__members__
                }

                # Convert to dictionary format and group by subcategory
                for rank in rankings:
                    rank_data = {
                        "id": str(rank.id),
                        "team_id": str(rank.team_id),
                        "base_score": rank.base_score,
                        "volume_bonus": rank.volume_bonus,
                        "unique_ascent_bonus": rank.unique_ascent_bonus,
                        "team_ascent_bonus": rank.team_ascent_bonus,
                        "master_grade_bonus": rank.master_grade_bonus,
                        "remote_boulder_bonus": rank.remote_boulder_bonus,
                        "total_score": rank.total_score,
                        "normalized_total_score": rank.normalized_total_score,
                        "rank": rank.rank,
                        "subcategory": rank.marathon_subcategory
                    }

                    # Find the enum key from its value
                    subcategory_key = None
                    for key, value in MarathonSubCategory.__members__.items():
                        if value.value == rank.marathon_subcategory:
                            subcategory_key = key
                            break

                    if subcategory_key:
                        subcategory_rankings[subcategory_key].append(rank_data)

                # If subcategory filter applied, only return that subcategory
                if subcategory:
                    logger.info(
                        f"Returning {subcategory} marathon rankings for "
                        f"competition {comp_id}")
                    return {
                        "status": "success",
                        "rankings": subcategory_rankings[subcategory]
                    }

                logger.info(
                    f"Returning marathon rankings for competition {comp_id}")
                return {"status": "success", "rankings": subcategory_rankings}

            elif category == "boulder_beasts":
                # Get boulder beasts rankings
                rankings = get_all_boulder_beasts_rankings(session)
                # Filter by competition ID
                comp_id_uuid = comp_id  # Assuming comp_id is already a UUID
                rankings = [
                    r for r in rankings if r.competition_id == comp_id_uuid
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
                        "top_5_routes":
                        rank.top_5_routes,
                        "top_5_routes_score":
                        rank.top_5_routes_score,
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
                if r.competition_id == comp_id_uuid
            ]
            boulder_beasts_rankings = [
                r for r in boulder_beasts_rankings
                if r.competition_id == comp_id_uuid
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
                    "volume_bonus": rank.volume_bonus,
                    "unique_ascent_bonus": rank.unique_ascent_bonus,
                    "team_ascent_bonus": rank.team_ascent_bonus,
                    "master_grade_bonus": rank.master_grade_bonus,
                    "remote_boulder_bonus": rank.remote_boulder_bonus,
                    "total_score": rank.total_score,
                    "normalized_total_score": rank.normalized_total_score,
                    "rank": rank.rank
                })

            boulder_beasts_data = []
            for rank in boulder_beasts_rankings:
                boulder_beasts_data.append({
                    "id":
                    str(rank.id),
                    "participant_id":
                    str(rank.participant_id),
                    "top_5_routes":
                    rank.top_5_routes,
                    "top_5_routes_score":
                    rank.top_5_routes_score,
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


@router.get("/export/{comp_id}")
async def export_competition_results(comp_id: str,
                                     session: Session = Depends(get_db)):
    """
    Export all rankings for a competition as a zip of three CSV files:
    - marathon_lt_6B.csv
    - marathon_gte_6B.csv
    - boulder_beasts.csv

    Each CSV includes team/participant names joined from related tables.
    Only files with data are included in the zip.

    Args:
        comp_id (str): ID of the competition
        session (Session): Database session

    Returns:
        StreamingResponse: ZIP file download
    """
    comp = get_competition_by_id(session, comp_id)
    if not comp:
        raise HTTPException(status_code=404,
                            detail=f"Competition {comp_id} not found")

    marathon_rows = session.exec(
        select(MarathonRanking, Team.name).join(
            Team, Team.id == MarathonRanking.team_id).where(
                MarathonRanking.competition_id == comp_id).order_by(
                    MarathonRanking.marathon_subcategory,
                    MarathonRanking.rank)).all()

    boulder_rows = session.exec(
        select(BoulderBeastsRanking, User.first_name, User.last_name).join(
            Participant,
            Participant.id == BoulderBeastsRanking.participant_id).join(
                User, User.id == Participant.user_id, isouter=True).where(
                    BoulderBeastsRanking.competition_id == comp_id).order_by(
                        BoulderBeastsRanking.rank)).all()

    if not marathon_rows and not boulder_rows:
        raise HTTPException(status_code=404,
                            detail=f"No rankings found for competition "
                            f"{comp_id}. Run /calculate first.")

    marathon_headers = [
        "rank", "team_name", "team_size", "base_score", "volume_bonus",
        "team_ascent_bonus", "unique_ascent_bonus", "master_grade_bonus",
        "remote_boulder_bonus", "total_score", "normalized_total_score"
    ]

    by_subcategory: dict = {}
    for ranking, team_name in marathon_rows:
        sub = (ranking.marathon_subcategory.value if ranking.marathon_subcategory
               else "unspecified")
        by_subcategory.setdefault(sub, []).append((ranking, team_name))

    def marathon_csv(rows) -> str:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(marathon_headers)
        for ranking, team_name in rows:
            w.writerow([
                ranking.rank, team_name, ranking.team_size, ranking.base_score,
                ranking.volume_bonus, ranking.team_ascent_bonus,
                ranking.unique_ascent_bonus, ranking.master_grade_bonus,
                ranking.remote_boulder_bonus, ranking.total_score,
                ranking.normalized_total_score
            ])
        return buf.getvalue()

    def boulder_csv(rows) -> str:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow([
            "rank", "first_name", "last_name", "top_5_routes_score",
            "total_score", "top_5_routes"
        ])
        for ranking, first_name, last_name in rows:
            w.writerow([
                ranking.rank, first_name or "", last_name or "",
                ranking.top_5_routes_score, ranking.total_score,
                ", ".join(ranking.top_5_routes or [])
            ])
        return buf.getvalue()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for subcategory, rows in by_subcategory.items():
            zf.writestr(f"marathon_{subcategory}.csv", marathon_csv(rows))
        if boulder_rows:
            zf.writestr("boulder_beasts.csv", boulder_csv(boulder_rows))

    zip_buffer.seek(0)
    filename = f"{comp.name.replace(' ', '_')}_results.zip"
    return StreamingResponse(
        iter([zip_buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/competitions", response_model=dict)
async def list_competitions(session: Session = Depends(get_db)):
    """
    Get a list of all competitions.

    Args:
        session (Session): Database session

    Returns:
        dict: List of competitions with basic details
    """
    try:
        logger.info("Fetching list of all competitions")

        # Get all competitions from the database
        competitions = get_all_competitions(session)

        if not competitions:
            logger.info("No competitions found in the database")
            return {"status": "success", "competitions": []}

        # Convert to dictionary format
        competitions_data = []
        for comp in competitions:
            competitions_data.append({
                "id":
                str(comp.id),
                "name":
                comp.name,
                "display_name":
                comp.display_name,
                "categories": [cat.category_type for cat in comp.categories],
                "start_date":
                comp.start_date.isoformat(),
                "end_date":
                comp.end_date.isoformat(),
                "status":
                comp.status,
                "crag":
                comp.crag,
                "venue":
                comp.venue or "N/A",
                "description":
                comp.description or "No description"
            })

        logger.info(f"Returning {len(competitions_data)} competitions")
        return {"status": "success", "competitions": competitions_data}

    except Exception as e:
        logger.error(f"Failed to get competitions: {str(e)}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to get competitions: {str(e)}")

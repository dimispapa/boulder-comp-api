import uuid
from typing import List, Dict, Any
from sqlmodel import Session
from database.crud.scoring import (create_or_update_marathon_ranking,
                                   create_or_update_marathon_detailed_results,
                                   create_or_update_boulder_beasts_ranking)
from database.models.scoring import (MarathonRanking, MarathonDetailedResults,
                                     BoulderBeastsRanking)
from utils.loggers import logger


def convert_to_python_type(value):
    """Convert NumPy types to native Python types."""
    if str(type(value)).startswith("<class 'numpy"):
        # Convert numpy numeric types to their Python equivalents
        return float(value) if 'float' in str(type(value)) else int(value)
    return value


def convert_nested_types(obj):
    """Recursively convert NumPy types in nested structures to Python types."""
    if isinstance(obj, dict):
        return {k: convert_nested_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_nested_types(item) for item in obj]
    else:
        return convert_to_python_type(obj)


async def store_results(session: Session,
                        comp_id: str,
                        scores: List[Dict[str, Any]],
                        detailed_calculations: List[Dict[str, Any]] = None,
                        is_marathon: bool = False) -> None:
    """
    Store calculation results in the database.

    Args:
        scores: List of score dictionaries for Marathon or Boulder Beasts
        detailed_calculations: Optional list of detailed calculation
                                dictionaries for Marathon
    """
    try:
        # Log the start of the database storage process with counts
        logger.info(f"Starting database storage for competition {comp_id} "
                    f"with {len(scores)} scores")

        # Store scores
        success_count = 0
        detailed_success_count = 0

        if is_marathon:
            # Store Marathon rankings
            for score in scores:
                try:
                    # Create Marathon ranking model
                    logger.debug(
                        f"Creating MarathonRanking for team "
                        f"{score['team_id']} (rank {score['ranking']}) "
                        f"with score {score['normalized_total_score']}")

                    ranking_model = MarathonRanking(
                        competition_id=uuid.UUID(comp_id),
                        team_id=uuid.UUID(score["team_id"]),
                        team_size=int(
                            convert_to_python_type(score["team_size"])),
                        base_score=float(
                            convert_to_python_type(score["base_score"])),
                        volume_bonus=float(
                            convert_to_python_type(score["volume_bonus"])),
                        unique_ascent_bonus=float(
                            convert_to_python_type(
                                score["unique_ascent_bonus"])),
                        team_ascent_bonus=float(
                            convert_to_python_type(
                                score["team_ascent_bonus"])),
                        master_grade_bonus=float(
                            convert_to_python_type(
                                score["master_grade_bonus"])),
                        remote_boulder_bonus=float(
                            convert_to_python_type(
                                score["remote_boulder_bonus"])),
                        total_score=float(
                            convert_to_python_type(score["total_score"])),
                        normalized_total_score=float(
                            convert_to_python_type(
                                score["normalized_total_score"])),
                        marathon_subcategory=score.get("marathon_subcategory"),
                        rank=int(convert_to_python_type(score["ranking"])))

                    # Store in database
                    create_or_update_marathon_ranking(session, ranking_model)
                    success_count += 1

                except Exception as e:
                    logger.error(f"Error storing Marathon ranking for team "
                                 f"{score.get('team_id')}: {str(e)}")

            # Store detailed calculations if available
            if detailed_calculations:
                for calculation in detailed_calculations:
                    try:
                        # Create MarathonDetailedCalculation model
                        logger.debug(
                            "Creating MarathonDetailedResults for team "
                            f"{calculation['team_id']}")

                        # Count team_completed_routes and team_unique_routes
                        # since they should be integers not arrays
                        team_completed_routes_count = len(
                            calculation["team_completed_routes"])
                        team_unique_routes_count = len(
                            calculation["team_unique_routes"])

                        # Convert routes and master_grades to JSONB
                        routes_json = convert_nested_types(
                            calculation["routes"])
                        master_grades_json = convert_nested_types(
                            calculation["master_grades"])

                        # Convert data to proper types for database storage
                        detailed_calc_model = MarathonDetailedResults(
                            competition_id=uuid.UUID(comp_id),
                            team_id=uuid.UUID(calculation["team_id"]),
                            team_name=calculation["team_name"],
                            team_size=int(
                                convert_to_python_type(
                                    calculation["team_size"])),
                            routes=routes_json,
                            total_ascents=int(
                                convert_to_python_type(
                                    calculation["total_ascents"])),
                            # Store the count of completed routes, not the list
                            team_completed_routes=team_completed_routes_count,
                            # Store the count of unique routes, not the list
                            team_unique_routes=team_unique_routes_count,
                            master_grades=master_grades_json,
                            master_grade_bonus=float(
                                convert_to_python_type(
                                    calculation["master_grade_bonus"])),
                            base_score=float(
                                convert_to_python_type(
                                    calculation["base_score"])),
                            team_ascent_bonus=float(
                                convert_to_python_type(
                                    calculation["team_ascent_bonus"])),
                            unique_ascent_bonus=float(
                                convert_to_python_type(
                                    calculation["unique_ascent_bonus"])),
                            remote_boulder_bonus=float(
                                convert_to_python_type(
                                    calculation["remote_boulder_bonus"])),
                            total_score=float(
                                convert_to_python_type(
                                    calculation["total_score"])),
                            normalized_base_score=float(
                                convert_to_python_type(
                                    calculation["normalized_base_score"])),
                            volume_bonus=float(
                                convert_to_python_type(
                                    calculation["volume_bonus"])),
                            normalized_team_ascent_bonus=float(
                                convert_to_python_type(
                                    calculation["normalized_team_ascent_bonus"]
                                )),
                            normalized_unique_ascent_bonus=float(
                                convert_to_python_type(calculation[
                                    "normalized_unique_ascent_bonus"])),
                            normalized_master_grade_bonus=float(
                                convert_to_python_type(calculation[
                                    "normalized_master_grade_bonus"])),
                            normalized_remote_boulder_bonus=float(
                                convert_to_python_type(calculation[
                                    "normalized_remote_boulder_bonus"])),
                            normalized_total_score=float(
                                convert_to_python_type(
                                    calculation["normalized_total_score"])),
                            marathon_subcategory=calculation.get(
                                "marathon_subcategory"),
                            rank=int(
                                convert_to_python_type(
                                    calculation["ranking"])))

                        # Store in database
                        create_or_update_marathon_detailed_results(
                            session, detailed_calc_model)
                        detailed_success_count += 1

                    except Exception as e:
                        logger.error(
                            f"Error storing Marathon calculation details "
                            f"for team {calculation.get('team_id')}: "
                            f"{str(e)}",
                            exc_info=True)
        else:
            # Store Boulder Beasts rankings
            for score in scores:
                try:
                    # Create Boulder Beasts ranking model
                    logger.debug(
                        "Creating BoulderBeastsRanking for participant "
                        f"{score['participant_id']} "
                        f"(rank {score['ranking']}) "
                        f"with score {score['total_score']}")

                    # Convert top_5_routes to a list of strings if it exists
                    top_5_routes = score.get("top_5_routes", [])
                    if top_5_routes:
                        top_5_routes = [str(route) for route in top_5_routes]

                    ranking_model = BoulderBeastsRanking(
                        competition_id=uuid.UUID(comp_id),
                        participant_id=uuid.UUID(score["participant_id"]),
                        total_score=float(
                            convert_to_python_type(score["total_score"])),
                        top_5_routes=top_5_routes,
                        top_5_routes_score=float(
                            convert_to_python_type(
                                score["top_5_routes_score"])),
                        rank=int(convert_to_python_type(score["ranking"])))

                    # Store in database
                    create_or_update_boulder_beasts_ranking(
                        session, ranking_model)
                    success_count += 1

                except Exception as e:
                    logger.error(
                        f"Error storing Boulder Beasts ranking "
                        f"for participant {score.get('participant_id')}: "
                        f"{str(e)}")

        logger.info(
            f"Completed database storage for competition {comp_id}. "
            f"Stored {success_count}/{len(scores)} scores" +
            (f" and {detailed_success_count}/{len(detailed_calculations)} "
             "detailed results." if detailed_calculations else "."))

    except Exception as e:
        logger.error(f"Error storing results for competition {comp_id}: "
                     f"{str(e)}")
        raise

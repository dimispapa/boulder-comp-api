import uuid
from typing import List, Dict, Any
from sqlmodel import Session
from database.crud.scoring import (create_or_update_marathon_ranking,
                                   create_or_update_marathon_detailed_results,
                                   create_or_update_boulder_beasts_ranking)
from database.models.scoring import (MarathonRanking, MarathonDetailedResults,
                                     BoulderBeastsRanking)
from utils.loggers import logger


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
                        f"with score {score['normalized_score']}")

                    ranking_model = MarathonRanking(
                        competition_id=uuid.UUID(comp_id),
                        team_id=uuid.UUID(score["team_id"]),
                        team_size=score["team_size"],
                        base_score=score["base_score"],
                        volume_bonus=score["volume_bonus"],
                        unique_ascent_bonus=score["unique_ascent_bonus"],
                        team_ascent_bonus=score["team_ascent_bonus"],
                        master_grade_bonus=score["master_grade_bonus"],
                        total_score=score["total_score"],
                        normalized_score=score["normalized_score"],
                        rank=score["ranking"])

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

                        # Convert data to proper types for database storage
                        detailed_calc_model = MarathonDetailedResults(
                            competition_id=uuid.UUID(comp_id),
                            team_id=uuid.UUID(calculation["team_id"]),
                            team_name=calculation["team_name"],
                            team_size=calculation["team_size"],
                            routes=calculation["routes"],
                            total_ascents=calculation["total_ascents"],
                            volume_bonus=calculation["volume_bonus"],
                            team_completed_routes=calculation[
                                "team_completed_routes"],
                            team_unique_routes=calculation[
                                "team_unique_routes"],
                            master_grades=calculation["master_grades"],
                            master_grade_bonus=calculation[
                                "master_grade_bonus"],
                            base_score=calculation["base_score"],
                            team_ascent_bonus=calculation["team_ascent_bonus"],
                            unique_ascent_bonus=calculation[
                                "unique_ascent_bonus"],
                            total_score=calculation["total_score"],
                            normalized_score=calculation["normalized_score"])

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

                    ranking_model = BoulderBeastsRanking(
                        competition_id=uuid.UUID(comp_id),
                        participant_id=uuid.UUID(score["participant_id"]),
                        total_score=score["total_score"],
                        top_5_routes=score["top_5_routes"],
                        top_5_routes_score=score["top_5_routes_score"],
                        rank=score["ranking"])

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

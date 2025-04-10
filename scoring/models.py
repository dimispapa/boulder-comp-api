"""
Pydantic models for scoring calculations and API requests/responses.
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union


# Request models
class ScoreCalculationRequest(BaseModel):
    """
    Request model for score calculation.
    """
    competition_id: str = Field(..., description="ID of the competition")
    category: Optional[str] = Field(
        None,
        description="Category to calculate: marathon, boulder_beasts, "
        "or None for both")


# Response models
class ScoreCalculationResponse(BaseModel):
    """
    Response model for score calculation task.
    """
    task_id: str = Field(..., description="ID of the calculation task")
    status: str = Field(..., description="Status of the calculation task")
    message: str = Field(..., description="Message describing the task status")


class MarathonScoreComponents(BaseModel):
    """
    Component scores for Marathon category.
    """
    base_score: float = Field(...,
                              description="Base score from completed ascents")
    volume_score: float = Field(..., description="Bonus for volume of ascents")
    unique_ascent_score: float = Field(...,
                                       description="Score from unique ascents")
    team_ascent_bonus: float = Field(
        ..., description="Bonus for team route completions")
    master_grade_bonus: float = Field(
        ..., description="Bonus for most ascents at grade")


class MarathonTeamRanking(BaseModel):
    """
    Marathon team ranking model.
    """
    team_id: str = Field(..., description="ID of the team")
    name: str = Field(..., description="Name of the team")
    team_size: int = Field(...,
                           description="Number of participants in the team")
    score: float = Field(..., description="Total normalized team score")
    rank: int = Field(..., description="Team ranking position")
    components: MarathonScoreComponents = Field(...,
                                                description="Score components")


class BoulderBeastsParticipantRanking(BaseModel):
    """
    Boulder Beasts participant ranking model.
    """
    participant_id: str = Field(..., description="ID of the participant")
    name: str = Field(..., description="Name of the participant")
    team_id: Optional[str] = Field(None, description="ID of the team (if any)")
    is_solo: bool = Field(..., description="Whether participant is solo")
    score: float = Field(..., description="Total participant score")
    rank: int = Field(..., description="Participant ranking position")
    top_grades: List[str] = Field(..., description="Top 5 grades climbed")


class MarathonLeaderboard(BaseModel):
    """
    Marathon category leaderboard.
    """
    competition_id: str = Field(..., description="ID of the competition")
    category: str = Field("marathon", description="Category name")
    teams: List[MarathonTeamRanking] = Field(
        ..., description="List of team rankings")


class BoulderBeastsLeaderboard(BaseModel):
    """
    Boulder Beasts category leaderboard.
    """
    competition_id: str = Field(..., description="ID of the competition")
    category: str = Field("boulder_beasts", description="Category name")
    participants: List[BoulderBeastsParticipantRanking] = Field(
        ..., description="List of participant rankings")


class CombinedLeaderboard(BaseModel):
    """
    Combined leaderboard with both categories.
    """
    status: str = Field("success", description="Status of the response")
    marathon: Optional[MarathonLeaderboard] = Field(
        None, description="Marathon leaderboard")
    boulder_beasts: Optional[BoulderBeastsLeaderboard] = Field(
        None, description="Boulder Beasts leaderboard")


class LeaderboardResponse(BaseModel):
    """
    API response for leaderboard endpoint.
    """
    status: str = Field("success", description="Status of the response")
    leaderboard: Union[MarathonLeaderboard, BoulderBeastsLeaderboard] = Field(
        ..., description="Leaderboard data")


class SingleCategoryRankingsResponse(BaseModel):
    """
    API response for a single category's rankings.
    """
    status: str = Field("success", description="Status of the response")
    rankings: List[Dict[str, Any]] = Field(
        ..., description="Raw ranking data from database")


class CombinedRankingsResponse(BaseModel):
    """
    API response for combined rankings.
    """
    status: str = Field("success", description="Status of the response")
    marathon: List[Dict[str,
                        Any]] = Field(...,
                                      description="Marathon rankings data")
    boulder_beasts: List[Dict[str, Any]] = Field(
        ..., description="Boulder Beasts rankings data")


class ErrorResponse(BaseModel):
    """
    API error response.
    """
    detail: str = Field(..., description="Error details")

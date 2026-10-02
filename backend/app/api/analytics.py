from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.analytics.service import (
    game_result,
    player_availability,
    player_period_summary,
    team_record,
    team_record_when_player_reaches,
)
from backend.app.database import get_session
from backend.app.schemas import AnalyticsResult

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])
SessionDependency = Annotated[Session, Depends(get_session)]
PositiveId = Annotated[int, Query(gt=0)]
NonnegativeThreshold = Annotated[int, Query(ge=0)]
GameType = Literal["Regular Season", "Emirates NBA Cup", "Play-in Tournament", "Playoffs"]


def _validate_dates(start_date: date, end_date: date) -> None:
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date")


@router.get("/game-result", response_model=AnalyticsResult)
def game_result_endpoint(
    team_id: PositiveId,
    opponent_team_id: PositiveId,
    game_date: date,
    session: SessionDependency,
) -> AnalyticsResult:
    return game_result(
        session,
        team_id=team_id,
        opponent_team_id=opponent_team_id,
        game_date=game_date,
    )


@router.get("/player-summary", response_model=AnalyticsResult)
def player_summary_endpoint(
    player_id: PositiveId,
    start_date: date,
    end_date: date,
    session: SessionDependency,
    team_id: PositiveId | None = None,
    game_type: GameType = "Regular Season",
) -> AnalyticsResult:
    _validate_dates(start_date, end_date)
    return player_period_summary(
        session,
        player_id=player_id,
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
        game_type=game_type,
    )


@router.get("/team-record", response_model=AnalyticsResult)
def team_record_endpoint(
    team_id: PositiveId,
    start_date: date,
    end_date: date,
    session: SessionDependency,
    game_type: GameType = "Regular Season",
) -> AnalyticsResult:
    _validate_dates(start_date, end_date)
    return team_record(
        session,
        team_id=team_id,
        start_date=start_date,
        end_date=end_date,
        game_type=game_type,
    )


@router.get("/threshold-record", response_model=AnalyticsResult)
def threshold_record_endpoint(
    team_id: PositiveId,
    player_id: PositiveId,
    stat: str,
    session: SessionDependency,
    threshold: NonnegativeThreshold,
    start_date: date = date(2025, 10, 1),
    end_date: date = date(2026, 6, 30),
    game_type: GameType = "Regular Season",
) -> AnalyticsResult:
    _validate_dates(start_date, end_date)
    return team_record_when_player_reaches(
        session,
        team_id=team_id,
        player_id=player_id,
        stat=stat,
        threshold=threshold,
        start_date=start_date,
        end_date=end_date,
        game_type=game_type,
    )


@router.get("/player-availability", response_model=AnalyticsResult)
def player_availability_endpoint(
    player_id: PositiveId,
    team_id: PositiveId,
    game_date: date,
    session: SessionDependency,
    opponent_team_id: PositiveId | None = None,
) -> AnalyticsResult:
    return player_availability(
        session,
        player_id=player_id,
        team_id=team_id,
        game_date=game_date,
        opponent_team_id=opponent_team_id,
    )

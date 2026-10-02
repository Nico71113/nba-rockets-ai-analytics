from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import get_session
from backend.app.models import Game, PlayerGameStat, TeamGameStat
from backend.app.schemas import CoverageResponse

router = APIRouter(prefix="/api/v1", tags=["coverage"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/coverage", response_model=CoverageResponse)
def coverage(session: SessionDependency) -> CoverageResponse:
    season_id = get_settings().season_id
    game_metrics = session.execute(
        select(
            func.min(Game.game_date),
            func.max(Game.game_date),
            func.count(Game.game_id),
        ).where(Game.season_id == season_id)
    ).one()
    return CoverageResponse(
        season_id=season_id,
        first_game_date=game_metrics[0],
        last_game_date=game_metrics[1],
        games=game_metrics[2],
        teams=session.scalar(
            select(func.count(func.distinct(TeamGameStat.team_id)))
            .join(Game, Game.game_id == TeamGameStat.game_id)
            .where(Game.season_id == season_id)
        )
        or 0,
        players=session.scalar(
            select(func.count(func.distinct(PlayerGameStat.player_id)))
            .join(Game, Game.game_id == PlayerGameStat.game_id)
            .where(Game.season_id == season_id)
        )
        or 0,
        player_game_rows=session.scalar(
            select(func.count())
            .select_from(PlayerGameStat)
            .join(Game, Game.game_id == PlayerGameStat.game_id)
            .where(Game.season_id == season_id)
        )
        or 0,
        team_game_rows=session.scalar(
            select(func.count())
            .select_from(TeamGameStat)
            .join(Game, Game.game_id == TeamGameStat.game_id)
            .where(Game.season_id == season_id)
        )
        or 0,
    )

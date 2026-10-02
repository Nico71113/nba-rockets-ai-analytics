from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from backend.app.database import get_session
from backend.app.models import Game, Team
from backend.app.schemas import GameEvidenceRow

router = APIRouter(prefix="/api/v1/evidence", tags=["evidence"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/games", response_model=list[GameEvidenceRow])
def evidence_games(
    game_ids: Annotated[str, Query(min_length=1)],
    session: SessionDependency,
) -> list[GameEvidenceRow]:
    requested = list(dict.fromkeys(value.strip() for value in game_ids.split(",") if value.strip()))
    if not requested:
        raise HTTPException(status_code=422, detail="At least one game ID is required")
    if len(requested) > 100:
        raise HTTPException(status_code=422, detail="At most 100 game IDs can be inspected")

    home_team = aliased(Team)
    away_team = aliased(Team)
    winner_team = aliased(Team)
    rows = session.execute(
        select(Game, home_team.name, away_team.name, winner_team.name)
        .join(home_team, home_team.team_id == Game.home_team_id)
        .join(away_team, away_team.team_id == Game.away_team_id)
        .join(winner_team, winner_team.team_id == Game.winner_team_id)
        .where(Game.game_id.in_(requested))
        .order_by(Game.game_date, Game.game_id)
    ).all()
    return [
        GameEvidenceRow(
            game_id=game.game_id,
            game_date=game.game_date,
            game_type=game.game_type,
            away_team=away_name,
            home_team=home_name,
            away_score=game.away_score,
            home_score=game.home_score,
            winner=winner_name,
        )
        for game, home_name, away_name, winner_name in rows
    ]

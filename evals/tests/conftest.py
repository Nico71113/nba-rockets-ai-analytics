from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.models import Base, Game, Player, PlayerGameStat, Team, TeamGameStat

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = PROJECT_ROOT / "evals" / "fixtures"


def load_json(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _game(values: dict[str, Any]) -> Game:
    converted = dict(values)
    converted["tipoff_at"] = datetime.fromisoformat(converted["tipoff_at"])
    converted["game_date"] = date.fromisoformat(converted["game_date"])
    return Game(**converted)


def _team_game_stat(values: dict[str, Any]) -> TeamGameStat:
    converted = {
        "assists": 20,
        "blocks": 5,
        "steals": 7,
        "field_goals_attempted": 80,
        "field_goals_made": 40,
        "field_goal_percentage": Decimal("0.5000"),
        "three_pointers_attempted": 30,
        "three_pointers_made": 10,
        "three_point_percentage": Decimal("0.3333"),
        "free_throws_attempted": 20,
        "free_throws_made": 10,
        "free_throw_percentage": Decimal("0.5000"),
        "defensive_rebounds": 30,
        "offensive_rebounds": 10,
        "total_rebounds": 40,
        "personal_fouls": 18,
        "turnovers": 12,
        "minutes_seconds": 14_400,
        **values,
    }
    converted["plus_minus"] = converted["team_score"] - converted["opponent_score"]
    return TeamGameStat(**converted)


def _player_game_stat(values: dict[str, Any]) -> PlayerGameStat:
    converted = dict(values)
    if minutes := converted.pop("minutes", None):
        converted["minutes_seconds"] = round(Decimal(minutes) * 60)
    if rebounds := converted.get("total_rebounds"):
        converted["offensive_rebounds"] = 1
        converted["defensive_rebounds"] = rebounds - 1
    return PlayerGameStat(**converted)


@pytest.fixture
def eval_snapshot() -> dict[str, Any]:
    return load_json("mini_snapshot.json")


@pytest.fixture
def eval_session(eval_snapshot: dict[str, Any]):
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(Team(**row) for row in eval_snapshot["teams"])
        session.add_all(Player(**row) for row in eval_snapshot["players"])
        session.add_all(_game(row) for row in eval_snapshot["games"])
        session.add_all(_team_game_stat(row) for row in eval_snapshot["team_game_stats"])
        session.add_all(_player_game_stat(row) for row in eval_snapshot["player_game_stats"])
        session.commit()
        yield session
    engine.dispose()

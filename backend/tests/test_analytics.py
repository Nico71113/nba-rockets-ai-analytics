from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.analytics.service import (
    game_result,
    player_period_summary,
    team_record,
    team_record_when_player_reaches,
)
from backend.app.models import Base, Game, Player, PlayerGameStat, Team, TeamGameStat

HOU = 1610612745
OKC = 1610612760
DURANT = 201142


@pytest.fixture
def session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    eastern = ZoneInfo("America/New_York")
    with Session(engine) as session:
        session.add_all(
            [
                Team(team_id=HOU, name="Houston Rockets"),
                Team(team_id=OKC, name="Oklahoma City Thunder"),
                Player(player_id=DURANT, first_name="Kevin", last_name="Durant"),
                Game(
                    game_id="g1",
                    season_id="2025-26",
                    tipoff_at=datetime(2026, 1, 5, 20, tzinfo=eastern),
                    game_date=date(2026, 1, 5),
                    game_type="Regular Season",
                    home_team_id=HOU,
                    away_team_id=OKC,
                    home_score=110,
                    away_score=100,
                    winner_team_id=HOU,
                ),
                Game(
                    game_id="g2",
                    season_id="2025-26",
                    tipoff_at=datetime(2026, 1, 7, 20, tzinfo=eastern),
                    game_date=date(2026, 1, 7),
                    game_type="Regular Season",
                    home_team_id=OKC,
                    away_team_id=HOU,
                    home_score=105,
                    away_score=102,
                    winner_team_id=OKC,
                ),
            ]
        )
        session.add_all(
            [
                TeamGameStat(
                    game_id="g1",
                    team_id=HOU,
                    opponent_team_id=OKC,
                    is_home=True,
                    won=True,
                    team_score=110,
                    opponent_score=100,
                    assists=25,
                    blocks=5,
                    steals=7,
                    field_goals_attempted=90,
                    field_goals_made=42,
                    field_goal_percentage=Decimal("0.4667"),
                    three_pointers_attempted=35,
                    three_pointers_made=13,
                    three_point_percentage=Decimal("0.3714"),
                    free_throws_attempted=17,
                    free_throws_made=13,
                    free_throw_percentage=Decimal("0.7647"),
                    defensive_rebounds=30,
                    offensive_rebounds=10,
                    total_rebounds=40,
                    personal_fouls=18,
                    turnovers=12,
                    plus_minus=10,
                    minutes_seconds=14_400,
                ),
                TeamGameStat(
                    game_id="g1",
                    team_id=OKC,
                    opponent_team_id=HOU,
                    is_home=False,
                    won=False,
                    team_score=100,
                    opponent_score=110,
                    assists=22,
                    blocks=4,
                    steals=6,
                    field_goals_attempted=88,
                    field_goals_made=39,
                    field_goal_percentage=Decimal("0.4432"),
                    three_pointers_attempted=33,
                    three_pointers_made=11,
                    three_point_percentage=Decimal("0.3333"),
                    free_throws_attempted=15,
                    free_throws_made=11,
                    free_throw_percentage=Decimal("0.7333"),
                    defensive_rebounds=28,
                    offensive_rebounds=9,
                    total_rebounds=37,
                    personal_fouls=19,
                    turnovers=14,
                    plus_minus=-10,
                    minutes_seconds=14_400,
                ),
                TeamGameStat(
                    game_id="g2",
                    team_id=HOU,
                    opponent_team_id=OKC,
                    is_home=False,
                    won=False,
                    team_score=102,
                    opponent_score=105,
                    assists=24,
                    blocks=6,
                    steals=8,
                    field_goals_attempted=91,
                    field_goals_made=40,
                    field_goal_percentage=Decimal("0.4396"),
                    three_pointers_attempted=36,
                    three_pointers_made=12,
                    three_point_percentage=Decimal("0.3333"),
                    free_throws_attempted=13,
                    free_throws_made=10,
                    free_throw_percentage=Decimal("0.7692"),
                    defensive_rebounds=31,
                    offensive_rebounds=8,
                    total_rebounds=39,
                    personal_fouls=20,
                    turnovers=13,
                    plus_minus=-3,
                    minutes_seconds=14_400,
                ),
                TeamGameStat(
                    game_id="g2",
                    team_id=OKC,
                    opponent_team_id=HOU,
                    is_home=True,
                    won=True,
                    team_score=105,
                    opponent_score=102,
                    assists=26,
                    blocks=5,
                    steals=9,
                    field_goals_attempted=89,
                    field_goals_made=41,
                    field_goal_percentage=Decimal("0.4607"),
                    three_pointers_attempted=34,
                    three_pointers_made=12,
                    three_point_percentage=Decimal("0.3529"),
                    free_throws_attempted=14,
                    free_throws_made=11,
                    free_throw_percentage=Decimal("0.7857"),
                    defensive_rebounds=29,
                    offensive_rebounds=11,
                    total_rebounds=40,
                    personal_fouls=17,
                    turnovers=11,
                    plus_minus=3,
                    minutes_seconds=14_400,
                ),
                PlayerGameStat(
                    game_id="g1",
                    player_id=DURANT,
                    team_id=HOU,
                    opponent_team_id=OKC,
                    is_home=True,
                    won=True,
                    did_play=True,
                    minutes_seconds=2_190,
                    points=35,
                    total_rebounds=7,
                    defensive_rebounds=6,
                    offensive_rebounds=1,
                    assists=5,
                ),
                PlayerGameStat(
                    game_id="g2",
                    player_id=DURANT,
                    team_id=HOU,
                    opponent_team_id=OKC,
                    is_home=False,
                    won=False,
                    did_play=True,
                    minutes_seconds=2_280,
                    points=25,
                    total_rebounds=9,
                    defensive_rebounds=8,
                    offensive_rebounds=1,
                    assists=4,
                ),
            ]
        )
        session.commit()
        yield session
    engine.dispose()


def test_player_period_summary_uses_exact_rows(session):
    result = player_period_summary(
        session,
        player_id=DURANT,
        team_id=HOU,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert result.method == "sql"
    assert result.metrics["games_played"] == 2
    assert result.metrics["total_points"] == 60
    assert result.metrics["points_per_game"] == 30.0
    assert result.evidence[0].game_ids == ["g1", "g2"]


def test_team_record_and_threshold_record(session):
    record = team_record(
        session,
        team_id=HOU,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )
    threshold = team_record_when_player_reaches(
        session,
        team_id=HOU,
        player_id=DURANT,
        stat="points",
        threshold=30,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert record.metrics == {"games": 2, "wins": 1, "losses": 1}
    assert threshold.metrics["games"] == 1
    assert threshold.metrics["wins"] == 1


def test_game_result_and_explicit_refusals(session):
    result = game_result(
        session,
        team_id=HOU,
        opponent_team_id=OKC,
        game_date=date(2026, 1, 5),
    )
    unsupported = team_record_when_player_reaches(
        session,
        team_id=HOU,
        player_id=DURANT,
        stat="defensive_assignment",
        threshold=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )
    missing = player_period_summary(
        session,
        player_id=DURANT,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
    )

    assert result.method == "sql"
    assert "Houston Rockets won" in result.answer
    assert unsupported.method == "refusal"
    assert "Supported player stats" in unsupported.coverage_note
    assert missing.method == "refusal"
    assert "No played games" in missing.answer

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import Game, PlayerGameStat, TeamGameStat
from evals.tests.conftest import PROJECT_ROOT, load_json
from ingestion.load_postgres import _player_game_row

HOUSTON_ROCKETS = "1610612745"
KEVIN_DURANT = "201142"
NUMERIC_PLAYER_FIELDS = (
    "minutes_seconds",
    "points",
    "assists",
    "blocks",
    "steals",
    "field_goal_percentage",
    "three_point_percentage",
    "free_throw_percentage",
    "total_rebounds",
    "turnovers",
    "plus_minus",
)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _bool(value: str) -> bool:
    return value.lower() == "true"


def test_synthetic_fixture_relational_invariants(eval_session: Session) -> None:
    games = list(eval_session.scalars(select(Game)))
    assert len(games) == 5

    for game in games:
        team_rows = list(
            eval_session.scalars(select(TeamGameStat).where(TeamGameStat.game_id == game.game_id))
        )
        assert len(team_rows) == 2
        assert {row.team_id for row in team_rows} == {
            game.home_team_id,
            game.away_team_id,
        }
        assert sum(row.won for row in team_rows) == 1
        for row in team_rows:
            assert row.opponent_team_id in {game.home_team_id, game.away_team_id}
            assert row.opponent_team_id != row.team_id
            assert row.is_home is (row.team_id == game.home_team_id)
            assert row.won is (row.team_id == game.winner_team_id)

    for player_row in eval_session.scalars(select(PlayerGameStat)):
        team_row = eval_session.get(TeamGameStat, (player_row.game_id, player_row.team_id))
        assert team_row is not None
        assert player_row.opponent_team_id == team_row.opponent_team_id
        assert player_row.is_home is team_row.is_home
        assert player_row.won is team_row.won
        if not player_row.did_play:
            assert player_row.minutes_seconds is None
            assert player_row.points is None
            assert player_row.assists is None
            assert player_row.total_rebounds is None


def test_source_manifest_has_unique_verifiable_file_records() -> None:
    manifest = json.loads(
        (PROJECT_ROOT / "data" / "manifests" / "source_snapshot.lock.json").read_text(
            encoding="utf-8"
        )
    )
    files = manifest["files"]

    assert manifest["schema_version"] == 1
    assert manifest["declared_license"] == "CC0: Public Domain"
    assert len({entry["name"] for entry in files}) == len(files)
    assert all(entry["bytes"] > 0 for entry in files)
    assert all(len(entry["sha256"]) == 64 for entry in files)
    assert all(set(entry["sha256"]) <= set("0123456789abcdef") for entry in files)


def test_normalized_snapshot_relational_integrity_if_present() -> None:
    processed = PROJECT_ROOT / "data" / "processed"
    paths = {
        "games": processed / "games.csv",
        "teams": processed / "team_game_stats.csv",
        "players": processed / "players.csv",
        "player_games": processed / "player_game_stats.csv",
    }
    if not all(path.is_file() for path in paths.values()):
        pytest.skip("Run the normalization pipeline to enable the snapshot integrity eval")

    expected = load_json("source_snapshot_expectations.json")["counts"]
    games = _rows(paths["games"])
    team_rows = _rows(paths["teams"])
    players = _rows(paths["players"])
    player_rows = _rows(paths["player_games"])
    games_by_id = {row["game_id"]: row for row in games}

    assert len(games) == expected["games"]
    assert len(games_by_id) == len(games)
    assert len(team_rows) == expected["team_game_rows"]
    assert len(player_rows) == expected["player_game_rows"]
    assert len(players) == expected["players"]
    assert len({row["player_id"] for row in players}) == len(players)

    team_rows_by_game: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in team_rows:
        game = games_by_id[row["game_id"]]
        team_rows_by_game[row["game_id"]].append(row)
        assert {row["team_id"], row["opponent_team_id"]} == {
            game["home_team_id"],
            game["away_team_id"],
        }
        expected_home = row["team_id"] == game["home_team_id"]
        assert _bool(row["is_home"]) is expected_home
        expected_score = game["home_score"] if expected_home else game["away_score"]
        opponent_score = game["away_score"] if expected_home else game["home_score"]
        assert row["team_score"] == expected_score
        assert row["opponent_score"] == opponent_score
        assert _bool(row["won"]) is (row["team_id"] == game["winner_team_id"])

    assert set(team_rows_by_game) == set(games_by_id)
    assert all(len(rows) == 2 for rows in team_rows_by_game.values())
    assert all(sum(_bool(row["won"]) for row in rows) == 1 for rows in team_rows_by_game.values())

    regular_games = [row for row in games if row["game_type"] == "Regular Season"]
    regular_teams = {
        team_id for row in regular_games for team_id in (row["home_team_id"], row["away_team_id"])
    }
    rockets_regular_ids = {
        row["game_id"]
        for row in regular_games
        if HOUSTON_ROCKETS in (row["home_team_id"], row["away_team_id"])
    }
    assert len(regular_games) == expected["regular_season_games"]
    assert len(regular_teams) == expected["regular_season_teams"]
    assert len(rockets_regular_ids) == expected["rockets_regular_season_games"]

    durant_regular_ids: set[str] = set()
    durant_regular_dnp = 0
    player_key_counts: Counter[tuple[str, str]] = Counter()
    for row in player_rows:
        game = games_by_id[row["game_id"]]
        player_key_counts[(row["game_id"], row["player_id"])] += 1
        assert {row["team_id"], row["opponent_team_id"]} == {
            game["home_team_id"],
            game["away_team_id"],
        }
        assert _bool(row["is_home"]) is (row["team_id"] == game["home_team_id"])
        assert _bool(row["won"]) is (row["team_id"] == game["winner_team_id"])

        if not _bool(row["did_play"]):
            converted = _player_game_row(row)
            assert all(converted[field] is None for field in NUMERIC_PLAYER_FIELDS)

        if (
            row["player_id"] == KEVIN_DURANT
            and row["team_id"] == HOUSTON_ROCKETS
            and row["game_type"] == "Regular Season"
        ):
            durant_regular_ids.add(row["game_id"])
            durant_regular_dnp += not _bool(row["did_play"])

    assert max(player_key_counts.values(), default=0) == 1
    assert len(durant_regular_ids) == expected["durant_rockets_regular_season_rows"]
    assert durant_regular_dnp == expected["durant_rockets_regular_season_dnp_rows"]
    assert len(rockets_regular_ids - durant_regular_ids) == 4


def test_fixture_count_matches_database(eval_session: Session) -> None:
    assert eval_session.scalar(select(func.count()).select_from(Game)) == 5
    assert eval_session.scalar(select(func.count()).select_from(TeamGameStat)) == 10
    assert eval_session.scalar(select(func.count()).select_from(PlayerGameStat)) == 5


def test_full_snapshot_golden_numbers_if_present() -> None:
    processed = PROJECT_ROOT / "data" / "processed"
    team_path = processed / "team_game_stats.csv"
    player_path = processed / "player_game_stats.csv"
    game_path = processed / "games.csv"
    if not all(path.is_file() for path in (team_path, player_path, game_path)):
        pytest.skip("Run the normalization pipeline to enable full-snapshot golden numbers")

    team_rows = _rows(team_path)
    player_rows = _rows(player_path)
    games = _rows(game_path)
    rockets = [
        row
        for row in team_rows
        if row["team_id"] == HOUSTON_ROCKETS and row["game_type"] == "Regular Season"
    ]
    thunder = [
        row
        for row in team_rows
        if row["team_name"] == "Oklahoma City Thunder"
        and row["game_type"] == "Regular Season"
    ]
    durant = [
        row
        for row in player_rows
        if row["player_id"] == KEVIN_DURANT
        and row["team_id"] == HOUSTON_ROCKETS
        and row["game_type"] == "Regular Season"
        and _bool(row["did_play"])
    ]

    assert (len(rockets), sum(_bool(row["won"]) for row in rockets)) == (82, 52)
    home = [row for row in rockets if _bool(row["is_home"])]
    away = [row for row in rockets if not _bool(row["is_home"])]
    assert (len(home), sum(_bool(row["won"]) for row in home)) == (41, 30)
    assert (len(away), sum(_bool(row["won"]) for row in away)) == (41, 22)
    assert (len(thunder), sum(_bool(row["won"]) for row in thunder)) == (82, 64)

    assert len(durant) == 78
    assert sum(int(row["points"]) for row in durant) == 2026
    assert round(sum(int(row["points"]) for row in durant) / len(durant), 1) == 26.0
    assert sum(int(row["total_rebounds"]) for row in durant) == 426
    assert round(sum(int(row["assists"]) for row in durant) / len(durant), 1) == 4.8
    road_durant = [row for row in durant if not _bool(row["is_home"])]
    assert (len(road_durant), max(int(row["points"]) for row in road_durant)) == (38, 40)

    def threshold_record(field: str, threshold: int) -> tuple[int, int]:
        matching = [row for row in durant if int(row[field]) >= threshold]
        return len(matching), sum(_bool(row["won"]) for row in matching)

    assert threshold_record("points", 20) == (64, 40)
    assert threshold_record("points", 30) == (29, 16)
    assert threshold_record("three_pointers_made", 4) == (17, 11)
    assert threshold_record("total_rebounds", 10) == (4, 2)

    january = [row for row in rockets if row["game_date"].startswith("2026-01-")]
    home_wins = [row for row in rockets if _bool(row["is_home"]) and _bool(row["won"])]
    assert (len(january), sum(int(row["team_score"]) for row in january)) == (17, 1834)
    assert round(sum(int(row["plus_minus"]) for row in home_wins) / len(home_wins), 1) == 13.4
    assert round(sum(int(row["opponent_score"]) for row in rockets) / len(rockets), 1) == 110.0
    assert max(int(row["team_score"]) for row in rockets) == 140

    opener = next(
        row
        for row in games
        if row["game_date"] == "2025-10-21"
        and {row["home_team_name"], row["away_team_name"]}
        == {"Houston Rockets", "Oklahoma City Thunder"}
    )
    assert (opener["away_score"], opener["home_score"], opener["winner_team_id"]) == (
        "124",
        "125",
        "1610612760",
    )

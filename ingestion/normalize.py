"""Stream the large source CSVs into a compact 2025-26 canonical dataset."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from ingestion.config import (
    INCLUDED_GAME_TYPES,
    PROCESSED_DIR,
    RAW_DIR,
    SEASON_END_EXCLUSIVE,
    SEASON_ID,
    SEASON_START,
)

GAME_FIELDS = (
    "season_id",
    "game_id",
    "game_datetime_est",
    "game_date",
    "game_type",
    "home_team_id",
    "home_team_name",
    "away_team_id",
    "away_team_name",
    "home_score",
    "away_score",
    "winner_team_id",
    "attendance",
    "arena_name",
)

TEAM_GAME_FIELDS = (
    "season_id",
    "game_id",
    "game_date",
    "game_type",
    "team_id",
    "team_name",
    "opponent_team_id",
    "opponent_team_name",
    "is_home",
    "won",
    "team_score",
    "opponent_score",
    "assists",
    "blocks",
    "steals",
    "field_goals_attempted",
    "field_goals_made",
    "field_goal_percentage",
    "three_pointers_attempted",
    "three_pointers_made",
    "three_point_percentage",
    "free_throws_attempted",
    "free_throws_made",
    "free_throw_percentage",
    "defensive_rebounds",
    "offensive_rebounds",
    "total_rebounds",
    "personal_fouls",
    "turnovers",
    "plus_minus",
    "minutes",
)

PLAYER_GAME_FIELDS = (
    "season_id",
    "game_id",
    "game_date",
    "game_type",
    "player_id",
    "first_name",
    "last_name",
    "team_id",
    "team_name",
    "opponent_team_id",
    "opponent_team_name",
    "is_home",
    "won",
    "did_play",
    "minutes",
    "points",
    "assists",
    "blocks",
    "steals",
    "field_goals_attempted",
    "field_goals_made",
    "field_goal_percentage",
    "three_pointers_attempted",
    "three_pointers_made",
    "three_point_percentage",
    "free_throws_attempted",
    "free_throws_made",
    "free_throw_percentage",
    "defensive_rebounds",
    "offensive_rebounds",
    "total_rebounds",
    "personal_fouls",
    "turnovers",
    "plus_minus",
    "availability_comment",
    "starting_position",
)


def _parse_datetime(value: str) -> datetime | None:
    value = (value or "").strip()
    return datetime.fromisoformat(value) if value else None


def _within_season(value: str) -> bool:
    parsed = _parse_datetime(value)
    return bool(parsed and SEASON_START <= parsed.date() < SEASON_END_EXCLUSIVE)


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _matches_game_teams(
    game: dict[str, str], team_id: str, opponent_team_id: str
) -> bool:
    return {team_id, opponent_team_id} == {
        game["home_team_id"],
        game["away_team_id"],
    }


@contextmanager
def _atomic_writer(path: Path, fields: tuple[str, ...]) -> Iterator[csv.DictWriter]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        yield writer
    temporary.replace(path)


def normalize_games() -> dict[str, dict[str, str]]:
    source = RAW_DIR / "Games.csv"
    destination = PROCESSED_DIR / "games.csv"
    games: dict[str, dict[str, str]] = {}

    with source.open(newline="", encoding="utf-8-sig") as handle, _atomic_writer(
        destination, GAME_FIELDS
    ) as writer:
        for row in csv.DictReader(handle):
            if not _within_season(row["gameDate"]) or row["gameType"] not in INCLUDED_GAME_TYPES:
                continue
            game = {
                "season_id": SEASON_ID,
                "game_id": _clean(row["gameId"]),
                "game_datetime_est": _clean(row["gameDateTimeEst"]),
                "game_date": _clean(row["gameDate"])[:10],
                "game_type": _clean(row["gameType"]),
                "home_team_id": _clean(row["hometeamId"]),
                "home_team_name": f"{_clean(row['hometeamCity'])} {_clean(row['hometeamName'])}",
                "away_team_id": _clean(row["awayteamId"]),
                "away_team_name": f"{_clean(row['awayteamCity'])} {_clean(row['awayteamName'])}",
                "home_score": _clean(row["homeScore"]),
                "away_score": _clean(row["awayScore"]),
                "winner_team_id": _clean(row["winner"]),
                "attendance": _clean(row["attendance"]),
                "arena_name": _clean(row["arenaName"]),
            }
            games[game["game_id"]] = game
            writer.writerow(game)
    return games


def normalize_team_stats(games: dict[str, dict[str, str]]) -> int:
    source = RAW_DIR / "TeamStatistics.csv"
    destination = PROCESSED_DIR / "team_game_stats.csv"
    written = 0
    with source.open(newline="", encoding="utf-8-sig") as handle, _atomic_writer(
        destination, TEAM_GAME_FIELDS
    ) as writer:
        for row in csv.DictReader(handle):
            game = games.get(_clean(row["gameId"]))
            if game is None:
                continue
            team_id = _clean(row["teamId"])
            opponent_team_id = _clean(row["opponentTeamId"])
            if not _matches_game_teams(game, team_id, opponent_team_id):
                # The source occasionally contains placeholder teamId=0 rows whose
                # gameId later points at a rescheduled real game. They are not box scores.
                continue
            normalized = {
                "season_id": SEASON_ID,
                "game_id": game["game_id"],
                "game_date": game["game_date"],
                "game_type": game["game_type"],
                "team_id": team_id,
                "team_name": f"{_clean(row['teamCity'])} {_clean(row['teamName'])}",
                "opponent_team_id": opponent_team_id,
                "opponent_team_name": (
                    f"{_clean(row['opponentTeamCity'])} {_clean(row['opponentTeamName'])}"
                ),
                "is_home": str(_as_bool(row["home"])).lower(),
                "won": str(_as_bool(row["win"])).lower(),
                "team_score": _clean(row["teamScore"]),
                "opponent_score": _clean(row["opponentScore"]),
                "assists": _clean(row["assists"]),
                "blocks": _clean(row["blocks"]),
                "steals": _clean(row["steals"]),
                "field_goals_attempted": _clean(row["fieldGoalsAttempted"]),
                "field_goals_made": _clean(row["fieldGoalsMade"]),
                "field_goal_percentage": _clean(row["fieldGoalsPercentage"]),
                "three_pointers_attempted": _clean(row["threePointersAttempted"]),
                "three_pointers_made": _clean(row["threePointersMade"]),
                "three_point_percentage": _clean(row["threePointersPercentage"]),
                "free_throws_attempted": _clean(row["freeThrowsAttempted"]),
                "free_throws_made": _clean(row["freeThrowsMade"]),
                "free_throw_percentage": _clean(row["freeThrowsPercentage"]),
                "defensive_rebounds": _clean(row["reboundsDefensive"]),
                "offensive_rebounds": _clean(row["reboundsOffensive"]),
                "total_rebounds": _clean(row["reboundsTotal"]),
                "personal_fouls": _clean(row["foulsPersonal"]),
                "turnovers": _clean(row["turnovers"]),
                "plus_minus": _clean(row["plusMinusPoints"]),
                "minutes": _clean(row["numMinutes"]),
            }
            writer.writerow(normalized)
            written += 1
    return written


def normalize_player_stats(games: dict[str, dict[str, str]]) -> tuple[int, set[str]]:
    source = RAW_DIR / "PlayerStatistics.csv"
    destination = PROCESSED_DIR / "player_game_stats.csv"
    written = 0
    player_ids: set[str] = set()
    with source.open(newline="", encoding="utf-8-sig") as handle, _atomic_writer(
        destination, PLAYER_GAME_FIELDS
    ) as writer:
        for row in csv.DictReader(handle):
            game = games.get(_clean(row["gameId"]))
            if game is None:
                continue
            team_id = _clean(row["playerteamId"])
            opponent_team_id = _clean(row["opponentteamId"])
            if not _matches_game_teams(game, team_id, opponent_team_id):
                continue
            player_id = _clean(row["personId"])
            player_ids.add(player_id)
            minutes = _clean(row["numMinutes"])
            normalized = {
                "season_id": SEASON_ID,
                "game_id": game["game_id"],
                "game_date": game["game_date"],
                "game_type": game["game_type"],
                "player_id": player_id,
                "first_name": _clean(row["firstName"]),
                "last_name": _clean(row["lastName"]),
                "team_id": team_id,
                "team_name": f"{_clean(row['playerteamCity'])} {_clean(row['playerteamName'])}",
                "opponent_team_id": opponent_team_id,
                "opponent_team_name": (
                    f"{_clean(row['opponentteamCity'])} {_clean(row['opponentteamName'])}"
                ),
                "is_home": str(_as_bool(row["home"])).lower(),
                "won": str(_as_bool(row["win"])).lower(),
                "did_play": str(bool(minutes)).lower(),
                "minutes": minutes,
                "points": _clean(row["points"]),
                "assists": _clean(row["assists"]),
                "blocks": _clean(row["blocks"]),
                "steals": _clean(row["steals"]),
                "field_goals_attempted": _clean(row["fieldGoalsAttempted"]),
                "field_goals_made": _clean(row["fieldGoalsMade"]),
                "field_goal_percentage": _clean(row["fieldGoalsPercentage"]),
                "three_pointers_attempted": _clean(row["threePointersAttempted"]),
                "three_pointers_made": _clean(row["threePointersMade"]),
                "three_point_percentage": _clean(row["threePointersPercentage"]),
                "free_throws_attempted": _clean(row["freeThrowsAttempted"]),
                "free_throws_made": _clean(row["freeThrowsMade"]),
                "free_throw_percentage": _clean(row["freeThrowsPercentage"]),
                "defensive_rebounds": _clean(row["reboundsDefensive"]),
                "offensive_rebounds": _clean(row["reboundsOffensive"]),
                "total_rebounds": _clean(row["reboundsTotal"]),
                "personal_fouls": _clean(row["foulsPersonal"]),
                "turnovers": _clean(row["turnovers"]),
                "plus_minus": _clean(row["plusMinusPoints"]),
                "availability_comment": _clean(row["comment"]),
                "starting_position": _clean(row["startingPosition"]),
            }
            writer.writerow(normalized)
            written += 1
    return written, player_ids


def normalize_players(player_ids: set[str]) -> int:
    source = RAW_DIR / "Players.csv"
    destination = PROCESSED_DIR / "players.csv"
    fields = (
        "player_id",
        "first_name",
        "last_name",
        "birth_date",
        "school",
        "country",
        "height_inches",
        "weight_lbs",
        "position_guard",
        "position_forward",
        "position_center",
        "from_year",
        "to_year",
    )
    written = 0
    with source.open(newline="", encoding="utf-8-sig") as handle, _atomic_writer(
        destination, fields
    ) as writer:
        for row in csv.DictReader(handle):
            if _clean(row["personId"]) not in player_ids:
                continue
            writer.writerow(
                {
                    "player_id": _clean(row["personId"]),
                    "first_name": _clean(row["firstName"]),
                    "last_name": _clean(row["lastName"]),
                    "birth_date": _clean(row["birthDate"])[:10],
                    "school": _clean(row["school"]),
                    "country": _clean(row["country"]),
                    "height_inches": _clean(row["heightInches"]),
                    "weight_lbs": _clean(row["bodyWeightLbs"]),
                    "position_guard": str(_as_bool(row["guard"])).lower(),
                    "position_forward": str(_as_bool(row["forward"])).lower(),
                    "position_center": str(_as_bool(row["center"])).lower(),
                    "from_year": _clean(row["fromYear"]),
                    "to_year": _clean(row["toYear"]),
                }
            )
            written += 1
    return written


def main() -> None:
    required = ("Games.csv", "TeamStatistics.csv", "PlayerStatistics.csv", "Players.csv")
    missing = [name for name in required if not (RAW_DIR / name).is_file()]
    if missing:
        message = f"Missing source files: {', '.join(missing)}. Run python -m ingestion.download"
        raise SystemExit(message)

    games = normalize_games()
    team_rows = normalize_team_stats(games)
    player_rows, player_ids = normalize_player_stats(games)
    player_count = normalize_players(player_ids)
    summary = {
        "season_id": SEASON_ID,
        "games": len(games),
        "team_game_rows": team_rows,
        "player_game_rows": player_rows,
        "players": player_count,
    }
    (PROCESSED_DIR / "normalization_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

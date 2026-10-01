"""Validate normalized coverage and reconcile canonical box-score rows."""

from __future__ import annotations

import csv
import json
from collections import Counter

from ingestion.config import (
    HOUSTON_ROCKETS_TEAM_ID,
    KEVIN_DURANT_PLAYER_ID,
    PROCESSED_DIR,
)


def _read(name: str) -> list[dict[str, str]]:
    path = PROCESSED_DIR / name
    if not path.is_file():
        raise SystemExit(f"Missing {path}. Run python -m ingestion.normalize first.")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def reconcile_team_rows(
    games_by_id: dict[str, dict[str, str]], team_rows: list[dict[str, str]]
) -> list[str]:
    errors: list[str] = []
    team_rows_by_game = Counter(row["game_id"] for row in team_rows)
    for game_id in games_by_id:
        if team_rows_by_game[game_id] != 2:
            errors.append(f"Game {game_id} has {team_rows_by_game[game_id]} team rows instead of 2")
            if len(errors) >= 25:
                return errors

    for row in team_rows:
        game = games_by_id.get(row["game_id"])
        if game is None:
            errors.append(f"Team row references unknown game {row['game_id']}")
            continue
        if row["team_id"] == game["home_team_id"]:
            expected_score = game["home_score"]
        elif row["team_id"] == game["away_team_id"]:
            expected_score = game["away_score"]
        else:
            errors.append(f"Team {row['team_id']} is not part of game {row['game_id']}")
            continue
        if row["team_score"] != expected_score:
            errors.append(
                f"Score mismatch for game {row['game_id']} and team {row['team_id']}: "
                f"{row['team_score']} != {expected_score}"
            )
    return errors


def validate() -> dict[str, object]:
    games = _read("games.csv")
    team_rows = _read("team_game_stats.csv")
    player_rows = _read("player_game_stats.csv")

    errors: list[str] = []
    warnings: list[str] = []
    games_by_id = {row["game_id"]: row for row in games}
    if len(games_by_id) != len(games):
        errors.append("games.csv contains duplicate game_id values")

    regular_games = [row for row in games if row["game_type"] == "Regular Season"]
    regular_teams = {
        team_id
        for row in regular_games
        for team_id in (row["home_team_id"], row["away_team_id"])
    }
    rockets_regular = [
        row
        for row in regular_games
        if HOUSTON_ROCKETS_TEAM_ID in (row["home_team_id"], row["away_team_id"])
    ]

    if len(regular_games) != 1230:
        errors.append(f"Expected 1,230 regular-season games, found {len(regular_games)}")
    if len(regular_teams) != 30:
        errors.append(f"Expected 30 regular-season teams, found {len(regular_teams)}")
    if len(rockets_regular) != 82:
        errors.append(f"Expected 82 Rockets regular-season games, found {len(rockets_regular)}")

    errors.extend(reconcile_team_rows(games_by_id, team_rows))

    unknown_player_games = sorted(
        {row["game_id"] for row in player_rows if row["game_id"] not in games_by_id}
    )
    if unknown_player_games:
        errors.append(f"Player rows reference {len(unknown_player_games)} unknown games")

    durant_regular = [
        row
        for row in player_rows
        if row["player_id"] == KEVIN_DURANT_PLAYER_ID
        and row["team_id"] == HOUSTON_ROCKETS_TEAM_ID
        and row["game_type"] == "Regular Season"
    ]
    if len(durant_regular) < 70:
        errors.append(f"Expected substantial Durant coverage, found {len(durant_regular)} rows")
    durant_did_not_play = sum(row["did_play"] == "false" for row in durant_regular)
    if not durant_did_not_play:
        warnings.append("No Durant DNP rows were found; availability-answer tests will be limited")

    metrics = {
        "games": len(games),
        "regular_season_games": len(regular_games),
        "regular_season_teams": len(regular_teams),
        "rockets_regular_season_games": len(rockets_regular),
        "team_game_rows": len(team_rows),
        "player_game_rows": len(player_rows),
        "durant_rockets_regular_season_rows": len(durant_regular),
        "durant_rockets_regular_season_dnp_rows": durant_did_not_play,
    }
    return {
        "status": "passed" if not errors else "failed",
        "metrics": metrics,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    report = validate()
    destination = PROCESSED_DIR / "validation_report.json"
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

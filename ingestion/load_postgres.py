"""Load normalized CSV files into PostgreSQL using the application schema."""

from __future__ import annotations

import argparse
import csv
from collections.abc import Callable, Iterable, Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database import build_engine
from backend.app.models import Game, Player, PlayerGameStat, Team, TeamGameStat
from ingestion.config import PROCESSED_DIR
from ingestion.validate import validate

BATCH_SIZE = 2_000


def _none_if_blank(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _int(value: str | None) -> int | None:
    cleaned = _none_if_blank(value)
    return int(cleaned) if cleaned is not None else None


def _decimal(value: str | None) -> Decimal | None:
    cleaned = _none_if_blank(value)
    return Decimal(cleaned) if cleaned is not None else None


def _bool(value: str | None) -> bool:
    cleaned = (value or "").strip().lower()
    if cleaned in {"1", "true", "yes", "y"}:
        return True
    if cleaned in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def _date(value: str | None) -> date | None:
    cleaned = _none_if_blank(value)
    return date.fromisoformat(cleaned) if cleaned is not None else None


def _datetime(value: str | None) -> datetime | None:
    cleaned = _none_if_blank(value)
    if cleaned is None:
        return None
    parsed = datetime.fromisoformat(cleaned)
    if parsed.utcoffset() is None:
        raise ValueError(f"Datetime must include a UTC offset: {value!r}")
    return parsed


def _chunks(
    rows: Iterable[dict[str, Any]], size: int = BATCH_SIZE
) -> Iterator[list[dict[str, Any]]]:
    batch: list[dict[str, Any]] = []
    for row in rows:
        batch.append(row)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def _csv_rows(path: Path) -> Iterator[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def _insert_rows(
    session: Session,
    model: type[Any],
    rows: Iterable[dict[str, Any]],
) -> int:
    inserted = 0
    for batch in _chunks(rows):
        session.execute(insert(model), batch)
        inserted += len(batch)
    return inserted


def _team_rows(games_path: Path) -> Iterator[dict[str, Any]]:
    teams: dict[int, str] = {}
    for row in _csv_rows(games_path):
        teams[int(row["home_team_id"])] = row["home_team_name"]
        teams[int(row["away_team_id"])] = row["away_team_name"]
    for team_id, name in sorted(teams.items()):
        yield {"team_id": team_id, "name": name}


def _game_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "game_id": row["game_id"],
        "season_id": row["season_id"],
        "tipoff_at": _datetime(row["tipoff_at"]),
        "game_date": _date(row["game_date"]),
        "game_type": row["game_type"],
        "home_team_id": int(row["home_team_id"]),
        "away_team_id": int(row["away_team_id"]),
        "home_score": int(row["home_score"]),
        "away_score": int(row["away_score"]),
        "winner_team_id": int(row["winner_team_id"]),
        "attendance": _int(row["attendance"]),
        "arena_name": _none_if_blank(row["arena_name"]),
    }


def _player_row(row: dict[str, str]) -> dict[str, Any]:
    return {
        "player_id": int(row["player_id"]),
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "birth_date": _date(row["birth_date"]),
        "school": _none_if_blank(row["school"]),
        "country": _none_if_blank(row["country"]),
        "height_inches": _decimal(row["height_inches"]),
        "weight_lbs": _decimal(row["weight_lbs"]),
        "position_guard": _bool(row["position_guard"]),
        "position_forward": _bool(row["position_forward"]),
        "position_center": _bool(row["position_center"]),
        "from_year": _int(row["from_year"]),
        "to_year": _int(row["to_year"]),
    }


def _team_game_row(row: dict[str, str]) -> dict[str, Any]:
    integer_fields = (
        "team_score",
        "opponent_score",
        "assists",
        "blocks",
        "steals",
        "field_goals_attempted",
        "field_goals_made",
        "three_pointers_attempted",
        "three_pointers_made",
        "free_throws_attempted",
        "free_throws_made",
        "defensive_rebounds",
        "offensive_rebounds",
        "total_rebounds",
        "personal_fouls",
        "turnovers",
        "plus_minus",
    )
    values: dict[str, Any] = {
        "game_id": row["game_id"],
        "team_id": int(row["team_id"]),
        "opponent_team_id": int(row["opponent_team_id"]),
        "is_home": _bool(row["is_home"]),
        "won": _bool(row["won"]),
        "field_goal_percentage": _decimal(row["field_goal_percentage"]),
        "three_point_percentage": _decimal(row["three_point_percentage"]),
        "free_throw_percentage": _decimal(row["free_throw_percentage"]),
        "minutes_seconds": int(row["minutes_seconds"]),
    }
    values.update({field: _int(row[field]) for field in integer_fields})
    return values


def _player_game_row(row: dict[str, str]) -> dict[str, Any]:
    did_play = _bool(row["did_play"])
    integer_fields = (
        "points",
        "assists",
        "blocks",
        "steals",
        "field_goals_attempted",
        "field_goals_made",
        "three_pointers_attempted",
        "three_pointers_made",
        "free_throws_attempted",
        "free_throws_made",
        "defensive_rebounds",
        "offensive_rebounds",
        "total_rebounds",
        "personal_fouls",
        "turnovers",
        "plus_minus",
    )
    values: dict[str, Any] = {
        "game_id": row["game_id"],
        "player_id": int(row["player_id"]),
        "team_id": int(row["team_id"]),
        "opponent_team_id": int(row["opponent_team_id"]),
        "is_home": _bool(row["is_home"]),
        "won": _bool(row["won"]),
        "did_play": did_play,
        "availability_comment": _none_if_blank(row["availability_comment"]),
        "starting_position": _none_if_blank(row["starting_position"]),
    }
    if did_play:
        values.update({field: _int(row[field]) for field in integer_fields})
        values.update(
            {
                "minutes_seconds": int(row["minutes_seconds"]),
                "field_goal_percentage": _decimal(row["field_goal_percentage"]),
                "three_point_percentage": _decimal(row["three_point_percentage"]),
                "free_throw_percentage": _decimal(row["free_throw_percentage"]),
            }
        )
    else:
        values.update({field: None for field in integer_fields})
        values.update(
            {
                "minutes_seconds": None,
                "field_goal_percentage": None,
                "three_point_percentage": None,
                "free_throw_percentage": None,
            }
        )
    return values


def _converted_rows(path: Path, converter: Callable[[dict[str, str]], dict[str, Any]]):
    for row in _csv_rows(path):
        yield converter(row)


def load(database_url: str, *, replace: bool) -> dict[str, int]:
    engine = build_engine(database_url)
    paths = {
        "games": PROCESSED_DIR / "games.csv",
        "players": PROCESSED_DIR / "players.csv",
        "team_stats": PROCESSED_DIR / "team_game_stats.csv",
        "player_stats": PROCESSED_DIR / "player_game_stats.csv",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise SystemExit(f"Missing normalized files: {', '.join(missing)}")

    validation = validate()
    if validation["status"] != "passed":
        errors = "; ".join(str(error) for error in validation["errors"])
        raise SystemExit(f"Refusing to load a failed normalized snapshot: {errors}")

    with Session(engine) as session, session.begin():
        if replace:
            for model in (PlayerGameStat, TeamGameStat, Game, Player, Team):
                session.execute(delete(model))

        counts = {
            "teams": _insert_rows(session, Team, _team_rows(paths["games"])),
            "players": _insert_rows(
                session, Player, _converted_rows(paths["players"], _player_row)
            ),
            "games": _insert_rows(session, Game, _converted_rows(paths["games"], _game_row)),
            "team_game_stats": _insert_rows(
                session,
                TeamGameStat,
                _converted_rows(paths["team_stats"], _team_game_row),
            ),
            "player_game_stats": _insert_rows(
                session,
                PlayerGameStat,
                _converted_rows(paths["player_stats"], _player_game_row),
            ),
        }
    engine.dispose()
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=get_settings().database_url)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing analytics rows before loading the snapshot",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    counts = load(args.database_url, replace=args.replace)
    for table, count in counts.items():
        print(f"{table}: {count:,}")


if __name__ == "__main__":
    main()

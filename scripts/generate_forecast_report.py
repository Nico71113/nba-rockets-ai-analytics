from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

from backend.app.experiments.three_point_forecast import (
    ShootingObservation,
    build_three_point_forecast,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the versioned three-point forecast backtest from normalized CSVs."
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("frontend/public/demo/three-point-forecast.json"),
    )
    parser.add_argument("--season-id", default="2025-26")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    game_dates_by_id: dict[str, date] = {}
    with (args.data_dir / "games.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["season_id"] == args.season_id and row["game_type"] == "Regular Season":
                game_dates_by_id[row["game_id"]] = date.fromisoformat(row["game_date"])

    observations = []
    with (args.data_dir / "player_game_stats.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        for row in csv.DictReader(handle):
            game_date = game_dates_by_id.get(row["game_id"])
            if game_date is None or row["did_play"].casefold() != "true":
                continue
            observations.append(
                ShootingObservation(
                    game_date=game_date,
                    player_id=int(row["player_id"]),
                    player_name=f"{row['first_name']} {row['last_name']}",
                    team_name=row["team_name"],
                    made=int(row["three_pointers_made"] or 0),
                    attempted=int(row["three_pointers_attempted"] or 0),
                )
            )

    report = build_three_point_forecast(
        season_id=args.season_id,
        game_dates=list(game_dates_by_id.values()),
        observations=observations,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f"{report.model_dump_json(indent=2)}\n", encoding="utf-8")
    print(
        f"Wrote {report.cohort.players} evaluated players and "
        f"{len(report.largest_misses)} error cases to {args.output}"
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Game, Player, PlayerGameStat, Team
from backend.app.schemas import (
    ForecastCohort,
    ForecastErrorCase,
    ForecastFeaturedPlayer,
    ForecastMethodResult,
    ForecastMetrics,
    ForecastSplit,
    ForecastVolumeBucket,
    ThreePointForecastResponse,
)

DEFAULT_PRIOR_STRENGTHS = (0, 1, 2, 5, 10, 20, 40, 60, 80, 100, 150, 200, 300, 500, 1000)


@dataclass(frozen=True)
class ShootingObservation:
    game_date: date
    player_id: int
    player_name: str
    team_name: str
    made: int
    attempted: int


@dataclass
class ShootingLine:
    made: int = 0
    attempted: int = 0

    @property
    def percentage(self) -> float:
        return self.made / self.attempted

    def add(self, made: int, attempted: int) -> None:
        self.made += made
        self.attempted += attempted


@dataclass
class PlayerPeriods:
    player_name: str
    teams: Counter[str] = field(default_factory=Counter)
    early: ShootingLine = field(default_factory=ShootingLine)
    validation: ShootingLine = field(default_factory=ShootingLine)
    test: ShootingLine = field(default_factory=ShootingLine)

    @property
    def training(self) -> ShootingLine:
        return ShootingLine(
            made=self.early.made + self.validation.made,
            attempted=self.early.attempted + self.validation.attempted,
        )

    @property
    def primary_team(self) -> str:
        return self.teams.most_common(1)[0][0] if self.teams else "Unknown"


def _midpoint_date(game_dates: list[date]) -> tuple[date, int]:
    if not game_dates:
        raise ValueError("At least one regular-season game is required.")
    counts = Counter(game_dates)
    target = len(game_dates) / 2
    cumulative = 0
    for game_date in sorted(counts):
        cumulative += counts[game_date]
        if cumulative >= target:
            return game_date, cumulative
    raise AssertionError("A midpoint must exist for a non-empty schedule.")


def _metrics(errors: list[tuple[float, int]]) -> ForecastMetrics:
    if not errors:
        raise ValueError("At least one prediction error is required.")
    attempts = sum(weight for _, weight in errors)
    return ForecastMetrics(
        mae=round(sum(abs(error) for error, _ in errors) / len(errors), 6),
        rmse=round(math.sqrt(sum(error**2 for error, _ in errors) / len(errors)), 6),
        attempt_weighted_mae=round(
            sum(abs(error) * weight for error, weight in errors) / attempts,
            6,
        ),
        attempt_weighted_rmse=round(
            math.sqrt(sum(error**2 * weight for error, weight in errors) / attempts),
            6,
        ),
    )


def _prediction(method: str, line: ShootingLine, league_mean: float, strength: int) -> float:
    if method == "historical_rate":
        return line.percentage
    if method == "league_mean":
        return league_mean
    if method == "shrinkage":
        return (line.made + strength * league_mean) / (line.attempted + strength)
    raise ValueError(f"Unknown prediction method: {method}")


def build_three_point_forecast(
    *,
    season_id: str,
    game_dates: list[date],
    observations: list[ShootingObservation],
    minimum_attempts_per_half: int = 25,
    validation_minimum_attempts: int = 10,
    prior_strengths: tuple[int, ...] = DEFAULT_PRIOR_STRENGTHS,
    featured_player_name: str = "Kevin Durant",
) -> ThreePointForecastResponse:
    """Backtest second-half 3P% predictions without using future data for fitting."""
    if minimum_attempts_per_half < 1 or validation_minimum_attempts < 1:
        raise ValueError("Attempt thresholds must be positive.")
    if not prior_strengths:
        raise ValueError("At least one prior strength is required.")

    training_end, training_games = _midpoint_date(game_dates)
    training_dates = [game_date for game_date in game_dates if game_date <= training_end]
    validation_start_boundary, validation_training_games = _midpoint_date(training_dates)

    periods: dict[int, PlayerPeriods] = {}
    for observation in observations:
        player = periods.setdefault(
            observation.player_id,
            PlayerPeriods(player_name=observation.player_name),
        )
        if observation.game_date <= validation_start_boundary:
            line = player.early
        elif observation.game_date <= training_end:
            line = player.validation
        else:
            line = player.test
        if observation.game_date <= training_end:
            player.teams[observation.team_name] += 1
        line.add(observation.made, observation.attempted)

    early_made = sum(player.early.made for player in periods.values())
    early_attempted = sum(player.early.attempted for player in periods.values())
    if early_attempted == 0:
        raise ValueError("The validation-training period has no three-point attempts.")
    early_league_mean = early_made / early_attempted
    validation_players = [
        player
        for player in periods.values()
        if player.early.attempted >= validation_minimum_attempts
        and player.validation.attempted >= validation_minimum_attempts
    ]
    if not validation_players:
        raise ValueError("No players meet the nested validation attempt threshold.")

    tuning_scores: list[tuple[float, int]] = []
    for strength in prior_strengths:
        squared_errors = []
        for player in validation_players:
            predicted = _prediction("shrinkage", player.early, early_league_mean, strength)
            squared_errors.append((predicted - player.validation.percentage) ** 2)
        tuning_scores.append((math.sqrt(sum(squared_errors) / len(squared_errors)), strength))
    validation_rmse, selected_strength = min(tuning_scores)

    training_made = sum(player.training.made for player in periods.values())
    training_attempted = sum(player.training.attempted for player in periods.values())
    if training_attempted == 0:
        raise ValueError("The training period has no three-point attempts.")
    league_mean = training_made / training_attempted
    eligible = {
        player_id: player
        for player_id, player in periods.items()
        if player.training.attempted >= minimum_attempts_per_half
        and player.test.attempted >= minimum_attempts_per_half
    }
    if not eligible:
        raise ValueError("No players meet the evaluation attempt threshold.")

    method_definitions = (
        (
            "historical_rate",
            "First-half rate",
            "Use each player's first-half makes divided by attempts without adjustment.",
        ),
        (
            "league_mean",
            "League mean",
            "Give every eligible player the first-half league-wide three-point rate.",
        ),
        (
            "shrinkage",
            "Empirical-Bayes shrinkage",
            "Blend each player's first-half rate toward the league mean using a prior "
            "strength selected only inside the first half.",
        ),
    )
    method_results: list[ForecastMethodResult] = []
    all_predictions: dict[str, dict[int, float]] = defaultdict(dict)
    for key, label, description in method_definitions:
        errors = []
        for player_id, player in eligible.items():
            predicted = _prediction(key, player.training, league_mean, selected_strength)
            all_predictions[key][player_id] = predicted
            errors.append((predicted - player.test.percentage, player.test.attempted))
        method_results.append(
            ForecastMethodResult(
                key=key,
                label=label,
                description=description,
                metrics=_metrics(errors),
            )
        )

    ranked_methods = sorted(method_results, key=lambda method: method.metrics.rmse)
    best_method = ranked_methods[0]
    method_by_key = {method.key: method for method in method_results}
    historical_rmse = method_by_key["historical_rate"].metrics.rmse
    league_rmse = method_by_key["league_mean"].metrics.rmse

    misses = []
    for player_id, player in eligible.items():
        predicted = all_predictions["shrinkage"][player_id]
        actual = player.test.percentage
        misses.append(
            ForecastErrorCase(
                player_id=player_id,
                player_name=player.player_name,
                primary_team=player.primary_team,
                first_half_made=player.training.made,
                first_half_attempts=player.training.attempted,
                first_half_percentage=round(player.training.percentage, 6),
                predicted_percentage=round(predicted, 6),
                second_half_made=player.test.made,
                second_half_attempts=player.test.attempted,
                actual_percentage=round(actual, 6),
                absolute_error=round(abs(predicted - actual), 6),
            )
        )
    misses.sort(key=lambda player: (-player.absolute_error, player.player_name))

    volume_buckets = []
    for label, minimum, maximum in (
        ("25–74 attempts", 25, 74),
        ("75–149 attempts", 75, 149),
        ("150+ attempts", 150, None),
    ):
        player_ids = [
            player_id
            for player_id, player in eligible.items()
            if player.training.attempted >= minimum
            and (maximum is None or player.training.attempted <= maximum)
        ]
        if not player_ids:
            continue
        bucket_metrics = {}
        for key, _, _ in method_definitions:
            errors = [
                (
                    all_predictions[key][player_id] - eligible[player_id].test.percentage,
                    eligible[player_id].test.attempted,
                )
                for player_id in player_ids
            ]
            bucket_metrics[key] = _metrics(errors)
        volume_buckets.append(
            ForecastVolumeBucket(
                label=label,
                minimum_attempts=minimum,
                maximum_attempts=maximum,
                players=len(player_ids),
                methods=bucket_metrics,
            )
        )

    featured_player = None
    for player_id, player in eligible.items():
        if player.player_name.casefold() == featured_player_name.casefold():
            featured_player = ForecastFeaturedPlayer(
                player_id=player_id,
                player_name=player.player_name,
                primary_team=player.primary_team,
                first_half_percentage=round(player.training.percentage, 6),
                league_mean_prediction=round(all_predictions["league_mean"][player_id], 6),
                shrinkage_prediction=round(all_predictions["shrinkage"][player_id], 6),
                second_half_percentage=round(player.test.percentage, 6),
                first_half_attempts=player.training.attempted,
                second_half_attempts=player.test.attempted,
            )
            break

    sorted_dates = sorted(game_dates)
    testing_start = min(game_date for game_date in sorted_dates if game_date > training_end)
    validation_start = min(
        game_date
        for game_date in sorted_dates
        if validation_start_boundary < game_date <= training_end
    )
    return ThreePointForecastResponse(
        season_id=season_id,
        question=(
            "Can first-half data predict a player's second-half three-point "
            "percentage more accurately?"
        ),
        split=ForecastSplit(
            training_start=sorted_dates[0],
            training_end=training_end,
            testing_start=testing_start,
            testing_end=sorted_dates[-1],
            validation_training_end=validation_start_boundary,
            validation_start=validation_start,
            training_games=training_games,
            testing_games=len(game_dates) - training_games,
        ),
        cohort=ForecastCohort(
            players=len(eligible),
            minimum_attempts_per_half=minimum_attempts_per_half,
            validation_players=len(validation_players),
            validation_minimum_attempts=validation_minimum_attempts,
        ),
        league_first_half_percentage=round(league_mean, 6),
        selected_prior_strength=selected_strength,
        validation_rmse=round(validation_rmse, 6),
        selection_metric="unweighted player-level RMSE",
        methods=method_results,
        best_method=best_method.key,
        improvement_vs_historical_rmse_pct=round(
            (historical_rmse - best_method.metrics.rmse) / historical_rmse * 100,
            1,
        ),
        improvement_vs_league_rmse_pct=round(
            (league_rmse - best_method.metrics.rmse) / league_rmse * 100,
            1,
        ),
        volume_buckets=volume_buckets,
        largest_misses=misses[:10],
        featured_player=featured_player,
        findings=[
            "Partial pooling materially reduces error versus trusting noisy first-half "
            "percentages at face value.",
            "The largest gains come from lower-volume shooters, whose observed rates "
            "carry the most sampling noise.",
            "Shrinkage wins across the cohort, but it can underpredict established "
            "high-skill shooters; player-level misses still need basketball context.",
        ],
        limitations=[
            "The evaluation cohort requires at least 25 three-point attempts in each "
            "half, so it excludes many low-usage and injured players.",
            "The model uses makes and attempts only; role, shot quality, injuries, "
            "lineup context, and tracking data are not available.",
            "This is a single-season backtest. A production forecast should repeat "
            "the design across multiple seasons before deployment.",
        ],
    )


def run_three_point_forecast(
    session: Session,
    season_id: str = "2025-26",
) -> ThreePointForecastResponse:
    game_dates = list(
        session.scalars(
            select(Game.game_date)
            .where(Game.season_id == season_id, Game.game_type == "Regular Season")
            .order_by(Game.game_date, Game.game_id)
        )
    )
    rows = session.execute(
        select(
            Game.game_date,
            PlayerGameStat.player_id,
            Player.first_name,
            Player.last_name,
            Team.name,
            PlayerGameStat.three_pointers_made,
            PlayerGameStat.three_pointers_attempted,
        )
        .join(PlayerGameStat, PlayerGameStat.game_id == Game.game_id)
        .join(Player, Player.player_id == PlayerGameStat.player_id)
        .join(Team, Team.team_id == PlayerGameStat.team_id)
        .where(
            Game.season_id == season_id,
            Game.game_type == "Regular Season",
            PlayerGameStat.did_play.is_(True),
            PlayerGameStat.three_pointers_made.is_not(None),
            PlayerGameStat.three_pointers_attempted.is_not(None),
        )
        .order_by(Game.game_date, Game.game_id, PlayerGameStat.player_id)
    )
    observations = [
        ShootingObservation(
            game_date=game_date,
            player_id=player_id,
            player_name=f"{first_name} {last_name}",
            team_name=team_name,
            made=int(made),
            attempted=int(attempted),
        )
        for game_date, player_id, first_name, last_name, team_name, made, attempted in rows
    ]
    return build_three_point_forecast(
        season_id=season_id,
        game_dates=game_dates,
        observations=observations,
    )

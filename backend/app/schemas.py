from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    source_table: str
    snapshot_id: str = "eoinamoore/historical-nba-data-and-player-box-scores@515"
    game_ids: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)


class AnalyticsResult(BaseModel):
    method: Literal["sql", "refusal"]
    answer: str
    metrics: dict[str, int | float | str | None] = Field(default_factory=dict)
    calculation: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    coverage_note: str | None = None


class CoverageResponse(BaseModel):
    season_id: str
    first_game_date: date | None
    last_game_date: date | None
    games: int
    teams: int
    players: int
    player_game_rows: int
    team_game_rows: int


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class QueryResponse(BaseModel):
    question: str
    intent: str
    routing_source: Literal[
        "local_model",
        "deterministic",
        "deterministic_fallback",
        "coverage_guard",
    ]
    interpretation: dict[str, Any] = Field(default_factory=dict)
    result: AnalyticsResult
    elapsed_ms: int | None = None


class GameEvidenceRow(BaseModel):
    game_id: str
    game_date: date
    game_type: str
    away_team: str
    home_team: str
    away_score: int
    home_score: int
    winner: str


class ForecastMetrics(BaseModel):
    mae: float
    rmse: float
    attempt_weighted_mae: float
    attempt_weighted_rmse: float


class ForecastMethodResult(BaseModel):
    key: Literal["historical_rate", "league_mean", "shrinkage"]
    label: str
    description: str
    metrics: ForecastMetrics


class ForecastSplit(BaseModel):
    training_start: date
    training_end: date
    testing_start: date
    testing_end: date
    validation_training_end: date
    validation_start: date
    training_games: int
    testing_games: int


class ForecastCohort(BaseModel):
    players: int
    minimum_attempts_per_half: int
    validation_players: int
    validation_minimum_attempts: int


class ForecastErrorCase(BaseModel):
    player_id: int
    player_name: str
    primary_team: str
    first_half_made: int
    first_half_attempts: int
    first_half_percentage: float
    predicted_percentage: float
    second_half_made: int
    second_half_attempts: int
    actual_percentage: float
    absolute_error: float


class ForecastFeaturedPlayer(BaseModel):
    player_id: int
    player_name: str
    primary_team: str
    first_half_percentage: float
    league_mean_prediction: float
    shrinkage_prediction: float
    second_half_percentage: float
    first_half_attempts: int
    second_half_attempts: int


class ForecastVolumeBucket(BaseModel):
    label: str
    minimum_attempts: int
    maximum_attempts: int | None
    players: int
    methods: dict[str, ForecastMetrics]


class ThreePointForecastResponse(BaseModel):
    season_id: str
    question: str
    split: ForecastSplit
    cohort: ForecastCohort
    league_first_half_percentage: float
    selected_prior_strength: int
    validation_rmse: float
    selection_metric: str
    methods: list[ForecastMethodResult]
    best_method: Literal["historical_rate", "league_mean", "shrinkage"]
    improvement_vs_historical_rmse_pct: float
    improvement_vs_league_rmse_pct: float
    volume_buckets: list[ForecastVolumeBucket]
    largest_misses: list[ForecastErrorCase]
    featured_player: ForecastFeaturedPlayer | None
    findings: list[str]
    limitations: list[str]

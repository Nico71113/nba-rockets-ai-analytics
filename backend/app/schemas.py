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
    interpretation: dict[str, Any] = Field(default_factory=dict)
    result: AnalyticsResult

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.orm import Session

from backend.app.analytics.service import (
    game_result,
    player_period_summary,
    team_record,
    team_record_when_player_reaches,
)
from backend.app.api.coverage import coverage
from evals.tests.conftest import load_json

QUESTION_CASES = load_json("structured_questions.json")["cases"]
OPERATIONS = {
    "game_result": game_result,
    "player_period_summary": player_period_summary,
    "team_record": team_record,
    "team_record_when_player_reaches": team_record_when_player_reaches,
}


def _typed_params(raw: dict[str, object]) -> dict[str, object]:
    params = dict(raw)
    for field in ("game_date", "start_date", "end_date"):
        if field in params:
            params[field] = date.fromisoformat(str(params[field]))
    return params


@pytest.mark.parametrize("case", QUESTION_CASES, ids=[case["id"] for case in QUESTION_CASES])
def test_golden_structured_question(case: dict[str, object], eval_session: Session) -> None:
    operation = OPERATIONS[str(case["operation"])]
    result = operation(eval_session, **_typed_params(case["params"]))
    expected = case["expected"]

    assert result.method == expected["method"]
    for name, value in expected.get("metrics", {}).items():
        assert result.metrics[name] == value

    if "game_ids" in expected:
        evidence_ids = [
            game_id for evidence in result.evidence for game_id in evidence.game_ids
        ]
        assert evidence_ids == expected["game_ids"]

    for phrase in expected.get("answer_contains", []):
        assert phrase in result.answer
    for phrase in expected.get("coverage_contains", []):
        assert result.coverage_note is not None
        assert phrase in result.coverage_note


def test_coverage_endpoint_reports_full_fixture_not_only_regular_season(
    eval_session: Session,
) -> None:
    result = coverage(eval_session)

    assert result.season_id == "2025-26"
    assert result.first_game_date == date(2025, 10, 1)
    assert result.last_game_date == date(2026, 6, 30)
    assert result.games == 5
    assert result.teams == 3
    assert result.players == 1
    assert result.team_game_rows == 10
    assert result.player_game_rows == 5


def test_dnp_is_not_silently_treated_as_a_zero_point_game(eval_session: Session) -> None:
    result = player_period_summary(
        eval_session,
        player_id=201142,
        team_id=1610612745,
        start_date=date(2026, 1, 5),
        end_date=date(2026, 1, 5),
    )

    assert result.method == "refusal"
    assert result.metrics == {}
    assert "No played games" in result.answer
    assert result.evidence[0].filters["did_play"] is True


def test_threshold_join_does_not_count_the_opponent_team_row(
    eval_session: Session,
) -> None:
    result = team_record_when_player_reaches(
        eval_session,
        team_id=1610612745,
        player_id=201142,
        stat="points",
        threshold=0,
        start_date=date(2025, 10, 1),
        end_date=date(2026, 6, 30),
    )

    # Three played regular-season player rows must remain three after joining a
    # two-row-per-game team box-score table.
    assert result.metrics == {"games": 3, "wins": 1, "losses": 2, "threshold": 0}
    assert result.evidence[0].game_ids == ["eval-001", "eval-002", "eval-004"]

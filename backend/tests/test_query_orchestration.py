from __future__ import annotations

from datetime import date

from backend.app.orchestration.router import IntentRouterError, ParsedIntent
from backend.app.orchestration.service import _month_range_from_question, answer_question
from evals.tests.conftest import eval_session as eval_session
from evals.tests.conftest import eval_snapshot as eval_snapshot


class FakeRouter:
    def __init__(self, parsed: ParsedIntent):
        self.parsed = parsed

    def parse(self, _: str) -> ParsedIntent:
        return self.parsed


class BrokenRouter:
    def parse(self, _: str) -> ParsedIntent:
        raise IntentRouterError("Ollama is offline")


def test_resolves_names_and_runs_exact_threshold_query(eval_session):
    parsed = ParsedIntent(
        intent="threshold_record",
        team_name="Rockets",
        start_date="2025-10-01",
        end_date="2026-06-30",
        threshold=30,
    )

    response = answer_question(
        eval_session,
        question="What was Houston's record when Durant scored at least 30 points?",
        router=FakeRouter(parsed),
    )

    assert response.intent == "threshold_record"
    assert response.interpretation["player_id"] == 201142
    assert response.interpretation["team_id"] == 1610612745
    assert response.result.metrics["wins"] == 1
    assert response.result.evidence[0].game_ids == ["eval-001", "eval-004"]


def test_explicit_month_range_is_deterministic():
    assert _month_range_from_question("What was Houston's record in January 2026?") == (
        date(2026, 1, 1),
        date(2026, 1, 31),
    )


def test_availability_reports_source_comment_without_inference(eval_session):
    parsed = ParsedIntent(
        intent="player_availability",
        player_name="Kevin Durant",
        team_name="Houston",
        opponent_name="Warriors",
        game_date="2026-01-05",
    )

    response = answer_question(
        eval_session,
        question="Why did Durant miss the game?",
        router=FakeRouter(parsed),
    )

    assert response.result.method == "sql"
    assert "Synthetic DNP - Injury/Illness" in response.result.answer
    assert response.result.calculation == [
        "Read the source-provided availability comment; no reason was inferred."
    ]


def test_unresolved_player_returns_specific_refusal(eval_session):
    parsed = ParsedIntent(
        intent="player_summary",
        player_name="Definitely Not A Player",
        team_name="Houston Rockets",
    )

    response = answer_question(
        eval_session,
        question="What did that player average?",
        router=FakeRouter(parsed),
    )

    assert response.result.method == "refusal"
    assert "No loaded player matches" in response.result.answer


def test_router_failure_is_visible_instead_of_fabricating(eval_session):
    response = answer_question(
        eval_session,
        question="What was Houston's record?",
        router=BrokenRouter(),
    )

    assert response.intent == "router_unavailable"
    assert response.result.method == "refusal"
    assert "local language model is unavailable" in response.result.answer


def test_known_tracking_question_returns_the_real_coverage_gap(eval_session):
    response = answer_question(
        eval_session,
        question="Which defender guarded Kevin Durant most often this season?",
        router=BrokenRouter(),
    )

    assert response.intent == "unsupported"
    assert response.result.method == "refusal"
    assert "no player-tracking or defensive-assignment data" in response.result.answer
    assert "No loaded team matches" not in response.result.answer


def test_supported_question_recovers_entities_and_date_when_model_omits_them(eval_session):
    response = answer_question(
        eval_session,
        question=(
            "Why did Kevin Durant miss the Houston Rockets game against the Golden State "
            "Warriors on January 5, 2026?"
        ),
        router=FakeRouter(ParsedIntent(intent="player_availability")),
    )

    assert response.result.method == "sql"
    assert "Synthetic DNP - Injury/Illness" in response.result.answer
    assert response.interpretation["team_name"] == "Houston Rockets"
    assert response.interpretation["opponent_name"] == "Golden State Warriors"
    assert response.interpretation["game_date"] == "2026-01-05"

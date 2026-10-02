from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GoldenAnswerCase:
    case_id: str
    question: str
    expected_intent: str
    expected_method: str
    expected_metrics: dict[str, int | float | str] = field(default_factory=dict)
    answer_contains: str | None = None
    coverage_contains: str | None = None


def build_golden_answer_cases() -> list[GoldenAnswerCase]:
    cases = [
        GoldenAnswerCase(
            "houston-record",
            "What was the Houston Rockets' regular-season record?",
            "team_record",
            "sql",
            {"games": 82, "wins": 52, "losses": 30},
        ),
        GoldenAnswerCase(
            "houston-home-record",
            "What was the Houston Rockets' home record this regular season?",
            "team_record",
            "sql",
            {"games": 41, "wins": 30, "losses": 11},
        ),
        GoldenAnswerCase(
            "houston-road-record",
            "What was the Houston Rockets' road record this regular season?",
            "team_record",
            "sql",
            {"games": 41, "wins": 22, "losses": 19},
        ),
        GoldenAnswerCase(
            "okc-record",
            "What was the Oklahoma City Thunder's regular-season record?",
            "team_record",
            "sql",
            {"games": 82, "wins": 64, "losses": 18},
        ),
        GoldenAnswerCase(
            "durant-season-summary",
            "What did Kevin Durant average during the regular season?",
            "player_summary",
            "sql",
            {
                "games_played": 78,
                "total_points": 2026,
                "points_per_game": 26.0,
                "rebounds_per_game": 5.5,
                "assists_per_game": 4.8,
            },
        ),
        GoldenAnswerCase(
            "durant-20-point-record",
            "What was Houston's record when Kevin Durant recorded at least 20 points?",
            "threshold_record",
            "sql",
            {"games": 64, "wins": 40, "losses": 24, "threshold": 20},
        ),
        GoldenAnswerCase(
            "durant-30-point-record",
            "What was Houston's record when Kevin Durant recorded at least 30 points?",
            "threshold_record",
            "sql",
            {"games": 29, "wins": 16, "losses": 13, "threshold": 30},
        ),
        GoldenAnswerCase(
            "durant-four-threes-record",
            "What was Houston's record when Kevin Durant recorded at least 4 three-pointers?",
            "threshold_record",
            "sql",
            {"games": 17, "wins": 11, "losses": 6, "threshold": 4},
        ),
        GoldenAnswerCase(
            "durant-ten-rebound-record",
            "What was Houston's record when Kevin Durant recorded at least 10 rebounds?",
            "threshold_record",
            "sql",
            {"games": 4, "wins": 2, "losses": 2, "threshold": 10},
        ),
        GoldenAnswerCase(
            "houston-january-points",
            "How many total points did Houston score in January 2026?",
            "metric_summary",
            "sql",
            {"games": 17, "value": 1834, "stat": "points", "aggregation": "sum"},
        ),
        GoldenAnswerCase(
            "houston-home-win-margin",
            "What was Houston's average point margin at home in wins?",
            "metric_summary",
            "sql",
            {
                "games": 30,
                "value": 13.4,
                "stat": "point_margin",
                "aggregation": "average",
                "location": "home",
                "outcome": "win",
            },
        ),
        GoldenAnswerCase(
            "durant-road-high",
            "What was Kevin Durant's highest points total on the road?",
            "metric_summary",
            "sql",
            {"games": 38, "value": 40, "stat": "points", "aggregation": "maximum"},
        ),
        GoldenAnswerCase(
            "durant-assists-average",
            "What was Kevin Durant's average assists figure this regular season?",
            "metric_summary",
            "sql",
            {"games": 78, "value": 4.8, "stat": "assists", "aggregation": "average"},
        ),
        GoldenAnswerCase(
            "durant-rebound-total",
            "What was Kevin Durant's total rebounds figure this regular season?",
            "metric_summary",
            "sql",
            {"games": 78, "value": 426, "stat": "rebounds", "aggregation": "sum"},
        ),
        GoldenAnswerCase(
            "houston-points-allowed",
            "What was Houston's average points allowed figure this regular season?",
            "metric_summary",
            "sql",
            {
                "games": 82,
                "value": 110.0,
                "stat": "opponent_points",
                "aggregation": "average",
            },
        ),
        GoldenAnswerCase(
            "houston-scoring-high",
            "What was Houston's highest points figure this regular season?",
            "metric_summary",
            "sql",
            {"games": 82, "value": 140, "stat": "points", "aggregation": "maximum"},
        ),
        GoldenAnswerCase(
            "houston-okc-opener",
            "What was the final score when Houston played Oklahoma City on October 21, 2025?",
            "game_result",
            "sql",
            {"home_score": 125, "away_score": 124, "winner_team_id": 1610612760},
            answer_contains="Oklahoma City Thunder won",
        ),
        GoldenAnswerCase(
            "missing-availability-source",
            "Why did Kevin Durant miss Houston's game against Phoenix on November 24, 2025?",
            "player_availability",
            "refusal",
            answer_contains="no availability row exists",
            coverage_contains="reason for the absence cannot be determined",
        ),
        GoldenAnswerCase(
            "tracking-coverage-guard",
            "Which defender guarded Kevin Durant most often this season?",
            "unsupported",
            "refusal",
            coverage_contains="no player-tracking or defensive-assignment data",
        ),
        GoldenAnswerCase(
            "live-score-coverage-guard",
            "What is the Rockets live score right now?",
            "unsupported",
            "refusal",
            coverage_contains="no live-data feed",
        ),
    ]
    if len(cases) != 20:
        raise AssertionError(f"Expected exactly 20 golden cases, found {len(cases)}")
    return cases

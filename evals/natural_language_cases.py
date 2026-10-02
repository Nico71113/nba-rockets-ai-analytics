from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class LanguageCase:
    case_id: str
    question: str
    expected_intent: str
    expected_method: str
    expected_interpretation: dict[str, object] = field(default_factory=dict)


def build_language_cases() -> list[LanguageCase]:
    cases: list[LanguageCase] = []
    teams = [
        "Houston Rockets",
        "Oklahoma City Thunder",
        "Golden State Warriors",
        "Boston Celtics",
        "Los Angeles Lakers",
    ]
    for team in teams:
        slug = team.casefold().replace(" ", "-")
        for location, wording in (
            ("all", f"What was the {team}'s regular-season record?"),
            ("home", f"What was the {team}'s home record this regular season?"),
            ("away", f"What was the {team}'s road record this regular season?"),
        ):
            cases.append(
                LanguageCase(
                    f"record-{slug}-{location}",
                    wording,
                    "team_record",
                    "sql",
                    {"location": location},
                )
            )

    summary_questions = [
        "What did Kevin Durant average during the regular season?",
        "Give me Kevin Durant's basic regular-season averages.",
        "Summarize Kevin Durant's regular-season production.",
        "How did Kevin Durant perform across the regular season?",
        "What did Durant average for Houston this season?",
        "Show Kevin Durant's scoring, rebounding, and assist averages.",
        "Give me a regular-season summary for Kevin Durant.",
        "What were Durant's basic numbers this season?",
        "Summarize KD's regular-season box-score production.",
        "Across the season, what did Kevin Durant average?",
    ]
    cases.extend(
        LanguageCase(f"player-summary-{index:02d}", question, "player_summary", "sql")
        for index, question in enumerate(summary_questions, start=1)
    )

    threshold_specs = [
        ("points", "points", (20, 25, 30, 35)),
        ("assists", "assists", (4, 5, 6, 8)),
        ("rebounds", "rebounds", (5, 7, 10, 12)),
        ("steals", "steals", (1, 2, 3, 4)),
        ("three_pointers_made", "three-pointers", (1, 2, 3, 4)),
    ]
    for stat, wording, thresholds in threshold_specs:
        for threshold in thresholds:
            cases.append(
                LanguageCase(
                    f"threshold-{stat}-{threshold}",
                    (
                        "What was Houston's record when Kevin Durant recorded at least "
                        f"{threshold} {wording}?"
                    ),
                    "threshold_record",
                    "sql",
                    {"stat": stat, "threshold": threshold},
                )
            )

    player_metric_specs = [
        ("points", "points"),
        ("assists", "assists"),
        ("rebounds", "rebounds"),
        ("steals", "steals"),
        ("three_pointers_made", "made threes"),
    ]
    aggregation_words = [
        ("sum", "total"),
        ("average", "average"),
        ("maximum", "highest"),
        ("minimum", "lowest"),
    ]
    for stat, wording in player_metric_specs:
        for aggregation, adjective in aggregation_words:
            cases.append(
                LanguageCase(
                    f"player-metric-{stat}-{aggregation}",
                    f"What was Kevin Durant's {adjective} {wording} figure this regular season?",
                    "metric_summary",
                    "sql",
                    {"entity_type": "player", "stat": stat, "aggregation": aggregation},
                )
            )

    team_metric_specs = [
        ("points", "points"),
        ("opponent_points", "points allowed"),
        ("assists", "assists"),
        ("rebounds", "rebounds"),
        ("point_margin", "point margin"),
    ]
    for stat, wording in team_metric_specs:
        for aggregation, adjective in aggregation_words[:3]:
            cases.append(
                LanguageCase(
                    f"team-metric-{stat}-{aggregation}",
                    f"What was Houston's {adjective} {wording} figure this regular season?",
                    "metric_summary",
                    "sql",
                    {"entity_type": "team", "stat": stat, "aggregation": aggregation},
                )
            )

    game_questions = [
        "What was the final score when Houston played Oklahoma City on October 21, 2025?",
        "Who won the Rockets-Thunder game on October 21, 2025?",
        "Give me the game result for Houston versus OKC on October 21, 2025.",
        "What was the final score of the October 21, 2025 Rockets vs Thunder game?",
        "Who won between the Houston Rockets and Oklahoma City Thunder on October 21, 2025?",
    ]
    cases.extend(
        LanguageCase(f"game-result-{index:02d}", question, "game_result", "sql")
        for index, question in enumerate(game_questions, start=1)
    )

    availability_questions = [
        "Why did Kevin Durant miss Houston's game against Phoenix on November 24, 2025?",
        "Did Kevin Durant play when Houston faced Phoenix on November 24, 2025?",
        "Why was Durant out for Rockets-Suns on November 24, 2025?",
        "Check Kevin Durant's availability against Phoenix on November 24, 2025.",
        "Did KD play in the Houston versus Phoenix game on November 24, 2025?",
    ]
    cases.extend(
        LanguageCase(f"availability-{index:02d}", question, "player_availability", "refusal")
        for index, question in enumerate(availability_questions, start=1)
    )

    unsupported_questions = [
        "Which defender guarded Kevin Durant most often this season?",
        "How many off-ball cuts by Durant created an open shot?",
        "Use game video to grade Houston's screen angles.",
        "Who will win Houston's next game?",
        "What is the Rockets live score right now?",
        "Predict Kevin Durant's points tomorrow.",
        "Which matchup forced the most defensive switches onto Durant?",
        "Analyze Houston's off-ball spacing from film.",
        "Project the Rockets' playoff odds.",
        "Show today's live Rockets game score.",
    ]
    cases.extend(
        LanguageCase(f"unsupported-{index:02d}", question, "unsupported", "refusal")
        for index, question in enumerate(unsupported_questions, start=1)
    )

    if len(cases) != 100:
        raise AssertionError(f"Expected exactly 100 language cases, found {len(cases)}")
    return cases

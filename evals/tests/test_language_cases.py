from evals.natural_language_cases import build_language_cases


def test_language_eval_has_exactly_100_unique_cases():
    cases = build_language_cases()

    assert len(cases) == 100
    assert len({case.case_id for case in cases}) == 100
    assert len({case.question for case in cases}) == 100
    assert {case.expected_intent for case in cases} == {
        "team_record",
        "player_summary",
        "threshold_record",
        "metric_summary",
        "game_result",
        "player_availability",
        "unsupported",
    }

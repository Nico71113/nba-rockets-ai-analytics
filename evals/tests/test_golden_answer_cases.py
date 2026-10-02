from evals.golden_answer_cases import build_golden_answer_cases


def test_golden_answer_suite_has_twenty_unique_cases() -> None:
    cases = build_golden_answer_cases()

    assert len(cases) == 20
    assert len({case.case_id for case in cases}) == 20
    assert len({case.question for case in cases}) == 20
    assert any(case.expected_metrics for case in cases)
    assert any(case.expected_method == "refusal" for case in cases)

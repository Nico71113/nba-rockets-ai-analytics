from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from evals.golden_answer_cases import GoldenAnswerCase, build_golden_answer_cases


def _evaluate(case: GoldenAnswerCase, response: dict[str, Any]) -> dict[str, Any]:
    result = response.get("result", {})
    metrics = result.get("metrics", {})
    checks = {
        "intent": response.get("intent") == case.expected_intent,
        "method": result.get("method") == case.expected_method,
        "metrics": all(metrics.get(key) == value for key, value in case.expected_metrics.items()),
        "answer": case.answer_contains is None or case.answer_contains in result.get("answer", ""),
        "coverage": case.coverage_contains is None
        or case.coverage_contains in (result.get("coverage_note") or ""),
    }
    return {
        "case_id": case.case_id,
        "question": case.question,
        "passed": all(checks.values()),
        "checks": checks,
        "expected": {
            "intent": case.expected_intent,
            "method": case.expected_method,
            "metrics": case.expected_metrics,
            "answer_contains": case.answer_contains,
            "coverage_contains": case.coverage_contains,
        },
        "actual": {
            "intent": response.get("intent"),
            "method": result.get("method"),
            "metrics": metrics,
            "answer": result.get("answer"),
            "coverage_note": result.get("coverage_note"),
        },
    }


def run(base_url: str) -> dict[str, Any]:
    cases = build_golden_answer_cases()
    results = []
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=30) as client:
        for case in cases:
            response = client.post("/api/v1/query", json={"question": case.question})
            response.raise_for_status()
            results.append(_evaluate(case, response.json()))
    passed = sum(result["passed"] for result in results)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "summary": {
            "cases": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "accuracy": round(passed / len(results), 4),
        },
        "failures": [result for result in results if not result["passed"]],
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run exact numerical golden-answer evaluation")
    parser.add_argument("--base-url", default="http://localhost:8100")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evals/reports/golden-latest.json"),
    )
    args = parser.parse_args()
    report = run(args.base_url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    if report["summary"]["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

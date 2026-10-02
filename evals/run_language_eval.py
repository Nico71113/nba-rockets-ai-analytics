from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

import httpx

from evals.natural_language_cases import LanguageCase, build_language_cases


def _case_result(case: LanguageCase, response: dict[str, Any]) -> dict[str, Any]:
    interpretation = response.get("interpretation", {})
    checks = {
        "intent": response.get("intent") == case.expected_intent,
        "method": response.get("result", {}).get("method") == case.expected_method,
        "interpretation": all(
            interpretation.get(key) == value
            for key, value in case.expected_interpretation.items()
        ),
    }
    return {
        "case_id": case.case_id,
        "question": case.question,
        "passed": all(checks.values()),
        "checks": checks,
        "expected": {
            "intent": case.expected_intent,
            "method": case.expected_method,
            "interpretation": case.expected_interpretation,
        },
        "actual": {
            "intent": response.get("intent"),
            "method": response.get("result", {}).get("method"),
            "interpretation": interpretation,
            "routing_source": response.get("routing_source"),
            "elapsed_ms": response.get("elapsed_ms"),
            "answer": response.get("result", {}).get("answer"),
        },
    }


def run(base_url: str) -> dict[str, Any]:
    cases = build_language_cases()
    results = []
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=60) as client:
        for case in cases:
            response = client.post("/api/v1/query", json={"question": case.question})
            response.raise_for_status()
            results.append(_case_result(case, response.json()))

    passed = sum(result["passed"] for result in results)
    latency_values = [
        int(result["actual"]["elapsed_ms"])
        for result in results
        if result["actual"]["elapsed_ms"] is not None
    ]
    sorted_latency = sorted(latency_values)
    p95_index = max(0, int(len(sorted_latency) * 0.95) - 1)
    per_intent: dict[str, list[bool]] = defaultdict(list)
    for case, result in zip(cases, results, strict=True):
        per_intent[case.expected_intent].append(result["passed"])

    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "base_url": base_url,
        "summary": {
            "cases": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "accuracy": round(passed / len(results), 4),
            "average_latency_ms": round(mean(latency_values), 1),
            "p95_latency_ms": sorted_latency[p95_index],
            "routing_sources": dict(
                Counter(result["actual"]["routing_source"] for result in results)
            ),
            "accuracy_by_intent": {
                intent: round(sum(values) / len(values), 4)
                for intent, values in sorted(per_intent.items())
            },
        },
        "failures": [result for result in results if not result["passed"]],
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the 100-question API evaluation")
    parser.add_argument("--base-url", default="http://localhost:8100")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evals/reports/latest.json"),
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

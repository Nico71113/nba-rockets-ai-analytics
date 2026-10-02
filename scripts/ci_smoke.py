from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


def request(url: str, *, payload: dict[str, str] | None = None) -> tuple[int, bytes]:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if body else {}
    with urllib.request.urlopen(
        urllib.request.Request(url, data=body, headers=headers), timeout=5
    ) as response:
        return response.status, response.read()


def wait_for(url: str) -> None:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            status, _ = request(url)
            if status == 200:
                return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2)
    raise RuntimeError(f"Timed out waiting for {url}")


def main() -> None:
    wait_for("http://localhost:8100/health")
    wait_for("http://localhost:4300/")
    status, coverage_body = request("http://localhost:8100/api/v1/coverage")
    coverage = json.loads(coverage_body)
    if status != 200 or coverage["games"] < 0:
        raise RuntimeError("Coverage endpoint failed its response contract")

    status, query_body = request(
        "http://localhost:8100/api/v1/query",
        payload={"question": "Which defender guarded Kevin Durant most often this season?"},
    )
    query = json.loads(query_body)
    if (
        status != 200
        or query["routing_source"] != "coverage_guard"
        or query["result"]["method"] != "refusal"
    ):
        raise RuntimeError("Coverage-guard query failed its response contract")

    print("Docker smoke test passed: database, API, and frontend are reachable.")


if __name__ == "__main__":
    main()

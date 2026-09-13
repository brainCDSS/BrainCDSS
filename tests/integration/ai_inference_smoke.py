"""Exercise API -> RabbitMQ -> Celery -> mock -> PostgreSQL -> API."""

import json
import subprocess
import time
from urllib.request import Request, urlopen


ROOT = "http://127.0.0.1:8080/api/v1/dev/ai-analyses"


def request_json(url, body=None):
    request = Request(
        url,
        data=None if body is None else json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    with urlopen(request, timeout=10) as response:
        return response.status, json.load(response)


def prepare_references():
    output = subprocess.check_output([
        "docker", "compose", "exec", "-T", "backend",
        "python", "manage.py", "prepare_inference_development",
    ], text=True)
    return json.loads(output.strip().splitlines()[-1])


def run_case(references, outcome, expected):
    status, created = request_json(ROOT, {
        **references,
        "analysis_type": "MOCK_INFERENCE",
        "priority": "NORMAL",
        "outcome": outcome,
    })
    assert status == 202 and created["status"] == "QUEUED", created
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        _, current = request_json(ROOT + "/" + created["analysis_id"])
        if current["status"] in {"COMPLETED", "FAILED"}:
            break
        time.sleep(0.25)
    assert current["status"] == expected, current
    assert [row["status"] for row in current["history"]] == [
        "QUEUED", "PROCESSING", expected,
    ], current
    if expected == "COMPLETED":
        assert current["result"]["is_mock"] is True, current
        assert current["result"]["accuracy_simulated"] is False, current
    else:
        assert current["failure_code"] == "MOCK_INFERENCE_FAILED", current
        assert current["result"] is None, current
    print(json.dumps(current, ensure_ascii=False))


def main():
    references = prepare_references()
    run_case(references, "success", "COMPLETED")
    run_case(references, "failure", "FAILED")


if __name__ == "__main__":
    main()

"""Locust load test for Remembr memory lifecycle.

Run:
    pip install locust
    REMEMBR_API_KEY=<key> locust -f tests/performance/locustfile.py --host https://api.remembr.dev

Suggested run profile:
    - 10 users, spawn rate 2
    - run time: 60s
"""

from __future__ import annotations

import os
from typing import Any

from locust import HttpUser, between, events, task

API_PREFIX = os.getenv("REMEMBR_API_PREFIX", "/api/v1")
API_KEY = os.getenv("REMEMBR_API_KEY", "")

STORE_P95_MS = int(os.getenv("REMEMBR_STORE_P95_MS", "500"))
SEARCH_P95_MS = int(os.getenv("REMEMBR_SEARCH_P95_MS", "1000"))


class MemoryLifecycleUser(HttpUser):
    wait_time = between(0.2, 1.0)

    def on_start(self) -> None:
        if not API_KEY:
            raise RuntimeError("REMEMBR_API_KEY is required for load test")

        self.headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }

    @task
    def memory_lifecycle(self) -> None:
        session_id = self._create_session()
        if not session_id:
            return

        for i in range(5):
            self.client.post(
                f"{API_PREFIX}/memory",
                headers=self.headers,
                json={
                    "role": "user",
                    "content": f"Load-test message {i}: service preference and context",
                    "session_id": session_id,
                },
                name="POST /memory",
            )

        self.client.post(
            f"{API_PREFIX}/memory/search",
            headers=self.headers,
            json={
                "query": "service preference",
                "session_id": session_id,
                "limit": 5,
            },
            name="POST /memory/search",
        )

        self.client.post(
            f"{API_PREFIX}/sessions/{session_id}/checkpoint",
            headers=self.headers,
            name="POST /sessions/:id/checkpoint",
        )

    def _create_session(self) -> str | None:
        with self.client.post(
            f"{API_PREFIX}/sessions",
            headers=self.headers,
            json={"metadata": {"source": "locust"}},
            name="POST /sessions",
            catch_response=True,
        ) as response:
            if response.status_code >= 400:
                response.failure(f"Session creation failed: {response.status_code}")
                return None

            body: dict[str, Any] = response.json()
            data = body.get("data", {}) if isinstance(body, dict) else {}
            return data.get("session_id")


@events.quitting.add_listener
def _(environment, **kwargs):
    """Fail load run if p95 SLO assertions are violated."""
    stats = environment.stats

    store = stats.get("POST /memory", "POST")
    search = stats.get("POST /memory/search", "POST")

    failed = False
    if store and store.get_response_time_percentile(0.95) > STORE_P95_MS:
        print(f"[SLO] FAIL: POST /memory p95={store.get_response_time_percentile(0.95):.1f}ms > {STORE_P95_MS}ms")
        failed = True
    if search and search.get_response_time_percentile(0.95) > SEARCH_P95_MS:
        print(f"[SLO] FAIL: POST /memory/search p95={search.get_response_time_percentile(0.95):.1f}ms > {SEARCH_P95_MS}ms")
        failed = True

    if failed:
        environment.process_exit_code = 1
        return

    print("[SLO] PASS: latency thresholds satisfied")
    environment.process_exit_code = 0

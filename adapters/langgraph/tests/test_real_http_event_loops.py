"""Regression test: sequential sync adapter calls over real HTTP keep-alive connections.

The other adapter tests mock the client, so they never touch an event loop's
sockets. Before the fix, ``BaseRemembrAdapter._run`` ran each call in a new
``asyncio.run()`` loop while ``RemembrClient`` reused one ``httpx.AsyncClient``
whose pooled connection belonged to the previous, closed loop, so every second
call failed with ``RuntimeError: Event loop is closed``.

This test starts a small in-process HTTP/1.1 keep-alive server that stands in
for the Remembr API (only the endpoints used here) and drives the real SDK
through the real LangGraph adapter.
"""

from __future__ import annotations

import datetime
import json
import threading
import uuid
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from remembr import RemembrClient

from adapters.langgraph.remembr_langgraph_memory import RemembrLangGraphMemory


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class _StandInRemembr(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.requests: list[tuple[str, str, str | None]] = []
        self.episodes: list[dict] = []
        self.lock = threading.Lock()


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # keep connections alive between requests
    server: _StandInRemembr

    def log_message(self, *args: object) -> None:
        pass

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        api_key = self.headers.get("x-api-key")
        with self.server.lock:
            self.server.requests.append(("POST", self.path, api_key))
        if api_key is None:
            self._send(401, {"error": {"code": "UNAUTHORIZED", "message": "X-API-Key missing"}})
            return

        if self.path.endswith("/sessions"):
            data = {
                "request_id": "req",
                "session_id": str(uuid.uuid4()),
                "org_id": "org",
                "created_at": _now(),
                "metadata": body.get("metadata"),
            }
        elif self.path.endswith("/memory/search"):
            with self.server.lock:
                hits = [e for e in self.server.episodes if e["session_id"] == body.get("session_id")]
            data = {
                "request_id": "req",
                "total": len(hits),
                "query_time_ms": 1,
                "results": [
                    {
                        "episode_id": e["episode_id"],
                        "content": e["content"],
                        "role": e["role"],
                        "score": 1.0,
                        "created_at": e["created_at"],
                        "tags": e["tags"],
                    }
                    for e in hits
                ],
            }
        elif self.path.endswith("/memory"):
            data = {
                "episode_id": str(uuid.uuid4()),
                "session_id": body.get("session_id"),
                "role": body["role"],
                "content": body["content"],
                "tags": body.get("tags", []),
                "created_at": _now(),
                "embedding_status": "pending",
            }
            with self.server.lock:
                self.server.episodes.append(data)
        else:
            self._send(404, {"error": {"code": "NOT_FOUND", "message": self.path}})
            return
        self._send(200, {"data": data})

    def _send(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


@pytest.fixture
def stand_in_server() -> Iterator[_StandInRemembr]:
    server = _StandInRemembr()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


def test_sequential_sync_calls_over_real_http(stand_in_server: _StandInRemembr) -> None:
    host, port = stand_in_server.server_address[:2]
    client = RemembrClient(api_key="rk_test_key", base_url=f"http://{host}:{port}/api/v1")

    # Call 1: the adapter creates a session.
    memory = RemembrLangGraphMemory(client=client, search_mode="keyword")
    config = {"configurable": {"thread_id": "thread-1"}}
    turn_one = {
        "messages": [
            {"role": "user", "content": "project codename atlas"},
            {"role": "assistant", "content": "noted: atlas"},
        ]
    }
    turn_two = {
        "messages": [
            {"role": "user", "content": "deadline is friday"},
            {"role": "assistant", "content": "noted: friday"},
        ]
    }

    # Calls 2-3: two stores. Call 4: a search. Calls 5-6: two stores. Call 7: a search.
    memory.save_memories(turn_one, config)
    loaded_one = memory.load_memories(turn_one, config)
    memory.save_memories(turn_two, config)
    loaded_two = memory.load_memories(turn_two, config)

    paths = [path for _, path, _ in stand_in_server.requests]
    assert paths == [
        "/api/v1/sessions",
        "/api/v1/memory",
        "/api/v1/memory",
        "/api/v1/memory/search",
        "/api/v1/memory",
        "/api/v1/memory",
        "/api/v1/memory/search",
    ]
    assert all(key == "rk_test_key" for _, _, key in stand_in_server.requests)
    assert "atlas" in loaded_one["remembr_context"]
    assert "atlas" in loaded_two["remembr_context"]
    assert "friday" in loaded_two["remembr_context"]

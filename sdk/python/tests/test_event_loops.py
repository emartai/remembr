"""One RemembrClient used from several event loops over real keep-alive HTTP.

Sync callers (``RemembrClient.request``, the CLI, framework adapters) run each
call in its own ``asyncio.run()`` loop. Before the fix the cached
``httpx.AsyncClient`` kept a pooled connection bound to the first, closed, loop
and every second call raised ``RuntimeError: Event loop is closed``.
"""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from remembr import RemembrClient


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"  # keep-alive, so connections are pooled

    def log_message(self, *args: object) -> None:
        pass

    def do_GET(self) -> None:  # noqa: N802
        self.server.api_keys.append(self.headers.get("x-api-key"))  # type: ignore[attr-defined]
        raw = json.dumps({"data": {"status": "ok", "path": self.path}}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


@pytest.fixture
def keep_alive_server() -> Iterator[ThreadingHTTPServer]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    server.api_keys = []  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


def _client_for(server: ThreadingHTTPServer) -> RemembrClient:
    host, port = server.server_address[:2]
    return RemembrClient(api_key="rk_loop_test", base_url=f"http://{host}:{port}/api/v1")


def test_sync_request_repeatedly(keep_alive_server: ThreadingHTTPServer) -> None:
    client = _client_for(keep_alive_server)
    for i in range(4):
        assert client.request("GET", f"/health?n={i}")["status"] == "ok"
        assert client._client is None
    assert keep_alive_server.api_keys == ["rk_loop_test"] * 4  # type: ignore[attr-defined]


def test_asyncio_run_per_call(keep_alive_server: ThreadingHTTPServer) -> None:
    client = _client_for(keep_alive_server)
    for i in range(4):
        data = asyncio.run(client.arequest("GET", f"/health?n={i}"))
        assert data["path"] == f"/api/v1/health?n={i}"


async def test_client_reused_within_one_loop(keep_alive_server: ThreadingHTTPServer) -> None:
    client = _client_for(keep_alive_server)
    await client.arequest("GET", "/health")
    first = client._client
    await client.arequest("GET", "/health")
    assert client._client is first
    await client.aclose()
    assert client._client is None


def test_injected_client_is_kept_across_loops() -> None:
    """A client assigned from outside (here a mock transport) is never replaced."""
    import httpx

    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json={"data": {"status": "ok"}})

    client = RemembrClient(api_key="rk_injected", base_url="https://example.test/api/v1")
    injected = httpx.AsyncClient(base_url=client.base_url, transport=httpx.MockTransport(handler))
    client._client = injected
    for _ in range(3):
        assert client.request("GET", "/health")["status"] == "ok"
    assert client._client is injected
    assert seen == ["https://example.test/api/v1/health"] * 3

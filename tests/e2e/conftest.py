from __future__ import annotations

import os
import sys
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SDK_PATH = os.path.join(ROOT, "sdk", "python")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if SDK_PATH not in sys.path:
    sys.path.insert(0, SDK_PATH)


def _load_client_class() -> Any:
    try:
        from remembr import RemembrClient
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Remembr SDK dependencies unavailable for E2E tests: {exc}")
    return RemembrClient


@pytest.fixture(scope="session")
def e2e_api_key() -> str:
    api_key = os.getenv("REMEMBR_E2E_API_KEY")
    if not api_key:
        pytest.skip("REMEMBR_E2E_API_KEY is not set; skipping E2E suite.")
    return api_key


@pytest.fixture(scope="session")
def e2e_base_url() -> str:
    return os.getenv("REMEMBR_E2E_BASE_URL", "http://localhost:8000/api/v1")


@pytest.fixture
async def e2e_client(e2e_api_key: str, e2e_base_url: str) -> AsyncIterator[Any]:
    RemembrClient = _load_client_class()
    client = RemembrClient(api_key=e2e_api_key, base_url=e2e_base_url)
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
def test_org_id() -> str:
    return f"e2e-org-{uuid.uuid4()}"


@pytest.fixture
def test_session() -> str:
    return f"e2e-session-{uuid.uuid4()}"


@pytest.fixture
def cleanup_user_id() -> str:
    return os.getenv("REMEMBR_E2E_USER_ID", str(uuid.uuid4()))


@pytest.fixture
def tracked_sessions() -> list[str]:
    return []


@pytest.fixture
def tracked_episodes() -> list[str]:
    return []


@pytest.fixture(autouse=True)
async def cleanup(
    e2e_client: Any,
    cleanup_user_id: str,
    tracked_sessions: list[str],
    tracked_episodes: list[str],
) -> AsyncIterator[None]:
    yield

    for episode_id in tracked_episodes:
        try:
            await e2e_client.forget_episode(episode_id)
        except Exception:
            pass

    for session_id in tracked_sessions:
        try:
            await e2e_client.forget_session(session_id)
        except Exception:
            pass

    try:
        await e2e_client.forget_user(cleanup_user_id)
    except Exception:
        pass


@pytest.fixture(scope="session")
def org_api_key_a() -> str:
    return os.getenv("REMEMBR_E2E_API_KEY_ORG_A") or os.getenv("REMEMBR_E2E_API_KEY") or ""


@pytest.fixture(scope="session")
def org_api_key_b() -> str:
    return os.getenv("REMEMBR_E2E_API_KEY_ORG_B") or ""


@pytest.fixture(scope="session")
def org_base_url() -> str:
    return os.getenv("REMEMBR_E2E_BASE_URL", "http://localhost:8000/api/v1")


@pytest.fixture
async def org_a_client(org_api_key_a: str, org_base_url: str) -> AsyncIterator[Any]:
    if not org_api_key_a:
        pytest.skip("REMEMBR_E2E_API_KEY_ORG_A or REMEMBR_E2E_API_KEY is required.")
    RemembrClient = _load_client_class()
    client = RemembrClient(api_key=org_api_key_a, base_url=org_base_url)
    try:
        yield client
    finally:
        await client.aclose()


@pytest.fixture
async def org_b_client(org_api_key_b: str, org_base_url: str) -> AsyncIterator[Any]:
    if not org_api_key_b:
        pytest.skip("REMEMBR_E2E_API_KEY_ORG_B is required for org isolation test.")
    RemembrClient = _load_client_class()
    client = RemembrClient(api_key=org_api_key_b, base_url=org_base_url)
    try:
        yield client
    finally:
        await client.aclose()

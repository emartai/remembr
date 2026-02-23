"""Lightweight local pytest-asyncio compatibility plugin.

Provides enough functionality for this repository's async tests without requiring
an external pytest-asyncio package in constrained environments.
"""

from __future__ import annotations

import asyncio
import inspect

import pytest

fixture = pytest.fixture


def pytest_configure(config: pytest.Config) -> None:
    """Register asyncio marker for tests executed by this plugin."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test to run in an asyncio event loop",
    )


def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Execute `@pytest.mark.asyncio` coroutine tests in an event loop."""
    if pyfuncitem.get_closest_marker("asyncio") is None:
        return None

    test_func = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_func):
        return None

    loop = pyfuncitem.funcargs.get("event_loop")
    created_loop = False
    if loop is None:
        loop = asyncio.new_event_loop()
        created_loop = True

    kwargs = {
        arg: pyfuncitem.funcargs[arg]
        for arg in pyfuncitem._fixtureinfo.argnames
        if arg in pyfuncitem.funcargs
    }

    try:
        loop.run_until_complete(test_func(**kwargs))
    finally:
        if created_loop:
            loop.close()

    return True

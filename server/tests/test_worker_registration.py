"""A fresh worker must load the task names published by the API and scheduler."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def test_fresh_worker_process_registers_memory_and_lifecycle_tasks():
    code = """
from app.celery_app import celery_app
celery_app.loader.import_default_modules()
required = {
    'app.tasks.embeddings.generate_embedding_for_episode',
    'app.tasks.cleanup.purge_soft_deleted',
    'app.tasks.webhooks.deliver_webhook',
    'app.tasks.project_memory.embed',
}
missing = required - set(celery_app.tasks)
assert not missing, f'Worker is missing tasks: {missing}'
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "OTEL_ENABLED": "false"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tasks,ready",
    [
        ([], False),
        (["app.tasks.embeddings.generate_embedding_for_episode"], False),
        (["app.tasks.project_memory.embed"], False),
        (
            [
                "app.tasks.embeddings.generate_embedding_for_episode",
                "app.tasks.project_memory.embed",
            ],
            True,
        ),
    ],
)
async def test_worker_readiness_requires_both_embedding_tasks(monkeypatch, tasks, ready):
    from app.celery_app import celery_app
    from app.services.readiness import check_worker

    inspection = MagicMock()
    inspection.registered.return_value = {"alive-worker": tasks}
    monkeypatch.setattr(celery_app.control, "inspect", lambda **kwargs: inspection)
    if ready:
        await check_worker()
    else:
        with pytest.raises(RuntimeError, match="embedding tasks"):
            await check_worker()


@pytest.mark.asyncio
async def test_worker_readiness_does_not_combine_incomplete_workers(monkeypatch):
    from app.celery_app import celery_app
    from app.services.readiness import check_worker

    inspection = MagicMock()
    inspection.registered.return_value = {
        "legacy-only": ["app.tasks.embeddings.generate_embedding_for_episode"],
        "project-only": ["app.tasks.project_memory.embed"],
    }
    monkeypatch.setattr(celery_app.control, "inspect", lambda **kwargs: inspection)
    with pytest.raises(RuntimeError, match="both embedding tasks"):
        await check_worker()

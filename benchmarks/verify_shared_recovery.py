"""Live local recovery probe using an owned disposable database and containers."""

import argparse
import json
import secrets
import subprocess
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError

from benchmarks.locomo import ROOT, Http, state_paths, write_json


def run(*args):
    return subprocess.check_output(
        args, text=True, encoding="utf-8", errors="replace", stderr=subprocess.STDOUT
    ).strip()


def cleanup_services(owned, database, database_created, work):
    errors = []
    for name in reversed(owned):
        try:
            log = run("docker", "logs", "--tail", "80", name)
            (work / (name + ".log")).write_text(log, encoding="utf-8")
        except Exception:
            pass  # Logging is best effort; stopping the container is mandatory.
        try:
            run("docker", "stop", name)
            run("docker", "rm", name)
        except Exception:
            errors.append(name)
    if database_created:
        try:
            run(
                "docker",
                "exec",
                "remembr-postgres",
                "dropdb",
                "-U",
                "remembr",
                database,
            )
        except Exception:
            errors.append(database)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", required=True, type=Path)
    args = parser.parse_args()
    work = state_paths(args.work_dir)
    if (work / "live-result.json").exists():
        raise ValueError("Preserve the previous probe; use a new work directory")
    suffix = uuid.uuid4().hex[:12]
    database = "remembr_probe_" + suffix
    api, worker, redis = [
        "remembr-probe-" + suffix + "-" + name for name in ("api", "worker", "redis")
    ]
    owned = []
    database_created = False
    result = {
        "scope": "Five independent Remembr credentials, real API/worker restarts and provider outage; not a Claude/Codex login-switch test",
        "checks": {},
    }
    base_env = [
        "--env",
        "DATABASE_URL=postgresql://remembr:remembr@remembr-postgres:5432/" + database,
        "--env",
        "REDIS_URL=redis://" + redis + ":6379/0",
        "--env",
        "SECRET_KEY=disposable-live-probe-only",
        "--env",
        "EMBEDDING_PROVIDER=ollama",
        "--env",
        "OLLAMA_EMBEDDING_MODEL=nomic-embed-text:publisher-f16",
        "--env",
        "OLLAMA_TASK_MODE=nomic_search",
    ]
    source = ["--volume", str(ROOT / "server") + ":/app:ro"]

    def launch(name, command, provider="http://host.docker.internal:11434", port=False):
        command_line = [
            "docker",
            "run",
            "-d",
            "--pull",
            "never",
            "--name",
            name,
            "--network",
            "remembr_default",
            "--memory",
            "384m",
            *base_env,
            "--env",
            "OLLAMA_BASE_URL=" + provider,
            *source,
        ]
        if port:
            command_line += ["--publish", "127.0.0.1:18000:8000"]
        owned.append(name)
        run(*command_line, "remembr-server:latest", *command)

    def remove(name):
        run("docker", "stop", name)
        run("docker", "rm", name)
        owned.remove(name)

    http = Http("http://127.0.0.1:18000/api/v1", interval=0.7, timeout=30)

    def wait_api():
        deadline = time.monotonic() + 120
        while True:
            try:
                http.call("GET", "/health")
                return
            except Exception:
                if time.monotonic() > deadline:
                    raise TimeoutError("Probe API did not start")
                time.sleep(1)

    try:
        run("docker", "exec", "remembr-postgres", "createdb", "-U", "remembr", database)
        database_created = True
        run(
            "docker",
            "run",
            "-d",
            "--pull",
            "never",
            "--name",
            redis,
            "--network",
            "remembr_default",
            "--memory",
            "64m",
            "redis:7-alpine",
        )
        owned.append(redis)
        migration = run(
            "docker",
            "run",
            "--rm",
            "--pull",
            "never",
            "--network",
            "remembr_default",
            *base_env,
            *source,
            "remembr-server:latest",
            "alembic",
            "upgrade",
            "head",
        )
        (work / "migration.log").write_text(migration, encoding="utf-8")
        launch(
            api,
            ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"],
            port=True,
        )
        wait_api()
        identity = {
            "email": "probe-" + suffix + "@example.com",
            "password": secrets.token_urlsafe(32),
            "org_name": "Disposable recovery probe",
        }
        token = http.call("POST", "/auth/register", identity)["data"]["access_token"]

        def call(method, path, body=None, key=None):
            return http.call(
                method, "/projects" + path, body, key=key, token=None if key else token
            )["data"]

        project = call("POST", "", {"name": "Disposable five-profile probe"})
        space = call(
            "POST", f"/{project['id']}/spaces", {"name": "Shared corrections"}
        )["id"]
        principals = [
            call("POST", "/principals", {"name": "Runtime profile " + str(i)})
            for i in range(5)
        ]
        write_json(
            work / "private.json", {"identity": identity, "principals": principals}
        )
        for principal in principals:
            call(
                "PUT",
                f"/spaces/{space}/grants/{principal['id']}",
                {"can_read": True, "can_write": True},
            )
        worker_command = [
            "celery",
            "-A",
            "app.celery_app:celery_app",
            "worker",
            "--pool=solo",
            "--concurrency=1",
            "--loglevel=WARNING",
        ]
        launch(worker, worker_command, provider="http://127.0.0.1:1")
        payload = {
            "content": "The project uses PostgreSQL.",
            "idempotency_key": "probe-original",
            "source_ref": "probe:source",
        }
        original = call(
            "POST", f"/spaces/{space}/memories", payload, principals[0]["api_key"]
        )

        def wait_status(memory_id, expected):
            deadline = time.monotonic() + 150
            while True:
                status = call("GET", f"/spaces/{space}/memories/{memory_id}/status")
                if status["embedding_status"] == expected:
                    return
                if time.monotonic() > deadline:
                    raise TimeoutError("Expected embedding status " + expected)
                time.sleep(1)

        wait_status(original["id"], "failed")
        result["checks"]["real_provider_outage_records_failure"] = True
        remove(worker)
        launch(worker, worker_command)
        retried = call(
            "POST",
            f"/spaces/{space}/memories/{original['id']}/retry-embedding",
            {},
            principals[0]["api_key"],
        )
        assert retried["queued"] and retried["id"] == original["id"]
        wait_status(original["id"], "ready")
        result["checks"]["retry_recovers_same_memory_after_provider_restoration"] = True
        run("docker", "stop", worker)
        correction = call(
            "POST",
            f"/spaces/{space}/memories",
            {
                "content": "Correction: the project uses PostgreSQL with pgvector.",
                "idempotency_key": "probe-correction",
                "supersedes_id": original["id"],
                "source_ref": "probe:correction",
            },
            principals[2]["api_key"],
        )
        assert correction["embedding_status"] == "pending"
        run("docker", "restart", api)
        wait_api()
        replay = call(
            "POST", f"/spaces/{space}/memories", payload, principals[0]["api_key"]
        )
        assert replay["id"] == original["id"]
        for principal in principals:
            visible = call("POST", f"/spaces/{space}/search", {}, principal["api_key"])
            assert [r["id"] for r in visible["results"]] == [correction["id"]]
        result["checks"]["five_credentials_and_idempotency_survive_api_restart"] = True
        run("docker", "start", worker)
        wait_status(correction["id"], "ready")
        for principal in principals:
            visible = call(
                "POST",
                f"/spaces/{space}/search",
                {"query": "PostgreSQL", "mode": "semantic"},
                principal["api_key"],
            )
            assert visible["results"][0]["id"] == correction["id"]
            assert visible["results"][0]["author_id"] == principals[2]["id"]
        result["checks"]["queued_correction_survives_worker_restart"] = True
        assert not call(
            "POST",
            f"/spaces/{space}/memories/{correction['id']}/retry-embedding",
            {},
            principals[1]["api_key"],
        )["queued"]
        call("DELETE", f"/principals/{principals[0]['id']}")
        try:
            call("POST", f"/spaces/{space}/search", {}, principals[0]["api_key"])
            raise AssertionError("Revoked credential was accepted")
        except HTTPError as exc:
            assert exc.code == 401
        for principal in principals[1:]:
            assert (
                call(
                    "GET",
                    f"/spaces/{space}/memories/{correction['id']}",
                    key=principal["api_key"],
                )["author_id"]
                == principals[2]["id"]
            )
        result["checks"]["revocation_is_independent"] = True
        for memory in (original, correction):
            call("DELETE", f"/spaces/{space}/memories/{memory['id']}")
        result["passed"] = True
    except Exception as exc:
        result.update(passed=False, error=type(exc).__name__)
        raise
    finally:
        cleanup_errors = cleanup_services(owned, database, database_created, work)
        result["cleanup_errors"] = cleanup_errors
        write_json(work / "live-result.json", result)
        print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()

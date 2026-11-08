"""Explicit, zero-cost pilot model adapters with no paid-model fallback."""

import json
import os
import time
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def request(base, method, path, payload=None, key=None):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = Request(
        base + path,
        method=method,
        headers=headers,
        data=json.dumps(payload).encode() if payload is not None else None,
    )
    with urlopen(req, timeout=600) as response:
        return json.load(response)


def validate_free_entry(model):
    if not model["id"].endswith(":free"):
        raise ValueError(
            "Select one explicit :free model, not an automatic or paid router"
        )
    if not {"prompt", "completion"} <= model.get("pricing", {}).keys():
        raise ValueError("Missing catalog prices; refuse to assume a free request")
    for field in ("prompt", "completion", "request"):
        if Decimal(str(model.get("pricing", {}).get(field, "0"))) != 0:
            raise ValueError(
                "Catalog pricing is not zero; this runner will not send the request"
            )


def configured_key(variable):
    if os.environ.get(variable):
        return os.environ[variable]
    path = Path(__file__).resolve().parents[1] / ".env.benchmarks"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() == variable:
                return value.strip().strip("\"'") or None
    return None


class CompletionClient:
    def __init__(
        self,
        provider,
        model,
        *,
        ollama_url="http://127.0.0.1:11434",
        free_account=False,
    ):
        self.provider, self.model, self.key = provider, model, None
        self.last_request = 0.0
        if provider == "ollama":
            from urllib.parse import urlparse

            parsed = urlparse(ollama_url)
            if (
                parsed.scheme not in {"http", "https"}
                or parsed.username
                or parsed.password
                or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            ):
                raise ValueError("Use a local Ollama endpoint")
            self.base = ollama_url.rstrip("/")
            models = request(self.base, "GET", "/api/tags")["models"]
            self.model_info = next((m for m in models if m["name"] == model), None)
            if self.model_info is None:
                raise ValueError(
                    "Model is not downloaded; no automatic model pull is performed"
                )
        elif provider in {"groq", "openrouter"}:
            if not free_account:
                raise ValueError(
                    "Confirm a free account with --confirm-free-account before API use"
                )
            variable = "GROQ_API_KEY" if provider == "groq" else "OPENROUTER_API_KEY"
            self.key = configured_key(variable)
            if not self.key:
                raise ValueError(
                    f"Configure {variable} locally; never put a key in command arguments"
                )
            self.base = (
                "https://api.groq.com/openai/v1"
                if provider == "groq"
                else "https://openrouter.ai/api/v1"
            )
            catalog = request(self.base, "GET", "/models", key=self.key)["data"]
            entry = next((m for m in catalog if m["id"] == model), None)
            if entry is None:
                raise ValueError("Requested model is absent from the provider catalog")
            if provider == "openrouter":
                validate_free_entry(entry)
            self.model_info = {
                k: entry[k]
                for k in ("id", "name", "pricing", "context_length")
                if k in entry
            }
        else:
            raise ValueError("Unsupported provider")

    def complete(self, messages, *, json_output=False):
        if self.provider == "ollama":
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "think": False,
                "keep_alive": "2m",
                "options": {
                    "temperature": 0,
                    "seed": 42,
                    "num_ctx": 8192,
                    "num_predict": 256,
                },
            }
            if json_output:
                payload["format"] = "json"
            response = request(self.base, "POST", "/api/chat", payload)
            return {
                "text": response["message"]["content"],
                "model": response["model"],
                "finish_reason": response.get("done_reason"),
                "prompt_tokens": response.get("prompt_eval_count"),
                "completion_tokens": response.get("eval_count"),
                "total_duration_ns": response.get("total_duration"),
            }
        time.sleep(max(0, 3.1 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 256,
        }
        if json_output:
            payload["response_format"] = {"type": "json_object"}
        # One model only. In particular, never add a paid fallback to a free route.
        try:
            response = request(
                self.base, "POST", "/chat/completions", payload, self.key
            )
        except HTTPError as error:
            if error.code == 429:
                raise RuntimeError(
                    "Provider rate limit reached. Outputs are checkpointed; resume after the provider's reset."
                ) from error
            raise
        usage = response.get("usage", {})
        if usage.get("cost") is not None and Decimal(str(usage["cost"])) > 0:
            raise RuntimeError(
                "Provider reported a charge; stop the free-only evaluation"
            )
        choice = response["choices"][0]
        return {
            "text": choice["message"]["content"],
            "model": response["model"],
            "finish_reason": choice.get("finish_reason"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "system_fingerprint": response.get("system_fingerprint"),
            "provider_reported_cost": usage.get("cost"),
        }

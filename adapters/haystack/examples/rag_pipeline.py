"""RAG pipeline example using Remembr memory in Haystack components.

Usage:
    PYTHONPATH=./sdk/python:. python adapters/haystack/examples/rag_pipeline.py
"""

from __future__ import annotations

import os

from adapters.haystack.remembr_haystack_memory import build_remembr_rag_pipeline
from remembr import RemembrClient


class DemoLLM:
    def run(self, prompt: str | None = None, **kwargs):
        text = prompt or kwargs.get("prompt") or ""
        return {"replies": f"LLM answer based on: {text}"}


def main() -> None:
    client = RemembrClient(api_key=os.environ["REMEMBR_API_KEY"])
    pipeline = build_remembr_rag_pipeline(client=client, llm_component=DemoLLM())

    run_1 = pipeline.run(
        {
            "memory_retriever": {"query": "user preference"},
            "prompt_builder": {"query": "User asked for concise summary"},
        }
    )
    run_2 = pipeline.run(
        {
            "memory_retriever": {"query": "concise summary"},
            "prompt_builder": {"query": "What style should we use?"},
        }
    )

    print("Run 1:", run_1)
    print("Run 2:", run_2)


if __name__ == "__main__":
    main()

# Multi-Agent Shared Memory

For independent agents or hosts, use a [shared project space](../shared-project-memory.md). Give each connection its own credential. Follow the [agent connection guide](../agent-connections.md#acceptance-sequence) to run the LangGraph, Claude Code and Codex handoff.

## Coordinating nodes within one workflow

Within a single application, use private session memory and structured tags so each node can retrieve the context it needs. This example uses one application credential and one session.

## Why it helps

- Research, writing, and review agents share durable state
- Each agent can query `kind:*` tags instead of replaying the whole transcript
- Review feedback from a previous run can guide the next run

## Example

See the [LangGraph workflow example](https://github.com/emartai/remembr/tree/main/examples/langgraph-multi-agent).

```python
import asyncio

from remembr import RemembrClient, TagFilter


async def main() -> None:
    async with RemembrClient(api_key="YOUR_API_KEY") as client:
        session = await client.create_session(metadata={"topic": "transformers"})
        await client.store(
            "Need stronger evidence around inference cost tradeoffs.",
            role="assistant",
            session_id=session.session_id,
            tags=["agent:review", "topic:transformers", "kind:feedback", "confidence:0.6"],
        )
        feedback = await client.search(
            "How should research improve next time?",
            session_id=session.session_id,
            tag_filters=[TagFilter(key="kind", value="feedback")],
            search_mode="keyword",
        )
        print(feedback.total)


asyncio.run(main())
```


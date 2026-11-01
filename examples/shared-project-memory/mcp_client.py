"""Protocol acceptance client. This is not a Claude Code or Codex model session."""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    parameters = StdioServerParameters(
        command=sys.executable, args=["-m", "remembr.mcp"], env=dict(os.environ)
    )
    async with stdio_client(parameters) as (read, write):  # noqa: SIM117
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {t.name for t in tools.tools} == {
                "store_memory",
                "search_memory",
                "get_memory",
                "get_processing_status",
            }
            found = await session.call_tool(
                "search_memory",
                {
                    "query": os.environ["REMEMBR_DEMO_QUERY"],
                    "mode": "keyword",
                },
            )
            assert not found.isError, str(found.content)
            payload = found.structuredContent
            if payload is None:
                payload = json.loads(found.content[0].text)
            if os.getenv("REMEMBR_DEMO_ACTION") == "correct":
                original = payload["results"][0]
                saved = await session.call_tool(
                    "store_memory",
                    {
                        "content": os.environ["REMEMBR_DEMO_CORRECTION"],
                        "idempotency_key": os.environ["REMEMBR_DEMO_KEY"],
                        "source_ref": "synthetic:mcp-correction",
                        "supersedes_id": original["id"],
                    },
                )
                assert not saved.isError, str(saved.content)
                payload = saved.structuredContent or json.loads(saved.content[0].text)
            print(json.dumps(payload))


if __name__ == "__main__":
    asyncio.run(main())

"""Read tools must be distinguishable from writes in approval-aware MCP hosts."""

import uuid

import pytest

pytest.importorskip("mcp")


@pytest.mark.asyncio
async def test_mcp_read_and_write_annotations(monkeypatch):
    from remembr.mcp import build_server

    monkeypatch.setenv("REMEMBR_SPACE_ID", str(uuid.uuid4()))
    monkeypatch.setenv("REMEMBR_API_KEY", "rmsp_metadata_test")
    tools = {tool.name: tool for tool in await build_server().list_tools()}
    assert set(tools) == {
        "store_memory",
        "search_memory",
        "get_memory",
        "get_processing_status",
    }
    for name in ("search_memory", "get_memory", "get_processing_status"):
        assert tools[name].annotations.readOnlyHint is True
        assert tools[name].annotations.destructiveHint is False
        assert tools[name].annotations.openWorldHint is False
    assert tools["store_memory"].annotations.readOnlyHint is False
    assert tools["store_memory"].annotations.destructiveHint is True
    assert tools["store_memory"].annotations.idempotentHint is True

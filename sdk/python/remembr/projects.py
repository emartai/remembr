"""Explicit shared-space operations; separate space credentials are required."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from .client import RemembrClient


class ProjectMemoryAPI:
    def __init__(self, client: RemembrClient):
        self.client = client

    @staticmethod
    def path(space_id: str, memory_id: str | None = None) -> str:
        path = f"/projects/spaces/{UUID(space_id)}/memories"
        return path if memory_id is None else f"{path}/{UUID(memory_id)}"

    def store(self, space_id: str, content: str, *, idempotency_key: str, **options) -> dict:
        return self.client.request(
            "POST",
            self.path(space_id),
            json={
                "content": content,
                "idempotency_key": idempotency_key,
                **options,
            },
        )

    async def astore(self, space_id: str, content: str, *, idempotency_key: str, **options) -> dict:
        return await self.client.arequest(
            "POST",
            self.path(space_id),
            json={
                "content": content,
                "idempotency_key": idempotency_key,
                **options,
            },
        )

    def search(self, space_id: str, query: str = "", **options) -> dict:
        return self.client.request(
            "POST", f"/projects/spaces/{UUID(space_id)}/search", json={"query": query, **options}
        )

    async def asearch(self, space_id: str, query: str = "", **options) -> dict:
        return await self.client.arequest(
            "POST", f"/projects/spaces/{UUID(space_id)}/search", json={"query": query, **options}
        )

    def get(self, space_id: str, memory_id: str) -> dict:
        return self.client.request("GET", self.path(space_id, memory_id))

    async def aget(self, space_id: str, memory_id: str) -> dict:
        return await self.client.arequest("GET", self.path(space_id, memory_id))

    def status(self, space_id: str, memory_id: str) -> dict:
        return self.client.request("GET", self.path(space_id, memory_id) + "/status")

    async def astatus(self, space_id: str, memory_id: str) -> dict:
        return await self.client.arequest("GET", self.path(space_id, memory_id) + "/status")

    def delete(self, space_id: str, memory_id: str) -> dict[str, Any]:
        return self.client.request("DELETE", self.path(space_id, memory_id))

    async def adelete(self, space_id: str, memory_id: str) -> dict[str, Any]:
        return await self.client.arequest("DELETE", self.path(space_id, memory_id))

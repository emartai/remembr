"""Checkpoint and forgetting operations example."""

import asyncio

from remembr import RemembrClient


async def main() -> None:
    async with RemembrClient() as client:
        session = await client.create_session(metadata={"purpose": "checkpoint-demo"})
        _ = await client.store("First message", session_id=session.session_id)

        checkpoint = await client.checkpoint(session.session_id)
        print(f"Created checkpoint: {checkpoint.checkpoint_id}")

        restored = await client.restore(session.session_id, checkpoint.checkpoint_id)
        print(restored)

        checkpoints = await client.list_checkpoints(session.session_id)
        print(f"Checkpoints available: {len(checkpoints)}")


if __name__ == "__main__":
    asyncio.run(main())

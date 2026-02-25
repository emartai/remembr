"""Test the Remembr Python SDK"""
import asyncio
import sys
sys.path.insert(0, 'sdk/python')

from remembr import RemembrClient

async def main():
    print("=" * 80)
    print("REMEMBR PYTHON SDK TEST")
    print("=" * 80)
    
    # Initialize client with JWT token (not API key)
    # Note: The SDK uses Bearer token auth, not X-API-Key
    client = RemembrClient(
        api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwODY3ODhhYi0xNjc0LTRhODEtYjdkMi04MTcyNmFlYzUyNzUiLCJlbWFpbCI6Im53YW5ndW1hZW1tYW51ZWwyOUBnbWFpbC5jb20iLCJleHAiOjE3NzE5NzU0OTcsInR5cGUiOiJhY2Nlc3MifQ.k-BuPVa5oLwh_iyJr0i0pXyBtobFr6pOqrT426ypr7E",
        base_url="http://localhost:8000/api/v1"
    )
    
    # 1. Create a session
    print("\n1. Creating a session...")
    session = await client.create_session(
        metadata={"user": "Emmanuel", "purpose": "SDK Testing"}
    )
    print(f"✓ Session created: {session.session_id}")
    
    # 2. Add memories
    print("\n2. Adding memories...")
    memories = [
        "The Remembr Python SDK makes it easy to integrate memory into AI applications.",
        "You can store conversations, facts, and context for later retrieval.",
        "Semantic search allows finding relevant memories based on meaning, not just keywords."
    ]
    
    for i, content in enumerate(memories, 1):
        episode = await client.store(
            content=content,
            session_id=session.session_id,
            role="user"
        )
        print(f"  Memory {i} added: {episode.episode_id}")
    
    # 3. Search memories
    print("\n3. Searching memories...")
    results = await client.search(
        query="How does the SDK work?",
        session_id=session.session_id,
        limit=3
    )
    
    print(f"Found {len(results.results)} results:")
    for i, result in enumerate(results.results, 1):
        print(f"\n  Result {i} (score: {result.score:.3f}):")
        print(f"    {result.content[:80]}...")
    
    # 4. Get session history
    print("\n4. Getting session history...")
    episodes = await client.get_session_history(session.session_id, limit=10)
    print(f"Session: {session.session_id}")
    print(f"Episodes: {len(episodes)}")
    for ep in episodes[:3]:
        print(f"  - {ep.role}: {ep.content[:50]}...")
    
    # 5. List all sessions
    print("\n5. Listing all sessions...")
    sessions = await client.list_sessions(limit=5)
    print(f"Total sessions: {len(sessions)}")
    for sess in sessions[:3]:
        print(f"  - {sess.session_id}: {sess.metadata}")
    
    print("\n" + "=" * 80)
    print("✓ SDK TEST COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())

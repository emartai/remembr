"""Tests for Row-Level Security policies."""

import uuid

import pytest
from sqlalchemy import select, text

from app.db.rls import clear_org_context, get_org_context, set_org_context
from app.db.session import AsyncSessionLocal
from app.models import Episode, Embedding, MemoryFact, Organization, Session


@pytest.fixture
async def test_orgs():
    """Create test organizations."""
    async with AsyncSessionLocal() as db:
        # Create two test organizations
        org_a = Organization(name="Test Org A")
        org_b = Organization(name="Test Org B")
        
        db.add(org_a)
        db.add(org_b)
        await db.commit()
        await db.refresh(org_a)
        await db.refresh(org_b)
        
        yield org_a, org_b
        
        # Cleanup
        await db.delete(org_a)
        await db.delete(org_b)
        await db.commit()


@pytest.mark.asyncio
async def test_set_org_context():
    """Test setting organization context."""
    async with AsyncSessionLocal() as db:
        org_id = uuid.uuid4()
        
        # Set context
        await set_org_context(db, org_id)
        
        # Verify context is set
        current_org = await get_org_context(db)
        assert current_org == str(org_id)


@pytest.mark.asyncio
async def test_clear_org_context():
    """Test clearing organization context."""
    async with AsyncSessionLocal() as db:
        org_id = uuid.uuid4()
        
        # Set context
        await set_org_context(db, org_id)
        assert await get_org_context(db) == str(org_id)
        
        # Clear context
        await clear_org_context(db)
        
        # Verify context is cleared
        current_org = await get_org_context(db)
        assert current_org is None or current_org == ""


@pytest.mark.asyncio
async def test_rls_sessions_isolation(test_orgs):
    """Test RLS prevents cross-org access to sessions."""
    org_a, org_b = await test_orgs
    
    async with AsyncSessionLocal() as db:
        # Create session for org A
        await set_org_context(db, org_a.id)
        session_a = Session(
            org_id=org_a.id,
            metadata={"test": "org_a"},
        )
        db.add(session_a)
        await db.commit()
        await db.refresh(session_a)
        
        # Create session for org B
        await set_org_context(db, org_b.id)
        session_b = Session(
            org_id=org_b.id,
            metadata={"test": "org_b"},
        )
        db.add(session_b)
        await db.commit()
        await db.refresh(session_b)
    
    # Query as org A - should only see org A's session
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_a.id)
        
        result = await db.execute(select(Session))
        sessions = result.scalars().all()
        
        # Should only see org A's session
        assert len(sessions) == 1
        assert sessions[0].id == session_a.id
        assert sessions[0].org_id == org_a.id
    
    # Query as org B - should only see org B's session
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_b.id)
        
        result = await db.execute(select(Session))
        sessions = result.scalars().all()
        
        # Should only see org B's session
        assert len(sessions) == 1
        assert sessions[0].id == session_b.id
        assert sessions[0].org_id == org_b.id
    
    # Cleanup
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_a.id)
        await db.delete(session_a)
        await set_org_context(db, org_b.id)
        await db.delete(session_b)
        await db.commit()


@pytest.mark.asyncio
async def test_rls_episodes_isolation(test_orgs):
    """Test RLS prevents cross-org access to episodes."""
    org_a, org_b = await test_orgs
    
    async with AsyncSessionLocal() as db:
        # Create episode for org A
        await set_org_context(db, org_a.id)
        episode_a = Episode(
            org_id=org_a.id,
            role="user",
            content="Message from org A",
        )
        db.add(episode_a)
        await db.commit()
        await db.refresh(episode_a)
        
        # Create episode for org B
        await set_org_context(db, org_b.id)
        episode_b = Episode(
            org_id=org_b.id,
            role="user",
            content="Message from org B",
        )
        db.add(episode_b)
        await db.commit()
        await db.refresh(episode_b)
    
    # Query as org A
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_a.id)
        
        result = await db.execute(select(Episode))
        episodes = result.scalars().all()
        
        assert len(episodes) == 1
        assert episodes[0].id == episode_a.id
        assert episodes[0].content == "Message from org A"
    
    # Query as org B
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_b.id)
        
        result = await db.execute(select(Episode))
        episodes = result.scalars().all()
        
        assert len(episodes) == 1
        assert episodes[0].id == episode_b.id
        assert episodes[0].content == "Message from org B"
    
    # Cleanup
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_a.id)
        await db.delete(episode_a)
        await set_org_context(db, org_b.id)
        await db.delete(episode_b)
        await db.commit()


@pytest.mark.asyncio
async def test_rls_direct_sql_query(test_orgs):
    """Test that RLS works even with direct SQL queries."""
    org_a, org_b = await test_orgs
    
    async with AsyncSessionLocal() as db:
        # Create episodes for both orgs
        await set_org_context(db, org_a.id)
        episode_a = Episode(
            org_id=org_a.id,
            role="user",
            content="Direct SQL test A",
        )
        db.add(episode_a)
        await db.commit()
        
        await set_org_context(db, org_b.id)
        episode_b = Episode(
            org_id=org_b.id,
            role="user",
            content="Direct SQL test B",
        )
        db.add(episode_b)
        await db.commit()
    
    # Try direct SQL query as org A
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_a.id)
        
        # Even with SELECT *, RLS should filter
        result = await db.execute(
            text("SELECT * FROM episodes WHERE content LIKE '%Direct SQL test%'")
        )
        rows = result.fetchall()
        
        # Should only see org A's episode
        assert len(rows) == 1
        assert "Direct SQL test A" in str(rows[0])
    
    # Cleanup
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_a.id)
        await db.execute(text(f"DELETE FROM episodes WHERE id = '{episode_a.id}'"))
        await set_org_context(db, org_b.id)
        await db.execute(text(f"DELETE FROM episodes WHERE id = '{episode_b.id}'"))
        await db.commit()


@pytest.mark.asyncio
async def test_rls_insert_wrong_org(test_orgs):
    """Test that RLS prevents inserting data for wrong org."""
    org_a, org_b = await test_orgs
    
    async with AsyncSessionLocal() as db:
        # Set context to org A
        await set_org_context(db, org_a.id)
        
        # Try to insert episode for org B (should fail)
        episode = Episode(
            org_id=org_b.id,  # Wrong org!
            role="user",
            content="This should fail",
        )
        db.add(episode)
        
        # Should raise an error due to RLS WITH CHECK clause
        with pytest.raises(Exception):
            await db.commit()
        
        await db.rollback()


@pytest.mark.asyncio
async def test_rls_memory_facts_isolation(test_orgs):
    """Test RLS for memory_facts table."""
    org_a, org_b = await test_orgs
    
    async with AsyncSessionLocal() as db:
        # Create memory fact for org A
        await set_org_context(db, org_a.id)
        fact_a = MemoryFact(
            org_id=org_a.id,
            subject="User",
            predicate="likes",
            object="Python",
        )
        db.add(fact_a)
        await db.commit()
        await db.refresh(fact_a)
        
        # Create memory fact for org B
        await set_org_context(db, org_b.id)
        fact_b = MemoryFact(
            org_id=org_b.id,
            subject="User",
            predicate="likes",
            object="JavaScript",
        )
        db.add(fact_b)
        await db.commit()
        await db.refresh(fact_b)
    
    # Query as org A
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_a.id)
        
        result = await db.execute(select(MemoryFact))
        facts = result.scalars().all()
        
        assert len(facts) == 1
        assert facts[0].object == "Python"
    
    # Cleanup
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_a.id)
        await db.delete(fact_a)
        await set_org_context(db, org_b.id)
        await db.delete(fact_b)
        await db.commit()


@pytest.mark.asyncio
async def test_rls_embeddings_isolation(test_orgs):
    """Test RLS for embeddings table."""
    org_a, org_b = await test_orgs
    
    async with AsyncSessionLocal() as db:
        # Create embedding for org A
        await set_org_context(db, org_a.id)
        embedding_a = Embedding(
            org_id=org_a.id,
            content="Test content A",
            model="test-model",
            dimensions=3,
            vector=[0.1, 0.2, 0.3],
        )
        db.add(embedding_a)
        await db.commit()
        await db.refresh(embedding_a)
        
        # Create embedding for org B
        await set_org_context(db, org_b.id)
        embedding_b = Embedding(
            org_id=org_b.id,
            content="Test content B",
            model="test-model",
            dimensions=3,
            vector=[0.4, 0.5, 0.6],
        )
        db.add(embedding_b)
        await db.commit()
        await db.refresh(embedding_b)
    
    # Query as org A
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_a.id)
        
        result = await db.execute(select(Embedding))
        embeddings = result.scalars().all()
        
        assert len(embeddings) == 1
        assert embeddings[0].content == "Test content A"
    
    # Cleanup
    async with AsyncSessionLocal() as db:
        await set_org_context(db, org_a.id)
        await db.delete(embedding_a)
        await set_org_context(db, org_b.id)
        await db.delete(embedding_b)
        await db.commit()


@pytest.mark.asyncio
async def test_rls_without_context():
    """Test that queries without org context return no results."""
    async with AsyncSessionLocal() as db:
        # Don't set org context
        
        # Query should return empty results due to RLS
        result = await db.execute(select(Episode))
        episodes = result.scalars().all()
        
        # Should be empty because no org context is set
        assert len(episodes) == 0

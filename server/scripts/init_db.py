#!/usr/bin/env python3
"""
Initialize database with sample data for development.

Usage:
    python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal
from app.models import Organization


async def init_db():
    """Initialize database with sample data."""
    async with AsyncSessionLocal() as db:
        try:
            # Create sample organization
            org = Organization(name="Demo Organization")
            db.add(org)
            await db.commit()
            
            print(f"✓ Created organization: {org.name} (ID: {org.id})")
            print("\nDatabase initialized successfully!")
            
        except Exception as e:
            print(f"✗ Error initializing database: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(init_db())

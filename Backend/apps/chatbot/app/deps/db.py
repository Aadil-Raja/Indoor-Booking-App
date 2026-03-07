"""
Database dependencies for chatbot app.

This module provides database session dependencies for dependency injection
in FastAPI routes. It imports the async database engine and session factory
from core.database and exports the get_async_db dependency.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from app.core.database import get_async_db, async_engine

# Re-export for use in routers
__all__ = ["get_async_db", "async_engine"]

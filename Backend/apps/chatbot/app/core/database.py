"""
Async database configuration and session management.

This module provides async database engine, session factory, and dependency
injection for database sessions. It configures connection pooling for
efficient async operations.
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker
)
from typing import AsyncGenerator
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create async engine with connection pooling
# Note: For async engines, SQLAlchemy automatically uses AsyncAdaptedQueuePool
async_engine = create_async_engine(
    settings.CHAT_DATABASE_URL,
    echo=settings.LOG_LEVEL == "DEBUG",
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,  # Verify connections before using
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions.
    
    Yields:
        AsyncSession: Database session for async operations
        
    Example:
        @app.get("/chats")
        async def get_chats(db: AsyncSession = Depends(get_async_db)):
            # Use db session here
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize database connection.
    
    This function can be called on application startup to verify
    database connectivity.
    """
    try:
        async with async_engine.begin() as conn:
            logger.info("Database connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def close_db():
    """
    Close database connections.
    
    This function should be called on application shutdown to
    properly close all database connections.
    """
    await async_engine.dispose()
    logger.info("Database connections closed")

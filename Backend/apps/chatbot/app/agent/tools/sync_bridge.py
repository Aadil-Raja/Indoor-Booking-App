"""
Sync-to-async bridge utility for calling sync services from async code.

This module provides utilities to safely call synchronous database operations
from async code using a thread pool executor. This is necessary because the
chatbot uses an async database but needs to integrate with existing sync
services (property, court, booking, etc.).

The bridge ensures proper session management and thread safety when calling
sync services from the async agent code.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Callable, TypeVar, Any
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

# Type variable for generic function return types
T = TypeVar('T')

# Create sync engine for main database
# This is separate from the async engine used for chat data
sync_engine = create_engine(
    settings.MAIN_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
)

# Create sync session factory
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autoflush=False,
    autocommit=False,
)

# Thread pool executor for running sync operations
# Using a limited pool size to prevent resource exhaustion
_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="sync_bridge")


def get_sync_db() -> Session:
    """
    Get a sync database session for main database operations.
    
    Returns:
        Session: Sync database session
        
    Note:
        Caller is responsible for closing the session.
    """
    return SyncSessionLocal()


async def run_sync_in_executor(
    func: Callable[..., T],
    *args: Any,
    **kwargs: Any
) -> T:
    """
    Execute a synchronous function in a thread pool executor.
    
    This function wraps sync service calls to make them safely callable
    from async code. It handles:
    - Thread pool execution
    - Session management for database operations
    - Error handling and logging
    - Proper cleanup
    
    Args:
        func: Synchronous function to execute
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func
        
    Returns:
        T: Return value from the sync function
        
    Raises:
        Exception: Any exception raised by the sync function
        
    Example:
        # Call a sync service from async code
        result = await run_sync_in_executor(
            property_service.get_owner_properties,
            db=db,
            owner_id=owner_id
        )
        
    Note:
        If the function requires a database session, pass it via kwargs
        using the 'db' parameter. The session will be properly managed.
    """
    loop = asyncio.get_event_loop()
    
    # Check if a database session is needed
    needs_db = 'db' in kwargs and kwargs['db'] is None
    db_session = None
    
    try:
        # Create a new sync session if needed
        if needs_db:
            db_session = get_sync_db()
            kwargs['db'] = db_session
            logger.debug(f"Created sync DB session for {func.__name__}")
        
        # Execute the sync function in thread pool
        logger.debug(f"Executing sync function {func.__name__} in thread pool")
        result = await loop.run_in_executor(_executor, lambda: func(*args, **kwargs))
        
        # Commit if we created the session
        if db_session:
            db_session.commit()
            logger.debug(f"Committed sync DB session for {func.__name__}")
        
        return result
        
    except Exception as e:
        # Rollback on error if we created the session
        if db_session:
            db_session.rollback()
            logger.error(f"Rolled back sync DB session for {func.__name__}: {e}")
        
        logger.error(f"Error executing sync function {func.__name__}: {e}")
        raise
        
    finally:
        # Clean up session if we created it
        if db_session:
            db_session.close()
            logger.debug(f"Closed sync DB session for {func.__name__}")


def sync_to_async(func: Callable[..., T]) -> Callable[..., asyncio.Future[T]]:
    """
    Decorator to convert a sync function to async using the executor.
    
    This decorator wraps a synchronous function to make it callable with
    await. It automatically handles thread pool execution and session
    management.
    
    Args:
        func: Synchronous function to wrap
        
    Returns:
        Async wrapper function
        
    Example:
        @sync_to_async
        def get_properties(db: Session, owner_id: int):
            return property_service.get_owner_properties(db, owner_id=owner_id)
        
        # Now callable as async
        result = await get_properties(db=None, owner_id=123)
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        return await run_sync_in_executor(func, *args, **kwargs)
    
    return wrapper


async def call_sync_service(
    service_func: Callable[..., T],
    *args: Any,
    **kwargs: Any
) -> T:
    """
    Convenience function to call a sync service function from async code.
    
    This is a higher-level wrapper around run_sync_in_executor that
    automatically manages database sessions for service calls.
    
    Args:
        service_func: Service function to call (e.g., property_service.get_owner_properties)
        *args: Positional arguments for the service function
        **kwargs: Keyword arguments for the service function
        
    Returns:
        T: Return value from the service function
        
    Example:
        from Backend.apps.management.app.services import property_service
        
        result = await call_sync_service(
            property_service.get_owner_properties,
            db=None,  # Will be auto-created
            owner_id=owner_id
        )
    """
    # Ensure db parameter is present for service calls
    if 'db' not in kwargs:
        kwargs['db'] = None
    
    return await run_sync_in_executor(service_func, *args, **kwargs)


def shutdown_executor():
    """
    Shutdown the thread pool executor.
    
    This should be called on application shutdown to properly
    clean up executor resources.
    """
    logger.info("Shutting down sync bridge executor")
    _executor.shutdown(wait=True)
    logger.info("Sync bridge executor shut down successfully")


# Context manager for manual session management
class SyncDBContext:
    """
    Context manager for manual sync database session management.
    
    Use this when you need more control over the session lifecycle,
    such as when making multiple service calls in a transaction.
    
    Example:
        async with SyncDBContext() as db:
            result1 = await run_sync_in_executor(
                property_service.get_property_details,
                db=db,
                property_id=prop_id,
                owner_id=owner_id
            )
            result2 = await run_sync_in_executor(
                court_service.get_courts_by_property,
                db=db,
                property_id=prop_id
            )
    """
    
    def __init__(self):
        self.db: Session = None
    
    async def __aenter__(self) -> Session:
        """Create and return a sync database session."""
        self.db = get_sync_db()
        logger.debug("Created sync DB session in context manager")
        return self.db
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close the database session."""
        if self.db:
            if exc_type:
                self.db.rollback()
                logger.error(f"Rolled back sync DB session due to error: {exc_val}")
            else:
                self.db.commit()
                logger.debug("Committed sync DB session in context manager")
            
            self.db.close()
            logger.debug("Closed sync DB session in context manager")
        
        # Don't suppress exceptions
        return False

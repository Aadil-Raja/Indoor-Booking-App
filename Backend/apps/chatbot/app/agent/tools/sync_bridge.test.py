"""
Unit tests for sync-to-async bridge utility.

Tests the sync bridge functionality including:
- Basic sync function execution in thread pool
- Database session management
- Error handling and rollback
- Decorator usage
- Context manager usage
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from .sync_bridge import (
    run_sync_in_executor,
    sync_to_async,
    call_sync_service,
    get_sync_db,
    SyncDBContext,
)


class TestSyncBridge:
    """Test suite for sync-to-async bridge utility."""
    
    @pytest.mark.asyncio
    async def test_run_sync_in_executor_basic(self):
        """Test basic sync function execution without database."""
        
        def sync_function(x: int, y: int) -> int:
            return x + y
        
        result = await run_sync_in_executor(sync_function, 5, 10)
        assert result == 15
    
    @pytest.mark.asyncio
    async def test_run_sync_in_executor_with_kwargs(self):
        """Test sync function execution with keyword arguments."""
        
        def sync_function(x: int, y: int, multiplier: int = 1) -> int:
            return (x + y) * multiplier
        
        result = await run_sync_in_executor(sync_function, 5, 10, multiplier=2)
        assert result == 30
    
    @pytest.mark.asyncio
    async def test_run_sync_in_executor_with_mock_db(self):
        """Test sync function execution with database session management."""
        
        mock_db = MagicMock(spec=Session)
        
        def sync_function(db: Session, value: int) -> int:
            # Simulate database operation
            return value * 2
        
        with patch('app.agent.tools.sync_bridge.get_sync_db', return_value=mock_db):
            result = await run_sync_in_executor(sync_function, db=None, value=5)
            assert result == 10
            mock_db.commit.assert_called_once()
            mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_sync_in_executor_error_handling(self):
        """Test error handling and rollback on exception."""
        
        mock_db = MagicMock(spec=Session)
        
        def sync_function(db: Session) -> None:
            raise ValueError("Test error")
        
        with patch('app.agent.tools.sync_bridge.get_sync_db', return_value=mock_db):
            with pytest.raises(ValueError, match="Test error"):
                await run_sync_in_executor(sync_function, db=None)
            
            mock_db.rollback.assert_called_once()
            mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sync_to_async_decorator(self):
        """Test sync_to_async decorator."""
        
        @sync_to_async
        def sync_function(x: int, y: int) -> int:
            return x * y
        
        result = await sync_function(6, 7)
        assert result == 42
    
    @pytest.mark.asyncio
    async def test_call_sync_service(self):
        """Test call_sync_service convenience function."""
        
        mock_db = MagicMock(spec=Session)
        
        def mock_service_func(db: Session, user_id: int) -> dict:
            return {"user_id": user_id, "data": "test"}
        
        with patch('app.agent.tools.sync_bridge.get_sync_db', return_value=mock_db):
            result = await call_sync_service(mock_service_func, user_id=123)
            assert result == {"user_id": 123, "data": "test"}
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_sync_db_context_manager_success(self):
        """Test SyncDBContext context manager with successful operation."""
        
        mock_db = MagicMock(spec=Session)
        
        with patch('app.agent.tools.sync_bridge.get_sync_db', return_value=mock_db):
            async with SyncDBContext() as db:
                assert db == mock_db
            
            mock_db.commit.assert_called_once()
            mock_db.close.assert_called_once()
            mock_db.rollback.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_sync_db_context_manager_error(self):
        """Test SyncDBContext context manager with error."""
        
        mock_db = MagicMock(spec=Session)
        
        with patch('app.agent.tools.sync_bridge.get_sync_db', return_value=mock_db):
            with pytest.raises(ValueError):
                async with SyncDBContext() as db:
                    raise ValueError("Test error")
            
            mock_db.rollback.assert_called_once()
            mock_db.close.assert_called_once()
            mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_concurrent_execution(self):
        """Test multiple concurrent sync function executions."""
        
        def sync_function(value: int) -> int:
            import time
            time.sleep(0.1)  # Simulate some work
            return value * 2
        
        # Execute multiple functions concurrently
        tasks = [
            run_sync_in_executor(sync_function, i)
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        assert results == [0, 2, 4, 6, 8]
    
    def test_get_sync_db(self):
        """Test get_sync_db returns a valid session."""
        
        with patch('app.agent.tools.sync_bridge.SyncSessionLocal') as mock_session_local:
            mock_session = MagicMock(spec=Session)
            mock_session_local.return_value = mock_session
            
            db = get_sync_db()
            assert db == mock_session
            mock_session_local.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Pytest configuration and fixtures for chatbot tests.

This module provides common fixtures and configuration for all chatbot tests.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add Backend path for imports
backend_path = Path(__file__).parent.parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


@pytest.fixture(scope="session", autouse=True)
def mock_settings():
    """Mock settings to avoid requiring environment variables during tests."""
    mock_settings_obj = MagicMock()
    mock_settings_obj.CHAT_DATABASE_URL = "postgresql+asyncpg://test:test@localhost/test_chat"
    mock_settings_obj.MAIN_DATABASE_URL = "postgresql://test:test@localhost/test_main"
    mock_settings_obj.JWT_SECRET = "test_secret_key_for_testing"
    mock_settings_obj.JWT_ALGORITHM = "HS256"
    mock_settings_obj.ACCESS_TOKEN_EXPIRE_MINUTES = 30
    mock_settings_obj.OPENAI_API_KEY = "test_openai_key"
    mock_settings_obj.OPENAI_MODEL = "gpt-4"
    mock_settings_obj.DB_POOL_SIZE = 5
    mock_settings_obj.DB_MAX_OVERFLOW = 10
    
    with patch('apps.chatbot.app.core.config.Settings', return_value=mock_settings_obj):
        with patch('apps.chatbot.app.core.config.settings', mock_settings_obj):
            yield mock_settings_obj


@pytest.fixture(scope="session", autouse=True)
def mock_sync_engine():
    """Mock the sync database engine to avoid database connections during tests."""
    mock_engine = MagicMock()
    
    with patch('apps.chatbot.app.agent.tools.sync_bridge.create_engine', return_value=mock_engine):
        with patch('apps.chatbot.app.agent.tools.sync_bridge.sessionmaker'):
            yield mock_engine


@pytest.fixture
def mock_db_session():
    """Provide a mock database session for tests."""
    session = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session

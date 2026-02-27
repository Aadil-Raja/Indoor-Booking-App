"""
Pytest configuration for chatbot tests.

This module provides fixtures and configuration for running chatbot tests,
including mocking environment variables and settings.
"""

import os
import sys
from pathlib import Path

# Add Backend directory to Python path for shared module imports
backend_path = Path(__file__).parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Set required environment variables for testing
os.environ.setdefault("CHAT_DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test_chat")
os.environ.setdefault("MAIN_DATABASE_URL", "postgresql://test:test@localhost/test_main")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-for-testing")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("OPENAI_MODEL", "gpt-4o-mini")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("SESSION_EXPIRY_HOURS", "24")
os.environ.setdefault("LOG_LEVEL", "INFO")

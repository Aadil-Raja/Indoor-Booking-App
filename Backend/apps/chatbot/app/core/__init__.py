"""
Core module for chatbot application.

This module contains configuration, database setup, and other core utilities.
"""

from .config import settings, Settings
from .database import (
    async_engine,
    AsyncSessionLocal,
    get_async_db,
    init_db,
    close_db,
)

__all__ = [
    "settings",
    "Settings",
    "async_engine",
    "AsyncSessionLocal",
    "get_async_db",
    "init_db",
    "close_db",
]

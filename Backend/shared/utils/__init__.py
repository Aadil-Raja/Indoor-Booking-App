# shared/utils/__init__.py
"""Shared utilities used across multiple apps."""
from typing import Optional


class OwnerContext:
    """Context object for authenticated owner"""
    def __init__(self, user_id: Optional[int] = None, owner_profile_id: Optional[int] = None):
        self.user_id = user_id
        self.owner_profile_id = owner_profile_id

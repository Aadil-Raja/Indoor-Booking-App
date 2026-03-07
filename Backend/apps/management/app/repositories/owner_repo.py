# This file is kept for backward compatibility
# All functionality has been moved to Backend/shared/repositories/owner_repo.py
from shared.repositories.owner_repo import (
    create,
    get_by_user_id,
    get_by_id,
    update,
    delete
)

__all__ = [
    'create',
    'get_by_user_id',
    'get_by_id',
    'update',
    'delete'
]

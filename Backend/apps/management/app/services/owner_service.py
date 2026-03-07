# This file is kept for backward compatibility
# All functionality has been moved to Backend/shared/services/owner_service.py
from shared.services.owner_service import (
    create_or_update_profile,
    get_profile,
    get_dashboard_stats
)

__all__ = [
    'create_or_update_profile',
    'get_profile',
    'get_dashboard_stats'
]

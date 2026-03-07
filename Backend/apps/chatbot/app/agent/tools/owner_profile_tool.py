"""
Owner profile tool for the chatbot agent.

This module provides a tool for retrieving owner profile information
by integrating with the shared owner_service through the sync bridge.
"""

import logging
from typing import Dict, Any, Optional

from app.agent.tools.sync_bridge import call_sync_service
from shared.utils import OwnerContext

logger = logging.getLogger(__name__)


async def get_owner_profile_tool(owner_profile_id: int) -> Optional[Dict[str, Any]]:
    """
    Get owner profile information by profile ID.
    
    This tool retrieves owner profile details including business_name, phone,
    address, and verification status.
    
    Args:
        owner_profile_id: Owner profile ID
        
    Returns:
        Owner profile dictionary with business_name, phone, address, verified
        Returns dict with default business_name if not found
        
    Example:
        profile = await get_owner_profile_tool(owner_profile_id=123)
        # Returns: {"id": 123, "business_name": "ABC Sports", ...}
    """
    try:
        logger.info(f"Getting owner profile for owner_profile_id={owner_profile_id}")
        
        # Import shared repository
        from shared.repositories import owner_repo
        from sqlalchemy.orm import Session
        
        # Define sync function to fetch profile
        def get_profile_sync(db: Session, profile_id: int) -> dict:
            """Sync function to fetch owner profile"""
            profile = owner_repo.get_by_id(db, profile_id)
            if profile:
                return {
                    "id": profile.id,
                    "business_name": profile.business_name or "our facility",
                    "phone": profile.phone,
                    "address": profile.address,
                    "verified": profile.verified
                }
            return {"business_name": "our facility"}  # Default if not found
        
        # Call sync service using the bridge
        profile_data = await call_sync_service(
            get_profile_sync,
            db=None,  # Auto-managed by sync bridge
            profile_id=owner_profile_id
        )
        
        logger.info(f"Retrieved owner profile for owner_profile_id={owner_profile_id}")
        return profile_data
        
    except Exception as e:
        logger.error(f"Error getting owner profile: {e}", exc_info=True)
        return {"business_name": "our facility"}  # Fallback on error


# Tool registry for easy access
OWNER_PROFILE_TOOLS = {
    "get_owner_profile": get_owner_profile_tool,
}

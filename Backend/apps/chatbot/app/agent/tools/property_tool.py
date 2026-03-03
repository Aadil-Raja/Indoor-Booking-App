"""
Property search and details tools for the chatbot agent.

This module provides tools for searching properties and retrieving property details
by integrating with the sync property_service through the sync bridge.

Note: Properties are linked to OwnerProfile in the main database.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.agent.tools.sync_bridge import call_sync_service
from shared.services import property_service

logger = logging.getLogger(__name__)


def _get_management_services():
    """
    Dynamically import management services to avoid import conflicts.
    
    This function imports the management app services at runtime to prevent
    conflicts with the chatbot's app.services module.
    """
    import sys
    from pathlib import Path
    
    # Add Backend path for shared modules
    backend_path = Path(__file__).parent.parent.parent.parent.parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    # Add management app path at the beginning to prioritize it
    management_path = backend_path / "apps" / "management"
    if str(management_path) not in sys.path:
        sys.path.insert(0, str(management_path))
    
    # Import services from management app
    # We need to temporarily remove chatbot path to avoid conflicts
    chatbot_path = str(Path(__file__).parent.parent.parent.parent.parent)
    original_path = sys.path.copy()
    
    try:
        # Remove chatbot path temporarily
        if chatbot_path in sys.path:
            sys.path.remove(chatbot_path)
        
        # Import from management app
        from app.services import property_service, public_service
        return property_service, public_service
    finally:
        # Restore original path
        sys.path = original_path

logger = logging.getLogger(__name__)


async def search_properties_tool(
    owner_id: str,
    city: Optional[str] = None,
    sport_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for properties with optional filters.
    
    This tool searches for active properties, optionally filtering by city,
    sport type, and price range. It uses the public_service.search_properties
    for comprehensive search capabilities.
    
    Args:
        owner_id: Owner ID to filter properties (optional for public search)
        city: City name to filter by (optional)
        sport_type: Sport type to filter courts by (optional)
        min_price: Minimum price per hour (optional)
        max_price: Maximum price per hour (optional)
        limit: Maximum number of results to return (default: 10)
        
    Returns:
        List of property dictionaries with basic information
        
    Example:
        properties = await search_properties_tool(
            owner_id="123e4567-e89b-12d3-a456-426614174000",
            sport_type="tennis",
            city="New York"
        )
    """
    try:
        logger.info(
            f"Searching properties: city={city}, sport_type={sport_type}, "
            f"min_price={min_price}, max_price={max_price}, limit={limit}"
        )
        
        # Get management services
        property_service, public_service = _get_management_services()
        
        # Call sync service using the bridge
        result = await call_sync_service(
            public_service.search_properties,
            db=None,  # Auto-managed by sync bridge
            city=city,
            sport_type=sport_type,
            min_price=min_price,
            max_price=max_price,
            page=1,
            limit=limit
        )
        
        # Extract data from response
        if result.get('success'):
            properties = result.get('data', {}).get('items', [])
            logger.info(f"Found {len(properties)} properties")
            return properties
        else:
            logger.warning(f"Property search failed: {result.get('message')}")
            return []
            
    except Exception as e:
        logger.error(f"Error searching properties: {e}", exc_info=True)
        return []


async def get_property_details_tool(
    property_id: int,
    owner_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific property.
    
    This tool retrieves comprehensive property details including courts,
    amenities, and media. If owner_id is provided, it uses the owner-specific
    service which includes additional ownership information.
    
    Args:
        property_id: ID of the property to retrieve
        owner_id: Owner ID for ownership verification (optional)
        
    Returns:
        Property details dictionary or None if not found
        
    Example:
        details = await get_property_details_tool(
            property_id=123,
            owner_id="123e4567-e89b-12d3-a456-426614174000"
        )
    """
    try:
        logger.info(f"Getting property details: property_id={property_id}, owner_id={owner_id}")
        
        # Get management services
        property_service, public_service = _get_management_services()
        
        if owner_id:
            # Use owner-specific service for detailed access
            result = await call_sync_service(
                property_service.get_property_details,
                db=None,
                property_id=property_id,
                owner_id=int(owner_id) if isinstance(owner_id, str) else owner_id
            )
        else:
            # Use public service for general access
            result = await call_sync_service(
                public_service.get_property_details,
                db=None,
                property_id=property_id
            )
        
        # Extract data from response
        if result.get('success'):
            property_data = result.get('data')
            logger.info(f"Retrieved property details for property_id={property_id}")
            return property_data
        else:
            logger.warning(
                f"Failed to get property details: {result.get('message')} "
                f"(property_id={property_id})"
            )
            return None
            
    except Exception as e:
        logger.error(f"Error getting property details: {e}", exc_info=True)
        return None


async def get_owner_properties_tool(owner_id: str) -> List[Dict[str, Any]]:
    """
    Get all properties owned by a specific owner.
    
    This tool retrieves all properties associated with an owner profile.
    Note: Properties are linked to OwnerProfile, not directly to User.
    
    Args:
        owner_id: Owner ID (from OwnerProfile)
        
    Returns:
        List of property dictionaries owned by the specified owner
        
    Example:
        properties = await get_owner_properties_tool(
            owner_id="123e4567-e89b-12d3-a456-426614174000"
        )
    """
    try:
        logger.info(f"Getting properties for owner_id={owner_id}")
        
        # Get management services
        property_service, public_service = _get_management_services()
        
        # Convert UUID string to int if needed
        owner_id_int = int(owner_id) if isinstance(owner_id, str) and owner_id.isdigit() else owner_id
        
        # Call sync service using the bridge
        result = await call_sync_service(
            property_service.get_owner_properties,
            db=None,
            owner_id=owner_id_int
        )
        
        # Extract data from response
        if result.get('success'):
            properties = result.get('data', [])
            logger.info(f"Found {len(properties)} properties for owner_id={owner_id}")
            return properties
        else:
            logger.warning(f"Failed to get owner properties: {result.get('message')}")
            return []
            
    except Exception as e:
        logger.error(f"Error getting owner properties: {e}", exc_info=True)
        return []


# Tool registry for easy access
PROPERTY_TOOLS = {
    "search_properties": search_properties_tool,
    "get_property_details": get_property_details_tool,
    "get_owner_properties": get_owner_properties_tool,
}

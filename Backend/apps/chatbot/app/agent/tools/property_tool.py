"""
Property search and details tools for the chatbot agent.

This module provides tools for searching properties and retrieving property details
by integrating with the sync property_service through the sync bridge.

Note: Properties are linked to OwnerProfile in the main database.
Services expect OwnerContext with owner_profile_id.
"""

import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.agent.tools.sync_bridge import call_sync_service
from shared.utils import OwnerContext

logger = logging.getLogger(__name__)


logger = logging.getLogger(__name__)


async def search_properties_tool(
    owner_profile_id: int,
    city: Optional[str] = None,
    sport_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for properties with optional filters.
    
    This tool searches for active properties owned by the specified owner_profile_id,
    optionally filtering by city, sport type, and price range.
    
    Args:
        owner_profile_id: Owner profile ID to filter properties
        city: City name to filter by (optional)
        sport_type: Sport type to filter courts by (optional)
        min_price: Minimum price per hour (optional)
        max_price: Maximum price per hour (optional)
        limit: Maximum number of results to return (default: 10)
        
    Returns:
        List of property dictionaries with basic information
        
    Example:
        properties = await search_properties_tool(
            owner_profile_id=123,
            sport_type="tennis",
            city="New York"
        )
    """
    try:
        logger.info(
            f"Searching properties for owner_profile_id={owner_profile_id}: "
            f"city={city}, sport_type={sport_type}, "
            f"min_price={min_price}, max_price={max_price}, limit={limit}"
        )
        
        # Import services
        from shared.services import property_service
        
        # Create OwnerContext for service call
        owner_context = OwnerContext(
            user_id=None,  # Not needed for property search
            owner_profile_id=owner_profile_id
        )
        
        # Call sync service using the bridge
        result = await call_sync_service(
            property_service.get_owner_properties,
            db=None,  # Auto-managed by sync bridge
            current_owner=owner_context
        )
        
        # Result is now a dict (auto-extracted from JSONResponse by sync_bridge)
        if result.get('success'):
            properties = result.get('data', [])
            logger.info(f"Found {len(properties)} properties for owner_profile_id={owner_profile_id}")
            return properties
        else:
            logger.warning(f"Property search failed: {result.get('message')}")
            return []
            
    except Exception as e:
        logger.error(f"Error searching properties: {e}", exc_info=True)
        return []


async def get_property_details_tool(
    property_id: int,
    owner_profile_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific property.
    
    This tool retrieves comprehensive property details including courts,
    amenities, and media.
    
    Args:
        property_id: ID of the property to retrieve
        owner_profile_id: Owner profile ID for ownership verification
        
    Returns:
        Property details dictionary or None if not found
        
    Example:
        details = await get_property_details_tool(
            property_id=123,
            owner_profile_id=456
        )
    """
    try:
        logger.info(f"Getting property details: property_id={property_id}, owner_profile_id={owner_profile_id}")
        
        # Import services
        from shared.services import property_service
        
        # Create OwnerContext for service call
        owner_context = OwnerContext(
            user_id=None,
            owner_profile_id=owner_profile_id
        )
        
        # Call sync service using the bridge
        result = await call_sync_service(
            property_service.get_property_details,
            db=None,
            property_id=property_id,
            current_owner=owner_context
        )
        
        # Result is now a dict (auto-extracted from JSONResponse by sync_bridge)
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


async def get_owner_properties_tool(owner_profile_id: int) -> List[Dict[str, Any]]:
    """
    Get all properties owned by a specific owner.
    
    This tool retrieves all properties associated with an owner profile.
    
    Args:
        owner_profile_id: Owner profile ID
        
    Returns:
        List of property dictionaries owned by the specified owner
        
    Example:
        properties = await get_owner_properties_tool(owner_profile_id=123)
    """
    try:
        logger.info(f"Getting properties for owner_profile_id={owner_profile_id}")
        
        # Import services
        from shared.services import property_service
        
        # Create OwnerContext for service call
        owner_context = OwnerContext(
            user_id=None,
            owner_profile_id=owner_profile_id
        )
        
        # Call sync service using the bridge
        result = await call_sync_service(
            property_service.get_owner_properties,
            db=None,
            current_owner=owner_context
        )
        
        # Result is now a dict (auto-extracted from JSONResponse by sync_bridge)
        if result.get('success'):
            properties = result.get('data', [])
            logger.info(f"Found {len(properties)} properties for owner_profile_id={owner_profile_id}")
            return properties
        else:
            logger.warning(f"Failed to get owner properties: {result.get('message')}")
            return []
            
    except Exception as e:
        logger.error(f"Error getting owner properties: {e}", exc_info=True)
        return []


async def get_property_details_public_tool(property_id: int) -> Optional[Dict[str, Any]]:
    """
    Get full property details including courts using public service.
    
    This tool uses public_service.get_property_details which doesn't require
    owner authentication. Returns property details with courts and media.
    
    Args:
        property_id: ID of the property to retrieve
        
    Returns:
        Property details dictionary with courts, or None if not found
        
    Example:
        details = await get_property_details_public_tool(property_id=123)
        # Returns: {"id": 123, "name": "...", "courts": [...], ...}
    """
    try:
        logger.info(f"Getting public property details: property_id={property_id}")
        
        # Import public service
        from shared.services import public_service
        
        # Call sync service using the bridge
        result = await call_sync_service(
            public_service.get_property_details,
            db=None,  # Auto-managed by sync bridge
            property_id=property_id
        )
        
        # Result is now a dict (auto-extracted from JSONResponse by sync_bridge)
        if result.get('success'):
            property_details = result.get('data')
            logger.info(f"Retrieved public property details for property_id={property_id}")
            return property_details
        else:
            logger.warning(
                f"Failed to get public property details: {result.get('message')} "
                f"(property_id={property_id})"
            )
            return None
            
    except Exception as e:
        logger.error(f"Error getting public property details: {e}", exc_info=True)
        return None


# Tool registry for easy access
PROPERTY_TOOLS = {
    "search_properties": search_properties_tool,
    "get_property_details": get_property_details_tool,
    "get_owner_properties": get_owner_properties_tool,
    "get_property_details_public": get_property_details_public_tool,
}

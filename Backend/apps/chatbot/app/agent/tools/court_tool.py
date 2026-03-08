"""
Court search and details tools for the chatbot agent.

This module provides tools for searching courts by sport type and retrieving
court details by integrating with the sync court_service and public_service
through the sync bridge.
"""

import logging
from typing import List, Dict, Any, Optional

from app.agent.tools.sync_bridge import call_sync_service
from shared.services import court_service

logger = logging.getLogger(__name__)


def _get_court_service():
    """
    Import court_service from shared.
    """
    import sys
    from pathlib import Path
    
    # Add Backend path for shared modules
    backend_path = Path(__file__).parent.parent.parent.parent.parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    # Import court_service from shared
    try:
        from shared.services import court_service
        return court_service
    except ImportError as e:
        logger.error(f"Failed to import court_service from shared: {e}")
        raise


async def search_courts_tool(
    sport_type: Optional[str] = None,
    city: Optional[str] = None,
    property_id: Optional[int] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search for courts by sport type and other filters.
    
    This tool searches for active courts, optionally filtering by sport type,
    city, or specific property. It uses the public_service.search_properties
    with sport_type filter to find properties with matching courts, then
    extracts court information.
    
    Args:
        sport_type: Sport type to filter by (e.g., "tennis", "basketball")
        city: City name to filter properties by (optional)
        property_id: Specific property ID to get courts from (optional)
        limit: Maximum number of results to return (default: 20)
        
    Returns:
        List of court dictionaries with basic information
        
    Example:
        courts = await search_courts_tool(
            sport_type="tennis",
            city="New York"
        )
    """
    try:
        logger.info(
            f"Searching courts: sport_type={sport_type}, city={city}, "
            f"property_id={property_id}, limit={limit}"
        )
        
        # Get court service from shared
        court_service = _get_court_service()
        
        # If property_id is specified, get courts for that property
        if property_id:
            result = await call_sync_service(
                public_service.get_property_details,
                db=None,
                property_id=property_id
            )
            
            if result.get('success'):
                property_data = result.get('data', {})
                courts = property_data.get('courts', [])
                
                # Filter by sport_type if specified
                if sport_type:
                    courts = [
                        c for c in courts 
                        if c.get('sport_type', '').lower() == sport_type.lower()
                    ]
                
                logger.info(f"Found {len(courts)} courts for property_id={property_id}")
                return courts[:limit]
            else:
                logger.warning(f"Failed to get property details: {result.get('message')}")
                return []
        
        # Otherwise, search properties by sport_type and extract courts
        result = await call_sync_service(
            public_service.search_properties,
            db=None,
            city=city,
            sport_type=sport_type,
            page=1,
            limit=limit
        )
        
        if not result.get('success'):
            logger.warning(f"Property search failed: {result.get('message')}")
            return []
        
        # Get property IDs from search results
        properties = result.get('data', {}).get('items', [])
        
        if not properties:
            logger.info("No properties found matching search criteria")
            return []
        
        # Get detailed information for each property to extract courts
        courts = []
        for prop in properties:
            prop_result = await call_sync_service(
                public_service.get_property_details,
                db=None,
                property_id=prop['id']
            )
            
            if prop_result.get('success'):
                prop_data = prop_result.get('data', {})
                prop_courts = prop_data.get('courts', [])
                
                # Filter by sport_type if specified
                if sport_type:
                    prop_courts = [
                        c for c in prop_courts 
                        if c.get('sport_type', '').lower() == sport_type.lower()
                    ]
                
                # Add property context to each court
                for court in prop_courts:
                    court['property_name'] = prop_data.get('name')
                    court['property_city'] = prop_data.get('city')
                    court['property_address'] = prop_data.get('address')
                
                courts.extend(prop_courts)
                
                # Stop if we've reached the limit
                if len(courts) >= limit:
                    break
        
        logger.info(f"Found {len(courts)} courts matching criteria")
        return courts[:limit]
        
    except Exception as e:
        logger.error(f"Error searching courts: {e}", exc_info=True)
        return []


async def get_court_details_tool(court_id: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific court.
    
    This tool retrieves comprehensive court details including property
    information, pricing rules, and media. It uses the public_service
    for general access.
    
    Args:
        court_id: ID of the court to retrieve
        
    Returns:
        Court details dictionary or None if not found
        
    Example:
        details = await get_court_details_tool(court_id=123)
    """
    try:
        logger.info(f"Getting court details: court_id={court_id}")
        
        # Get court service from shared
        court_service = _get_court_service()
        
        # Call sync service using the bridge
        result = await call_sync_service(
            public_service.get_court_details,
            db=None,
            court_id=court_id
        )
        
        # Extract data from response
        if result.get('success'):
            court_data = result.get('data')
            logger.info(f"Retrieved court details for court_id={court_id}")
            return court_data
        else:
            logger.warning(
                f"Failed to get court details: {result.get('message')} "
                f"(court_id={court_id})"
            )
            return None
            
    except Exception as e:
        logger.error(f"Error getting court details: {e}", exc_info=True)
        return None


async def get_property_courts_tool(
    property_id: int,
    owner_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get all courts for a specific property.
    
    This tool retrieves all active courts associated with a property.
    If owner_id is provided, it uses the owner-specific service which
    includes ownership verification.
    
    Args:
        property_id: ID of the property
        owner_id: Owner ID for ownership verification (optional)
        
    Returns:
        List of court dictionaries for the property
        
    Example:
        courts = await get_property_courts_tool(
            property_id=123,
            owner_id=456
        )
    """
    try:
        logger.info(
            f"Getting courts for property: property_id={property_id}, "
            f"owner_id={owner_id}"
        )
        
        # Get court service from shared
        court_service = _get_court_service()
        
        if owner_id:
            # Use owner-specific service
            result = await call_sync_service(
                court_service.get_property_courts,
                db=None,
                property_id=property_id,
                owner_id=owner_id
            )
        else:
            # Use public service to get property details with courts
            result = await call_sync_service(
                public_service.get_property_details,
                db=None,
                property_id=property_id
            )
            
            if result.get('success'):
                property_data = result.get('data', {})
                courts = property_data.get('courts', [])
                return courts
        
        # Extract data from response
        if result.get('success'):
            courts = result.get('data', [])
            logger.info(f"Found {len(courts)} courts for property_id={property_id}")
            return courts
        else:
            logger.warning(
                f"Failed to get property courts: {result.get('message')} "
                f"(property_id={property_id})"
            )
            return []
            
    except Exception as e:
        logger.error(f"Error getting property courts: {e}", exc_info=True)
        return []


# Tool registry for easy access
COURT_TOOLS = {
    "search_courts": search_courts_tool,
    "get_court_details": get_court_details_tool,
    "get_property_courts": get_property_courts_tool,
}

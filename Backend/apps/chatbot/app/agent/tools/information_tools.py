"""
Information tools for the chatbot agent.

This module provides tools for the Information Node to handle all information-related
queries including property search, property details, court details, availability,
pricing, and media. All tools integrate with public_service through the sync bridge.

These tools are designed to be used by LangChain agents with automatic tool calling.

Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 9.6
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import date

from app.agent.tools.sync_bridge import call_sync_service

logger = logging.getLogger(__name__)


def _extract_response_data(result):
    """
    Extract data from a JSONResponse or dict result.
    
    Args:
        result: Either a JSONResponse object or a dict
        
    Returns:
        Tuple of (success, data, message)
    """
    try:
        # If it's a JSONResponse, extract the body
        if hasattr(result, 'body'):
            body_bytes = result.body
            body_str = body_bytes.decode('utf-8') if isinstance(body_bytes, bytes) else body_bytes
            response_data = json.loads(body_str)
            return (
                response_data.get('success', False),
                response_data.get('data'),
                response_data.get('message', '')
            )
        # If it's already a dict, use it directly
        elif isinstance(result, dict):
            return (
                result.get('success', False),
                result.get('data'),
                result.get('message', '')
            )
        else:
            logger.error(f"Unexpected result type: {type(result)}")
            return (False, None, "Unexpected response format")
    except Exception as e:
        logger.error(f"Error extracting response data: {e}", exc_info=True)
        return (False, None, str(e))


def _get_public_service():
    """
    Dynamically import public_service to avoid import conflicts.
    
    This function imports the public_service at runtime to prevent
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
    chatbot_path = str(Path(__file__).parent.parent.parent.parent.parent)
    original_path = sys.path.copy()
    
    try:
        # Remove chatbot path temporarily
        if chatbot_path in sys.path:
            sys.path.remove(chatbot_path)
        
        # Import directly from service module
        import importlib.util
        
        public_service_path = management_path / "app" / "services" / "public_service.py"
        
        # Load public_service
        spec = importlib.util.spec_from_file_location("public_service", public_service_path)
        public_service = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(public_service)
        
        return public_service
    finally:
        # Restore original path
        sys.path = original_path


async def search_properties_tool(
    city: Optional[str] = None,
    sport_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for properties with optional filters.
    
    This tool searches for active properties, optionally filtering by city,
    sport type, and price range. It uses public_service.search_properties()
    which returns properties accessible to all users.
    
    Includes comprehensive error handling for service failures.
    
    Args:
        city: City name to filter by (optional)
        sport_type: Sport type to filter courts by (optional)
        min_price: Minimum price per hour (optional)
        max_price: Maximum price per hour (optional)
        limit: Maximum number of results to return (default: 10)
        
    Returns:
        List of property dictionaries with basic information (id, name, city, address, amenities)
        Returns empty list on error
        
    Example:
        properties = await search_properties_tool(
            sport_type="tennis",
            city="New York",
            limit=5
        )
        
    Requirements: 20.3
    """
    try:
        logger.info(
            f"Searching properties: city={city}, sport_type={sport_type}, "
            f"min_price={min_price}, max_price={max_price}, limit={limit}"
        )
        
        # Get public service
        public_service = _get_public_service()
        
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
        success, data, message = _extract_response_data(result)
        
        if success and data:
            properties = data.get('items', [])
            logger.info(f"Found {len(properties)} properties")
            return properties
        else:
            logger.warning(f"Property search failed: {message}")
            return []
            
    except Exception as e:
        logger.error(
            f"Error searching properties: {e}",
            extra={
                "city": city,
                "sport_type": sport_type,
                "min_price": min_price,
                "max_price": max_price
            },
            exc_info=True
        )
        # Return empty list to allow conversation to continue
        return []


async def get_property_details_tool(
    property_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific property.
    
    This tool retrieves comprehensive property details including description,
    location, contact information, amenities, courts, and media. It uses
    public_service.get_property_details().
    
    Includes comprehensive error handling for service failures.
    
    Args:
        property_id: ID of the property to retrieve
        
    Returns:
        Property details dictionary containing:
        - id, name, description
        - address, city, state, country
        - phone, email, maps_link
        - amenities (list)
        - courts (list with court details)
        - media (list with photos/videos)
        
        Returns None if property not found or on error
        
    Example:
        details = await get_property_details_tool(property_id=123)
        
    Requirements: 20.3
    """
    try:
        logger.info(f"Getting property details: property_id={property_id}")
        
        # Get public service
        public_service = _get_public_service()
        
        # Call sync service using the bridge
        result = await call_sync_service(
            public_service.get_property_details,
            db=None,  # Auto-managed by sync bridge
            property_id=property_id
        )
        
        # Extract data from response
        success, data, message = _extract_response_data(result)
        
        if success and data:
            logger.info(f"Retrieved property details for property_id={property_id}")
            return data
        else:
            logger.warning(
                f"Failed to get property details: {message} "
                f"(property_id={property_id})"
            )
            return None
            
    except Exception as e:
        logger.error(
            f"Error getting property details: {e}",
            extra={"property_id": property_id},
            exc_info=True
        )
        # Return None to allow conversation to continue
        return None


async def get_court_details_tool(
    court_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific court.
    
    This tool retrieves comprehensive court details including specifications,
    amenities, property information, pricing rules, and media. It uses
    public_service.get_court_details().
    
    Includes comprehensive error handling for service failures.
    
    Args:
        court_id: ID of the court to retrieve
        
    Returns:
        Court details dictionary containing:
        - id, name, sport_type
        - description, specifications, amenities
        - property (basic property info)
        - pricing_rules (list with time-based pricing)
        - media (list with photos/videos)
        
        Returns None if court not found or on error
        
    Example:
        details = await get_court_details_tool(court_id=23)
        
    Requirements: 20.3
    """
    try:
        logger.info(f"Getting court details: court_id={court_id}")
        
        # Get public service
        public_service = _get_public_service()
        
        # Call sync service using the bridge
        result = await call_sync_service(
            public_service.get_court_details,
            db=None,  # Auto-managed by sync bridge
            court_id=court_id
        )
        
        # Extract data from response
        success, data, message = _extract_response_data(result)
        
        if success and data:
            logger.info(f"Retrieved court details for court_id={court_id}")
            return data
        else:
            logger.warning(
                f"Failed to get court details: {message} "
                f"(court_id={court_id})"
            )
            return None
            
    except Exception as e:
        logger.error(
            f"Error getting court details: {e}",
            extra={"court_id": court_id},
            exc_info=True
        )
        # Return None to allow conversation to continue
        return None


async def get_court_availability_tool(
    court_id: int,
    date_val: str  # ISO format YYYY-MM-DD
) -> Optional[Dict[str, Any]]:
    """
    Get available time slots for a court on a specific date.
    
    This tool retrieves all available time slots for booking on a specific
    date, excluding blocked slots and existing bookings. It uses
    public_service.get_available_slots() which returns slots with pricing.
    
    Includes comprehensive error handling for service failures.
    
    Args:
        court_id: ID of the court
        date_val: Date to check availability for (ISO format YYYY-MM-DD)
        
    Returns:
        Dictionary containing:
        - date: The requested date (ISO format)
        - court_id: The court ID
        - court_name: Name of the court
        - available_slots: List of available time slots with pricing
          Each slot contains: start_time, end_time, price_per_hour, label
        
        Returns None if court not found, no slots available, or on error
        
    Example:
        availability = await get_court_availability_tool(
            court_id=23,
            date_val="2026-03-10"
        )
        
    Requirements: 20.3
    """
    try:
        logger.info(f"Getting available slots: court_id={court_id}, date={date_val}")
        
        # Parse date string to date object
        if isinstance(date_val, str):
            from datetime import datetime
            date_obj = datetime.fromisoformat(date_val).date()
        else:
            date_obj = date_val
        
        # Get public service
        public_service = _get_public_service()
        
        # Call sync service using the bridge
        result = await call_sync_service(
            public_service.get_available_slots,
            db=None,  # Auto-managed by sync bridge
            court_id=court_id,
            date_val=date_obj
        )
        
        # Extract data from response
        success, data, message = _extract_response_data(result)
        
        if success and data:
            num_slots = len(data.get('available_slots', []))
            logger.info(
                f"Found {num_slots} available slots for court_id={court_id} "
                f"on {date_val}"
            )
            return data
        else:
            logger.warning(
                f"Failed to get available slots: {message} "
                f"(court_id={court_id}, date={date_val})"
            )
            return None
            
    except Exception as e:
        logger.error(
            f"Error getting available slots: {e}",
            extra={"court_id": court_id, "date": date_val},
            exc_info=True
        )
        # Return None to allow conversation to continue
        return None


async def get_court_pricing_tool(
    court_id: int,
    date_val: str  # ISO format YYYY-MM-DD
) -> Optional[Dict[str, Any]]:
    """
    Get pricing information for a court on a specific date.
    
    This tool retrieves pricing rules applicable to a specific court and date.
    It uses public_service.get_court_pricing_for_date() which returns
    time-based pricing rules for the day of week.
    
    Args:
        court_id: ID of the court
        date_val: Date to get pricing for (ISO format YYYY-MM-DD)
        
    Returns:
        Dictionary containing:
        - date: The requested date (ISO format)
        - day_of_week: Day of week (0=Monday, 6=Sunday)
        - pricing: List of pricing rules with start_time, end_time,
          price_per_hour, and label
        
        Returns None if court not found or no pricing configured
        
    Example:
        pricing = await get_court_pricing_tool(
            court_id=23,
            date_val="2026-03-10"
        )
    """
    try:
        logger.info(f"Getting pricing: court_id={court_id}, date={date_val}")
        
        # Parse date string to date object
        if isinstance(date_val, str):
            from datetime import datetime
            date_obj = datetime.fromisoformat(date_val).date()
        else:
            date_obj = date_val
        
        # Get public service
        public_service = _get_public_service()
        
        # Call sync service using the bridge
        result = await call_sync_service(
            public_service.get_court_pricing_for_date,
            db=None,  # Auto-managed by sync bridge
            court_id=court_id,
            date_val=date_obj
        )
        
        # Extract data from response
        success, data, message = _extract_response_data(result)
        
        if success and data:
            num_rules = len(data.get('pricing', []))
            logger.info(
                f"Found {num_rules} pricing rules for court_id={court_id} "
                f"on {date_val}"
            )
            return data
        else:
            logger.warning(
                f"Failed to get pricing: {message} "
                f"(court_id={court_id}, date={date_val})"
            )
            return None
            
    except Exception as e:
        logger.error(f"Error getting pricing: {e}", exc_info=True)
        return None


async def get_property_media_tool(
    property_id: int,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get media (photos/videos) for a property.
    
    This tool extracts media from property details. It calls
    get_property_details_tool and returns only the media portion.
    
    Args:
        property_id: ID of the property
        limit: Maximum number of media items to return (default: 5)
        
    Returns:
        List of media dictionaries containing:
        - id: Media ID
        - media_type: Type of media (photo, video)
        - url: Full URL to the media
        - thumbnail_url: URL to thumbnail (if available)
        - caption: Media caption/description
        
    Example:
        media = await get_property_media_tool(property_id=6, limit=3)
    """
    try:
        logger.info(f"Getting property media: property_id={property_id}, limit={limit}")
        
        # Get property details which includes media
        property_data = await get_property_details_tool(property_id=property_id)
        
        if not property_data:
            logger.warning(f"Property not found: property_id={property_id}")
            return []
        
        # Extract media
        media = property_data.get('media', [])
        
        # Limit results
        limited_media = media[:limit] if media else []
        
        logger.info(
            f"Found {len(limited_media)} media items for property_id={property_id}"
        )
        return limited_media
        
    except Exception as e:
        logger.error(f"Error getting property media: {e}", exc_info=True)
        return []


async def get_court_media_tool(
    court_id: int,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Get media (photos/videos) for a court.
    
    This tool extracts media from court details. It calls
    get_court_details_tool and returns only the media portion.
    
    Args:
        court_id: ID of the court
        limit: Maximum number of media items to return (default: 5)
        
    Returns:
        List of media dictionaries containing:
        - id: Media ID
        - media_type: Type of media (photo, video)
        - url: Full URL to the media
        - thumbnail_url: URL to thumbnail (if available)
        - caption: Media caption/description
        
    Example:
        media = await get_court_media_tool(court_id=23, limit=3)
    """
    try:
        logger.info(f"Getting court media: court_id={court_id}, limit={limit}")
        
        # Get court details which includes media
        court_data = await get_court_details_tool(court_id=court_id)
        
        if not court_data:
            logger.warning(f"Court not found: court_id={court_id}")
            return []
        
        # Extract media
        media = court_data.get('media', [])
        
        # Limit results
        limited_media = media[:limit] if media else []
        
        logger.info(
            f"Found {len(limited_media)} media items for court_id={court_id}"
        )
        return limited_media
        
    except Exception as e:
        logger.error(f"Error getting court media: {e}", exc_info=True)
        return []


# Tool registry for easy access
INFORMATION_TOOLS = {
    "search_properties": search_properties_tool,
    "get_property_details": get_property_details_tool,
    "get_court_details": get_court_details_tool,
    "get_court_availability": get_court_availability_tool,
    "get_court_pricing": get_court_pricing_tool,
    "get_property_media": get_property_media_tool,
    "get_court_media": get_court_media_tool,
}

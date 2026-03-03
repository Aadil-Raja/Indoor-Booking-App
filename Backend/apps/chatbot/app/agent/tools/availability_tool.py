"""
Availability checking tools for the chatbot agent.

This module provides tools for checking court availability and retrieving
available time slots by integrating with the sync availability_service and
public_service through the sync bridge.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import date

from app.agent.tools.sync_bridge import call_sync_service
from shared.services import availability_service

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
        
        # Import directly from service modules
        import importlib.util
        
        availability_service_path = management_path / "app" / "services" / "availability_service.py"
        public_service_path = management_path / "app" / "services" / "public_service.py"
        
        # Load availability_service
        spec = importlib.util.spec_from_file_location("availability_service", availability_service_path)
        availability_service = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(availability_service)
        
        # Load public_service
        spec = importlib.util.spec_from_file_location("public_service", public_service_path)
        public_service = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(public_service)
        
        return availability_service, public_service
    finally:
        # Restore original path
        sys.path = original_path


async def check_availability_tool(
    court_id: int,
    owner_id: int,
    from_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """
    Check blocked time slots for a court.
    
    This tool retrieves all blocked time slots for a specific court,
    optionally filtering from a specific date onwards. It uses the
    availability_service.get_blocked_slots method.
    
    Args:
        court_id: ID of the court to check
        owner_id: Owner ID for ownership verification
        from_date: Optional start date to filter blocked slots (defaults to today)
        
    Returns:
        List of blocked slot dictionaries with date, start_time, end_time, and reason
        
    Example:
        blocked_slots = await check_availability_tool(
            court_id=123,
            owner_id=456,
            from_date=date(2024, 1, 15)
        )
    """
    try:
        logger.info(
            f"Checking availability: court_id={court_id}, owner_id={owner_id}, "
            f"from_date={from_date}"
        )
        
        # Get management services
        availability_service, public_service = _get_management_services()
        
        # Call sync service using the bridge
        result = await call_sync_service(
            availability_service.get_blocked_slots,
            db=None,  # Auto-managed by sync bridge
            court_id=court_id,
            owner_id=owner_id,
            from_date=from_date
        )
        
        # Extract data from response
        if result.get('success'):
            blocked_slots = result.get('data', [])
            logger.info(f"Found {len(blocked_slots)} blocked slots for court_id={court_id}")
            return blocked_slots
        else:
            logger.warning(
                f"Failed to get blocked slots: {result.get('message')} "
                f"(court_id={court_id})"
            )
            return []
            
    except Exception as e:
        logger.error(f"Error checking availability: {e}", exc_info=True)
        return []


async def get_available_slots_tool(
    court_id: int,
    date_val: date
) -> Optional[Dict[str, Any]]:
    """
    Get available time slots for a court on a specific date.
    
    This tool retrieves all available time slots for booking on a specific
    date, excluding blocked slots and existing bookings. It uses the
    public_service.get_available_slots method which returns slots with
    pricing information.
    
    Args:
        court_id: ID of the court
        date_val: Date to check availability for
        
    Returns:
        Dictionary containing:
        - date: The requested date
        - court_id: The court ID
        - court_name: Name of the court
        - available_slots: List of available time slots with pricing
        
        Returns None if court not found or no slots available
        
    Example:
        availability = await get_available_slots_tool(
            court_id=123,
            date_val=date(2024, 1, 15)
        )
        
        # Result format:
        {
            "date": "2024-01-15",
            "court_id": 123,
            "court_name": "Tennis Court A",
            "available_slots": [
                {
                    "start_time": "09:00:00",
                    "end_time": "10:00:00",
                    "price_per_hour": 50.0,
                    "label": "Morning Rate"
                },
                ...
            ]
        }
    """
    try:
        logger.info(
            f"Getting available slots: court_id={court_id}, date={date_val}"
        )
        
        # Get management services
        availability_service, public_service = _get_management_services()
        
        # Call sync service using the bridge
        result = await call_sync_service(
            public_service.get_available_slots,
            db=None,  # Auto-managed by sync bridge
            court_id=court_id,
            date_val=date_val
        )
        
        # Extract data from response
        if result.get('success'):
            availability_data = result.get('data')
            num_slots = len(availability_data.get('available_slots', []))
            logger.info(
                f"Found {num_slots} available slots for court_id={court_id} "
                f"on {date_val}"
            )
            return availability_data
        else:
            logger.warning(
                f"Failed to get available slots: {result.get('message')} "
                f"(court_id={court_id}, date={date_val})"
            )
            return None
            
    except Exception as e:
        logger.error(f"Error getting available slots: {e}", exc_info=True)
        return None


# Tool registry for easy access
AVAILABILITY_TOOLS = {
    "check_availability": check_availability_tool,
    "get_available_slots": get_available_slots_tool,
}

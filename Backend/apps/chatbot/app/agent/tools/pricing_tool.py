"""
Pricing tools for the chatbot agent.

This module provides tools for retrieving pricing information for courts
by integrating with the sync public_service through the sync bridge.
"""

import logging
from typing import Dict, Any, Optional
from datetime import date, time

from app.agent.tools.sync_bridge import call_sync_service

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
        from app.services import public_service
        return public_service
    finally:
        # Restore original path
        sys.path = original_path


async def get_pricing_tool(
    court_id: int,
    date_val: date
) -> Optional[Dict[str, Any]]:
    """
    Get pricing information for a court on a specific date.
    
    This tool retrieves all pricing rules applicable to a specific court
    on a given date. It uses the public_service.get_court_pricing_for_date
    method which returns pricing rules based on the day of week.
    
    Args:
        court_id: ID of the court
        date_val: Date to get pricing for
        
    Returns:
        Dictionary containing:
        - date: The requested date (ISO format)
        - day_of_week: Day of week (0=Monday, 6=Sunday)
        - pricing: List of pricing rules with start_time, end_time, price_per_hour, label
        
        Returns None if court not found or no pricing available
        
    Example:
        pricing = await get_pricing_tool(
            court_id=123,
            date_val=date(2024, 1, 15)
        )
        
        # Result format:
        {
            "date": "2024-01-15",
            "day_of_week": 0,
            "pricing": [
                {
                    "start_time": "09:00:00",
                    "end_time": "17:00:00",
                    "price_per_hour": 50.0,
                    "label": "Daytime Rate"
                },
                {
                    "start_time": "17:00:00",
                    "end_time": "22:00:00",
                    "price_per_hour": 75.0,
                    "label": "Evening Rate"
                }
            ]
        }
    """
    try:
        logger.info(
            f"Getting pricing: court_id={court_id}, date={date_val}"
        )
        
        # Get management services
        public_service = _get_management_services()
        
        # Call sync service using the bridge
        result = await call_sync_service(
            public_service.get_court_pricing_for_date,
            db=None,  # Auto-managed by sync bridge
            court_id=court_id,
            date_val=date_val
        )
        
        # Extract data from response
        if result.get('success'):
            pricing_data = result.get('data')
            num_rules = len(pricing_data.get('pricing', []))
            logger.info(
                f"Found {num_rules} pricing rules for court_id={court_id} "
                f"on {date_val}"
            )
            return pricing_data
        else:
            logger.warning(
                f"Failed to get pricing: {result.get('message')} "
                f"(court_id={court_id}, date={date_val})"
            )
            return None
            
    except Exception as e:
        logger.error(f"Error getting pricing: {e}", exc_info=True)
        return None


async def calculate_total_price(
    court_id: int,
    date_val: date,
    start_time: time,
    duration_minutes: int
) -> Optional[float]:
    """
    Calculate total price for a booking based on duration.
    
    This tool calculates the total cost for booking a court for a specific
    duration by applying the appropriate pricing rules for each hour.
    
    Args:
        court_id: ID of the court
        date_val: Date of the booking
        start_time: Start time of the booking
        duration_minutes: Duration of the booking in minutes
        
    Returns:
        Total price as a float, or None if pricing cannot be calculated
        
    Example:
        total = await calculate_total_price(
            court_id=123,
            date_val=date(2024, 1, 15),
            start_time=time(16, 0),  # 4:00 PM
            duration_minutes=90  # 1.5 hours
        )
        # Returns: 112.5 (if rate is $75/hour)
    """
    try:
        logger.info(
            f"Calculating total price: court_id={court_id}, date={date_val}, "
            f"start_time={start_time}, duration={duration_minutes}min"
        )
        
        # Get pricing data for the date
        pricing_data = await get_pricing_tool(court_id, date_val)
        
        if not pricing_data or not pricing_data.get('pricing'):
            logger.warning(
                f"No pricing data available for calculation "
                f"(court_id={court_id}, date={date_val})"
            )
            return None
        
        pricing_rules = pricing_data['pricing']
        
        # Convert duration to hours (as float)
        duration_hours = duration_minutes / 60.0
        
        # Find the applicable pricing rule for the start time
        # Assuming the booking falls within a single pricing period
        applicable_rate = None
        for rule in pricing_rules:
            rule_start = time.fromisoformat(rule['start_time'])
            rule_end = time.fromisoformat(rule['end_time'])
            
            # Check if start_time falls within this pricing rule
            if rule_start <= start_time < rule_end:
                applicable_rate = rule['price_per_hour']
                logger.info(
                    f"Found applicable rate: ${applicable_rate}/hour "
                    f"(rule: {rule_start}-{rule_end})"
                )
                break
        
        if applicable_rate is None:
            logger.warning(
                f"No pricing rule found for start_time={start_time} "
                f"(court_id={court_id}, date={date_val})"
            )
            return None
        
        # Calculate total price
        total_price = applicable_rate * duration_hours
        
        logger.info(
            f"Calculated total price: ${total_price:.2f} "
            f"({duration_hours}h × ${applicable_rate}/h)"
        )
        
        return round(total_price, 2)
        
    except Exception as e:
        logger.error(f"Error calculating total price: {e}", exc_info=True)
        return None


# Tool registry for easy access
PRICING_TOOLS = {
    "get_pricing": get_pricing_tool,
    "calculate_total_price": calculate_total_price,
}

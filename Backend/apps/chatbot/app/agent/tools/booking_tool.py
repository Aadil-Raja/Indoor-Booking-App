"""
Booking tools for the chatbot agent.

This module provides tools for creating bookings by integrating with the
sync booking_service through the sync bridge. Bookings are created with
pending status awaiting confirmation or payment.
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
        from app.services import booking_service
        return booking_service
    finally:
        # Restore original path
        sys.path = original_path


def _get_booking_schema():
    """
    Dynamically import BookingCreate schema from shared schemas.
    
    Returns:
        BookingCreate: The Pydantic schema class for creating bookings
    """
    import sys
    from pathlib import Path
    
    # Add Backend path for shared modules
    backend_path = Path(__file__).parent.parent.parent.parent.parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    # Import shared schema
    from shared.schemas.booking import BookingCreate
    return BookingCreate


async def create_booking_tool(
    customer_id: int,
    court_id: int,
    booking_date: date,
    start_time: time,
    end_time: time,
    notes: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Create a new booking with pending status.
    
    This tool creates a booking by calling the booking_service.create_booking
    method through the sync bridge. The booking is created with pending status
    and awaits confirmation or payment.
    
    The tool performs the following validations:
    - Court exists and is active
    - Time slot is not blocked
    - No booking conflicts exist
    - Pricing is available for the time slot
    
    Args:
        customer_id: ID of the customer making the booking (user_id)
        court_id: ID of the court to book
        booking_date: Date of the booking
        start_time: Start time of the booking
        end_time: End time of the booking
        notes: Optional notes for the booking
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating if booking was created
        - message: Success or error message
        - data: Booking details if successful (id, booking_date, start_time, 
                end_time, total_price, status, payment_status)
        
        Returns None if an unexpected error occurs
        
    Example:
        result = await create_booking_tool(
            customer_id=123,
            court_id=456,
            booking_date=date(2024, 1, 15),
            start_time=time(14, 0),
            end_time=time(15, 30),
            notes="Birthday party booking"
        )
        
        # Success result format:
        {
            "success": True,
            "message": "Booking created successfully",
            "data": {
                "id": 789,
                "booking_date": "2024-01-15",
                "start_time": "14:00:00",
                "end_time": "15:30:00",
                "total_price": 75.0,
                "status": "pending",
                "payment_status": "pending"
            }
        }
        
        # Error result format:
        {
            "success": False,
            "message": "This time slot is already booked"
        }
    """
    try:
        logger.info(
            f"Creating booking: customer_id={customer_id}, court_id={court_id}, "
            f"date={booking_date}, time={start_time}-{end_time}"
        )
        
        # Get management services and schema
        booking_service = _get_management_services()
        BookingCreate = _get_booking_schema()
        
        # Create booking data object
        booking_data = BookingCreate(
            court_id=court_id,
            booking_date=booking_date,
            start_time=start_time,
            end_time=end_time,
            notes=notes
        )
        
        # Call sync service using the bridge
        result = await call_sync_service(
            booking_service.create_booking,
            db=None,  # Auto-managed by sync bridge
            customer_id=customer_id,
            data=booking_data
        )
        
        # Log result
        if result.get('success'):
            booking_id = result.get('data', {}).get('id')
            total_price = result.get('data', {}).get('total_price')
            logger.info(
                f"Booking created successfully: booking_id={booking_id}, "
                f"total_price=${total_price}"
            )
        else:
            logger.warning(
                f"Failed to create booking: {result.get('message')} "
                f"(customer_id={customer_id}, court_id={court_id})"
            )
        
        return result
            
    except ValueError as e:
        # Validation errors from Pydantic schema
        logger.warning(f"Booking validation error: {e}")
        return {
            "success": False,
            "message": f"Invalid booking data: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error creating booking: {e}", exc_info=True)
        return {
            "success": False,
            "message": "An unexpected error occurred while creating the booking"
        }


async def get_booking_details_tool(
    booking_id: int,
    user_id: int
) -> Optional[Dict[str, Any]]:
    """
    Get details of a specific booking.
    
    This tool retrieves detailed information about a booking, including
    court, property, and customer information. Access is restricted to
    the customer who made the booking or the property owner.
    
    Args:
        booking_id: ID of the booking to retrieve
        user_id: ID of the user requesting the details
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating if booking was found
        - message: Success or error message
        - data: Booking details if successful
        
        Returns None if an unexpected error occurs
        
    Example:
        result = await get_booking_details_tool(
            booking_id=789,
            user_id=123
        )
        
        # Success result format:
        {
            "success": True,
            "message": "Booking details retrieved successfully",
            "data": {
                "id": 789,
                "booking_date": "2024-01-15",
                "start_time": "14:00:00",
                "end_time": "15:30:00",
                "total_hours": 1.5,
                "price_per_hour": 50.0,
                "total_price": 75.0,
                "status": "pending",
                "payment_status": "pending",
                "notes": "Birthday party booking",
                "court": {
                    "id": 456,
                    "name": "Tennis Court A",
                    "sport_type": "tennis"
                },
                "property": {
                    "id": 123,
                    "name": "Downtown Sports Center",
                    "address": "123 Main St",
                    "phone": "555-0100"
                }
            }
        }
    """
    try:
        logger.info(
            f"Getting booking details: booking_id={booking_id}, user_id={user_id}"
        )
        
        # Get management services
        booking_service = _get_management_services()
        
        # Call sync service using the bridge
        result = await call_sync_service(
            booking_service.get_booking_details,
            db=None,  # Auto-managed by sync bridge
            booking_id=booking_id,
            user_id=user_id
        )
        
        # Log result
        if result.get('success'):
            logger.info(f"Booking details retrieved: booking_id={booking_id}")
        else:
            logger.warning(
                f"Failed to get booking details: {result.get('message')} "
                f"(booking_id={booking_id}, user_id={user_id})"
            )
        
        return result
            
    except Exception as e:
        logger.error(f"Error getting booking details: {e}", exc_info=True)
        return {
            "success": False,
            "message": "An unexpected error occurred while retrieving booking details"
        }


async def cancel_booking_tool(
    booking_id: int,
    user_id: int
) -> Optional[Dict[str, Any]]:
    """
    Cancel a booking (customer only).
    
    This tool allows a customer to cancel their booking. Only the customer
    who made the booking can cancel it. Completed bookings cannot be cancelled.
    
    Args:
        booking_id: ID of the booking to cancel
        user_id: ID of the user (must be the customer)
        
    Returns:
        Dictionary containing:
        - success: Boolean indicating if booking was cancelled
        - message: Success or error message
        
        Returns None if an unexpected error occurs
        
    Example:
        result = await cancel_booking_tool(
            booking_id=789,
            user_id=123
        )
        
        # Success result format:
        {
            "success": True,
            "message": "Booking cancelled successfully"
        }
    """
    try:
        logger.info(
            f"Cancelling booking: booking_id={booking_id}, user_id={user_id}"
        )
        
        # Get management services
        booking_service = _get_management_services()
        
        # Call sync service using the bridge
        result = await call_sync_service(
            booking_service.cancel_booking,
            db=None,  # Auto-managed by sync bridge
            booking_id=booking_id,
            user_id=user_id
        )
        
        # Log result
        if result.get('success'):
            logger.info(f"Booking cancelled: booking_id={booking_id}")
        else:
            logger.warning(
                f"Failed to cancel booking: {result.get('message')} "
                f"(booking_id={booking_id}, user_id={user_id})"
            )
        
        return result
            
    except Exception as e:
        logger.error(f"Error cancelling booking: {e}", exc_info=True)
        return {
            "success": False,
            "message": "An unexpected error occurred while cancelling the booking"
        }


# Tool registry for easy access
BOOKING_TOOLS = {
    "create_booking": create_booking_tool,
    "get_booking_details": get_booking_details_tool,
    "cancel_booking": cancel_booking_tool,
}

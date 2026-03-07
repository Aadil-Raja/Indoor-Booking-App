"""
Unit tests for create_booking node.

Tests the create_booking node functionality including:
- Successful booking creation
- Time slot parsing
- Error handling for missing data
- Error handling for invalid data
- Flow state clearing on success/failure
"""

import pytest
from datetime import date, time
from unittest.mock import AsyncMock, MagicMock

from app.agent.nodes.booking.create_booking import create_booking


@pytest.mark.asyncio
async def test_create_booking_success():
    """Test successful booking creation with valid data."""
    # Arrange
    state = {
        "chat_id": "test_chat_123",
        "user_id": "456",
        "flow_state": {
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 10,
            "court_name": "Tennis Court A",
            "date": "2024-12-25",
            "time_slot": "14:00-15:00",
            "booking_step": "confirming"
        }
    }
    
    # Mock tools
    tools = {}
    
    # Mock create_booking_tool to return success
    import app.agent.nodes.booking.create_booking as create_booking_module
    original_tool = create_booking_module.create_booking_tool
    
    async def mock_create_booking_tool(*args, **kwargs):
        return {
            "success": True,
            "data": {
                "id": 789,
                "booking_date": "2024-12-25",
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "total_price": 75.0,
                "status": "pending",
                "payment_status": "pending"
            }
        }
    
    create_booking_module.create_booking_tool = mock_create_booking_tool
    
    try:
        # Act
        result = await create_booking(state, tools)
        
        # Assert
        assert result["response_type"] == "text"
        assert "Booking confirmed" in result["response_content"]
        assert "789" in result["response_content"]
        assert result["next_node"] == "end"
        assert result["flow_state"] == {}  # Flow state should be cleared (Req 15.5)
        assert result["response_metadata"]["booking_id"] == 789
        
    finally:
        # Restore original tool
        create_booking_module.create_booking_tool = original_tool


@pytest.mark.asyncio
async def test_create_booking_missing_required_fields():
    """Test error handling when required booking fields are missing."""
    # Arrange
    state = {
        "chat_id": "test_chat_123",
        "user_id": "456",
        "flow_state": {
            "property_id": 1,
            "property_name": "Sports Center",
            # Missing court_id, date, time_slot
            "booking_step": "confirming"
        }
    }
    
    tools = {}
    
    # Act
    result = await create_booking(state, tools)
    
    # Assert
    assert result["response_type"] == "text"
    assert "missing" in result["response_content"].lower()
    assert result["next_node"] == "select_property"
    assert result["flow_state"] == {}  # Flow state should be cleared


@pytest.mark.asyncio
async def test_create_booking_invalid_date_format():
    """Test error handling for invalid date format."""
    # Arrange
    state = {
        "chat_id": "test_chat_123",
        "user_id": "456",
        "flow_state": {
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 10,
            "court_name": "Tennis Court A",
            "date": "invalid-date",
            "time_slot": "14:00-15:00",
            "booking_step": "confirming"
        }
    }
    
    tools = {}
    
    # Act
    result = await create_booking(state, tools)
    
    # Assert
    assert result["response_type"] == "text"
    assert "error" in result["response_content"].lower()
    assert "date" in result["response_content"].lower()
    assert result["next_node"] == "select_date"
    assert result["flow_state"]["date"] is None
    assert result["flow_state"]["booking_step"] == "court_selected"


@pytest.mark.asyncio
async def test_create_booking_invalid_time_slot_format():
    """Test error handling for invalid time slot format."""
    # Arrange
    state = {
        "chat_id": "test_chat_123",
        "user_id": "456",
        "flow_state": {
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 10,
            "court_name": "Tennis Court A",
            "date": "2024-12-25",
            "time_slot": "invalid-time",
            "booking_step": "confirming"
        }
    }
    
    tools = {}
    
    # Act
    result = await create_booking(state, tools)
    
    # Assert
    assert result["response_type"] == "text"
    assert "error" in result["response_content"].lower()
    assert "time" in result["response_content"].lower()
    assert result["next_node"] == "select_time"
    assert result["flow_state"]["time_slot"] is None
    assert result["flow_state"]["booking_step"] == "date_selected"


@pytest.mark.asyncio
async def test_create_booking_invalid_time_range():
    """Test error handling when end time is before start time."""
    # Arrange
    state = {
        "chat_id": "test_chat_123",
        "user_id": "456",
        "flow_state": {
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 10,
            "court_name": "Tennis Court A",
            "date": "2024-12-25",
            "time_slot": "15:00-14:00",  # End before start
            "booking_step": "confirming"
        }
    }
    
    tools = {}
    
    # Act
    result = await create_booking(state, tools)
    
    # Assert
    assert result["response_type"] == "text"
    assert "end time must be after" in result["response_content"].lower()
    assert result["next_node"] == "select_time"
    assert result["flow_state"]["time_slot"] is None


@pytest.mark.asyncio
async def test_create_booking_tool_failure_time_conflict():
    """Test handling of booking tool failure due to time conflict."""
    # Arrange
    state = {
        "chat_id": "test_chat_123",
        "user_id": "456",
        "flow_state": {
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 10,
            "court_name": "Tennis Court A",
            "date": "2024-12-25",
            "time_slot": "14:00-15:00",
            "booking_step": "confirming"
        }
    }
    
    tools = {}
    
    # Mock create_booking_tool to return failure
    import app.agent.nodes.booking.create_booking as create_booking_module
    original_tool = create_booking_module.create_booking_tool
    
    async def mock_create_booking_tool(*args, **kwargs):
        return {
            "success": False,
            "message": "This time slot is already booked"
        }
    
    create_booking_module.create_booking_tool = mock_create_booking_tool
    
    try:
        # Act
        result = await create_booking(state, tools)
        
        # Assert
        assert result["response_type"] == "text"
        assert "Unable to create booking" in result["response_content"]
        assert "already booked" in result["response_content"]
        assert result["next_node"] == "select_time"  # Route back to time selection
        assert result["flow_state"]["time_slot"] is None  # Time slot cleared
        assert result["flow_state"]["booking_step"] == "date_selected"
        
    finally:
        # Restore original tool
        create_booking_module.create_booking_tool = original_tool


@pytest.mark.asyncio
async def test_create_booking_tool_failure_generic():
    """Test handling of generic booking tool failure."""
    # Arrange
    state = {
        "chat_id": "test_chat_123",
        "user_id": "456",
        "flow_state": {
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 10,
            "court_name": "Tennis Court A",
            "date": "2024-12-25",
            "time_slot": "14:00-15:00",
            "booking_step": "confirming"
        }
    }
    
    tools = {}
    
    # Mock create_booking_tool to return generic failure
    import app.agent.nodes.booking.create_booking as create_booking_module
    original_tool = create_booking_module.create_booking_tool
    
    async def mock_create_booking_tool(*args, **kwargs):
        return {
            "success": False,
            "message": "Database connection error"
        }
    
    create_booking_module.create_booking_tool = mock_create_booking_tool
    
    try:
        # Act
        result = await create_booking(state, tools)
        
        # Assert
        assert result["response_type"] == "text"
        assert "Unable to create booking" in result["response_content"]
        assert result["next_node"] == "end"  # End flow for generic errors
        assert result["flow_state"] == {}  # Flow state cleared (Req 15.5)
        
    finally:
        # Restore original tool
        create_booking_module.create_booking_tool = original_tool


@pytest.mark.asyncio
async def test_create_booking_missing_user_id():
    """Test error handling when user_id is missing."""
    # Arrange
    state = {
        "chat_id": "test_chat_123",
        "user_id": None,  # Missing user_id
        "flow_state": {
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 10,
            "court_name": "Tennis Court A",
            "date": "2024-12-25",
            "time_slot": "14:00-15:00",
            "booking_step": "confirming"
        }
    }
    
    tools = {}
    
    # Act
    result = await create_booking(state, tools)
    
    # Assert
    assert result["response_type"] == "text"
    assert "trouble identifying" in result["response_content"].lower()
    assert result["next_node"] == "end"
    assert result["flow_state"] == {}  # Flow state cleared


@pytest.mark.asyncio
async def test_create_booking_time_slot_parsing():
    """Test correct parsing of time_slot into start_time and end_time."""
    # Arrange
    state = {
        "chat_id": "test_chat_123",
        "user_id": "456",
        "flow_state": {
            "property_id": 1,
            "property_name": "Sports Center",
            "court_id": 10,
            "court_name": "Tennis Court A",
            "date": "2024-12-25",
            "time_slot": "09:30-11:45",  # Non-standard times
            "booking_step": "confirming"
        }
    }
    
    tools = {}
    
    # Mock create_booking_tool to capture arguments
    import app.agent.nodes.booking.create_booking as create_booking_module
    original_tool = create_booking_module.create_booking_tool
    
    captured_args = {}
    
    async def mock_create_booking_tool(*args, **kwargs):
        captured_args.update(kwargs)
        return {
            "success": True,
            "data": {
                "id": 789,
                "booking_date": "2024-12-25",
                "start_time": "09:30:00",
                "end_time": "11:45:00",
                "total_price": 150.0,
                "status": "pending",
                "payment_status": "pending"
            }
        }
    
    create_booking_module.create_booking_tool = mock_create_booking_tool
    
    try:
        # Act
        result = await create_booking(state, tools)
        
        # Assert
        assert captured_args["start_time"] == time(9, 30)
        assert captured_args["end_time"] == time(11, 45)
        assert captured_args["booking_date"] == date(2024, 12, 25)
        assert captured_args["customer_id"] == 456
        assert captured_args["court_id"] == 10
        
    finally:
        # Restore original tool
        create_booking_module.create_booking_tool = original_tool

"""
Test for confirm booking node.

This test verifies that the confirm booking node correctly:
- Presents booking summary with all details
- Handles confirmation responses
- Handles cancellation responses
- Handles modification requests
"""

import pytest
from datetime import datetime

from app.agent.nodes.booking.confirm import confirm_booking


@pytest.mark.asyncio
async def test_present_booking_summary():
    """Test that booking summary is presented correctly."""
    state = {
        "chat_id": "test-chat-123",
        "user_id": "test-user-123",
        "owner_id": "test-owner-123",
        "user_message": "14:00",
        "flow_state": {
            "intent": "booking",
            "property_id": "1",
            "property_name": "Downtown Sports Center",
            "service_id": "10",
            "service_name": "Tennis Court A",
            "sport_type": "tennis",
            "date": "2024-12-25",
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "price": 50.0,
            "step": "time_selected"
        },
        "bot_memory": {},
        "messages": [],
        "response_content": "",
        "response_type": "text",
        "response_metadata": {}
    }
    
    result = await confirm_booking(state)
    
    # Verify response contains booking summary
    assert "Booking Summary" in result["response_content"]
    assert "Downtown Sports Center" in result["response_content"]
    assert "Tennis Court A" in result["response_content"]
    assert "tennis" in result["response_content"]
    assert "$50.00/hour" in result["response_content"]
    assert "Would you like to confirm this booking?" in result["response_content"]
    
    # Verify flow state updated
    assert result["flow_state"]["step"] == "confirm"
    assert "total_price" in result["flow_state"]
    assert "duration_hours" in result["flow_state"]


@pytest.mark.asyncio
async def test_confirm_booking_yes():
    """Test that user confirmation is handled correctly."""
    state = {
        "chat_id": "test-chat-123",
        "user_id": "test-user-123",
        "owner_id": "test-owner-123",
        "user_message": "yes, confirm it",
        "flow_state": {
            "intent": "booking",
            "property_id": "1",
            "property_name": "Downtown Sports Center",
            "service_id": "10",
            "service_name": "Tennis Court A",
            "sport_type": "tennis",
            "date": "2024-12-25",
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "price": 50.0,
            "step": "confirm"
        },
        "bot_memory": {},
        "messages": [],
        "response_content": "",
        "response_type": "text",
        "response_metadata": {}
    }
    
    result = await confirm_booking(state)
    
    # Verify confirmation response
    assert "creating your booking" in result["response_content"].lower()
    
    # Verify flow state updated to confirmed
    assert result["flow_state"]["step"] == "confirmed"


@pytest.mark.asyncio
async def test_cancel_booking():
    """Test that booking cancellation is handled correctly."""
    state = {
        "chat_id": "test-chat-123",
        "user_id": "test-user-123",
        "owner_id": "test-owner-123",
        "user_message": "no, cancel",
        "flow_state": {
            "intent": "booking",
            "property_id": "1",
            "property_name": "Downtown Sports Center",
            "service_id": "10",
            "service_name": "Tennis Court A",
            "sport_type": "tennis",
            "date": "2024-12-25",
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "price": 50.0,
            "step": "confirm"
        },
        "bot_memory": {},
        "messages": [],
        "response_content": "",
        "response_type": "text",
        "response_metadata": {}
    }
    
    result = await confirm_booking(state)
    
    # Verify cancellation response
    assert "cancelled" in result["response_content"].lower()
    
    # Verify flow state cleared
    assert result["flow_state"]["step"] == "cancelled"
    assert "property_id" not in result["flow_state"]
    assert "service_id" not in result["flow_state"]
    assert "date" not in result["flow_state"]


@pytest.mark.asyncio
async def test_modify_date():
    """Test that date modification request is handled correctly."""
    state = {
        "chat_id": "test-chat-123",
        "user_id": "test-user-123",
        "owner_id": "test-owner-123",
        "user_message": "change the date",
        "flow_state": {
            "intent": "booking",
            "property_id": "1",
            "property_name": "Downtown Sports Center",
            "service_id": "10",
            "service_name": "Tennis Court A",
            "sport_type": "tennis",
            "date": "2024-12-25",
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "price": 50.0,
            "step": "confirm"
        },
        "bot_memory": {},
        "messages": [],
        "response_content": "",
        "response_type": "text",
        "response_metadata": {}
    }
    
    result = await confirm_booking(state)
    
    # Verify modification response
    assert "different date" in result["response_content"].lower()
    
    # Verify flow state updated
    assert result["flow_state"]["step"] == "service_selected"
    assert "date" not in result["flow_state"]
    assert "start_time" not in result["flow_state"]
    assert "end_time" not in result["flow_state"]
    # Property and service should still be present
    assert result["flow_state"]["property_id"] == "1"
    assert result["flow_state"]["service_id"] == "10"


@pytest.mark.asyncio
async def test_modify_time():
    """Test that time modification request is handled correctly."""
    state = {
        "chat_id": "test-chat-123",
        "user_id": "test-user-123",
        "owner_id": "test-owner-123",
        "user_message": "change the time",
        "flow_state": {
            "intent": "booking",
            "property_id": "1",
            "property_name": "Downtown Sports Center",
            "service_id": "10",
            "service_name": "Tennis Court A",
            "sport_type": "tennis",
            "date": "2024-12-25",
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "price": 50.0,
            "step": "confirm"
        },
        "bot_memory": {},
        "messages": [],
        "response_content": "",
        "response_type": "text",
        "response_metadata": {}
    }
    
    result = await confirm_booking(state)
    
    # Verify modification response
    assert "different time" in result["response_content"].lower()
    
    # Verify flow state updated
    assert result["flow_state"]["step"] == "date_selected"
    assert "start_time" not in result["flow_state"]
    assert "end_time" not in result["flow_state"]
    # Property, service, and date should still be present
    assert result["flow_state"]["property_id"] == "1"
    assert result["flow_state"]["service_id"] == "10"
    assert result["flow_state"]["date"] == "2024-12-25"


@pytest.mark.asyncio
async def test_missing_booking_details():
    """Test that missing booking details are handled gracefully."""
    state = {
        "chat_id": "test-chat-123",
        "user_id": "test-user-123",
        "owner_id": "test-owner-123",
        "user_message": "confirm",
        "flow_state": {
            "intent": "booking",
            "property_id": "1",
            # Missing other required fields
            "step": "time_selected"
        },
        "bot_memory": {},
        "messages": [],
        "response_content": "",
        "response_type": "text",
        "response_metadata": {}
    }
    
    result = await confirm_booking(state)
    
    # Verify error response
    assert "missing" in result["response_content"].lower()
    
    # Verify flow state reset
    assert result["flow_state"]["step"] == "select_property"

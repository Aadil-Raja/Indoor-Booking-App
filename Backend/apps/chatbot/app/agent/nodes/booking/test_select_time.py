"""
Unit tests for select_time node.

This module tests the time selection functionality including:
- Skipping when time_slot already exists
- Presenting available time slots
- Parsing user time selection
- Handling no available slots
- Finding nearest available date
- Validating time_slot format
"""

import pytest
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.nodes.booking.select_time import (
    select_time,
    _format_time_slot,
    _format_time_for_display,
    _parse_time_selection,
    _find_nearest_available_date
)
from app.agent.state.conversation_state import ConversationState


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()
    return provider


@pytest.fixture
def mock_tools():
    """Create mock tools registry."""
    return {
        "get_available_slots": AsyncMock()
    }


@pytest.fixture
def base_state():
    """Create a base conversation state for testing."""
    return {
        "chat_id": "test-chat-123",
        "user_id": "user-456",
        "owner_profile_id": "owner-789",
        "user_message": "14:00",
        "flow_state": {
            "property_id": 1,
            "property_name": "Test Property",
            "court_id": 10,
            "court_name": "Court A",
            "date": "2024-12-25",
            "booking_step": "date_selected"
        },
        "bot_memory": {},
        "messages": [],
        "response_content": "",
        "response_type": "text",
        "response_metadata": {}
    }


@pytest.mark.asyncio
async def test_skip_when_time_slot_exists(base_state, mock_llm_provider, mock_tools):
    """Test that time selection is skipped when time_slot already exists (Requirement 7.4)."""
    # Add time_slot to flow_state
    base_state["flow_state"]["time_slot"] = "14:00-15:00"
    
    result = await select_time(base_state, mock_llm_provider, mock_tools)
    
    # Should skip to next step
    assert result["next_node"] == "confirm_booking"
    assert result["flow_state"]["time_slot"] == "14:00-15:00"


@pytest.mark.asyncio
async def test_error_when_no_date(base_state, mock_llm_provider, mock_tools):
    """Test error handling when date is not selected."""
    # Remove date from flow_state
    del base_state["flow_state"]["date"]
    
    result = await select_time(base_state, mock_llm_provider, mock_tools)
    
    # Should return error and route to select_date
    assert "select a date first" in result["response_content"].lower()
    assert result["next_node"] == "select_date"


@pytest.mark.asyncio
async def test_error_when_no_court(base_state, mock_llm_provider, mock_tools):
    """Test error handling when court is not selected."""
    # Remove court from flow_state
    del base_state["flow_state"]["court_id"]
    
    result = await select_time(base_state, mock_llm_provider, mock_tools)
    
    # Should return error and route to select_court
    assert "select a court first" in result["response_content"].lower()
    assert result["next_node"] == "select_court"


@pytest.mark.asyncio
async def test_present_time_options(base_state, mock_llm_provider, mock_tools):
    """Test presenting available time slots to user."""
    # Mock available slots
    mock_slots = [
        {
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "price_per_hour": 50.0,
            "label": "Morning Rate"
        },
        {
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "price_per_hour": 60.0,
            "label": "Afternoon Rate"
        }
    ]
    
    mock_tools["get_available_slots"].return_value = {
        "date": "2024-12-25",
        "court_id": 10,
        "court_name": "Court A",
        "available_slots": mock_slots
    }
    
    result = await select_time(base_state, mock_llm_provider, mock_tools)
    
    # Should present list of options
    assert result["response_type"] == "list"
    assert "list_items" in result["response_metadata"]
    assert len(result["response_metadata"]["list_items"]) == 2
    
    # Should update booking_step
    assert result["flow_state"]["booking_step"] == "awaiting_time_selection"
    
    # Should wait for selection
    assert result["next_node"] == "wait_for_selection"
    
    # Should store slots in bot_memory
    assert "slot_details" in result["bot_memory"]["context"]


@pytest.mark.asyncio
async def test_no_available_slots_suggests_alternative(base_state, mock_llm_provider, mock_tools):
    """Test that nearest available date is suggested when no slots available."""
    # Mock no slots for requested date
    mock_tools["get_available_slots"].return_value = {
        "date": "2024-12-25",
        "court_id": 10,
        "court_name": "Court A",
        "available_slots": []
    }
    
    # Mock slots available on next day
    async def mock_get_slots(court_id, date_val):
        if date_val == date(2024, 12, 25):
            return {"available_slots": []}
        elif date_val == date(2024, 12, 26):
            return {
                "available_slots": [
                    {"start_time": "09:00:00", "end_time": "10:00:00", "price_per_hour": 50.0}
                ]
            }
        return {"available_slots": []}
    
    mock_tools["get_available_slots"].side_effect = mock_get_slots
    
    result = await select_time(base_state, mock_llm_provider, mock_tools)
    
    # Should suggest alternative date
    assert "no available time slots" in result["response_content"].lower()
    assert "nearest available date" in result["response_content"].lower() or "different date" in result["response_content"].lower()
    
    # Should keep booking_step at date_selected to allow change
    assert result["flow_state"]["booking_step"] == "date_selected"


def test_format_time_slot():
    """Test time_slot formatting to HH:MM-HH:MM format (Requirement 8.5)."""
    # Test normal case
    result = _format_time_slot("14:00:00", "15:00:00")
    assert result == "14:00-15:00"
    
    # Test without seconds
    result = _format_time_slot("09:30", "10:30")
    assert result == "09:30-10:30"
    
    # Test edge case
    result = _format_time_slot("23:45:00", "00:45:00")
    assert result == "23:45-00:45"


def test_format_time_for_display():
    """Test time formatting for user-friendly display."""
    # Test afternoon time
    result = _format_time_for_display("14:00:00")
    assert result == "2:00 PM"
    
    # Test morning time
    result = _format_time_for_display("09:30:00")
    assert result == "9:30 AM"
    
    # Test noon
    result = _format_time_for_display("12:00:00")
    assert result == "12:00 PM"
    
    # Test midnight
    result = _format_time_for_display("00:00:00")
    assert result == "12:00 AM"


def test_parse_time_selection():
    """Test parsing user time selection from various formats."""
    available_slots = [
        {"start_time": "09:00:00", "end_time": "10:00:00", "price_per_hour": 50.0},
        {"start_time": "14:00:00", "end_time": "15:00:00", "price_per_hour": 60.0},
        {"start_time": "18:00:00", "end_time": "19:00:00", "price_per_hour": 70.0}
    ]
    
    # Test exact time match
    result = _parse_time_selection("14:00", available_slots)
    assert result is not None
    assert result["start_time"] == "14:00:00"
    
    # Test index selection
    result = _parse_time_selection("1", available_slots)
    assert result is not None
    assert result["start_time"] == "09:00:00"
    
    # Test word-based index
    result = _parse_time_selection("second", available_slots)
    assert result is not None
    assert result["start_time"] == "14:00:00"
    
    # Test PM format
    result = _parse_time_selection("2 pm", available_slots)
    assert result is not None
    assert result["start_time"] == "14:00:00"
    
    # Test invalid selection
    result = _parse_time_selection("25:00", available_slots)
    assert result is None


@pytest.mark.asyncio
async def test_find_nearest_available_date(mock_tools):
    """Test finding nearest available date."""
    start_date = date(2024, 12, 25)
    
    # Mock slots available on third day
    async def mock_get_slots(court_id, date_obj, chat_id):
        if date_obj == date(2024, 12, 28):
            return [{"start_time": "09:00:00", "end_time": "10:00:00"}]
        return []
    
    with patch('app.agent.nodes.booking.select_time._get_available_time_slots', side_effect=mock_get_slots):
        result = await _find_nearest_available_date(
            tools=mock_tools,
            court_id=10,
            start_date=start_date,
            chat_id="test-chat"
        )
        
        assert result == date(2024, 12, 28)


@pytest.mark.asyncio
async def test_process_time_selection_updates_flow_state(base_state, mock_llm_provider, mock_tools):
    """Test that time selection updates flow_state correctly (Requirement 8.2)."""
    # Set up state for processing selection
    base_state["flow_state"]["booking_step"] = "awaiting_time_selection"
    base_state["user_message"] = "14:00"
    
    # Mock slots in bot_memory
    base_state["bot_memory"]["context"] = {
        "slot_details": [
            {
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "price_per_hour": 60.0,
                "label": "Afternoon Rate"
            }
        ]
    }
    
    result = await select_time(base_state, mock_llm_provider, mock_tools)
    
    # Should store time_slot in correct format
    assert result["flow_state"]["time_slot"] == "14:00-15:00"
    
    # Should update booking_step (Requirement 8.2)
    assert result["flow_state"]["booking_step"] == "time_selected"
    
    # Should route to confirmation
    assert result["next_node"] == "confirm_booking"
    
    # Should store price
    assert result["flow_state"]["price"] == 60.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

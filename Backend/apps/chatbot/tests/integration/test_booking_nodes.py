"""
Integration tests for booking nodes.

This module tests complete booking flows through all booking nodes, including
property selection, service selection, date selection, time selection, and
confirmation. Tests use mocked LLM responses and tool calls for predictable behavior.

Requirements: Booking requirements
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Dict, Any
from contextlib import contextmanager
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

# Add Backend path for imports
backend_path = Path(__file__).parent.parent.parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import directly to avoid circular imports
import importlib.util
import os

# Load booking node modules directly
def load_booking_node(node_name):
    """Load a booking node module dynamically."""
    spec = importlib.util.spec_from_file_location(
        node_name,
        os.path.join(backend_path, "apps", "chatbot", "app", "agent", "nodes", "booking", f"{node_name}.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load all booking nodes
select_property_module = load_booking_node("select_property")
select_service_module = load_booking_node("select_service")
select_date_module = load_booking_node("select_date")
select_time_module = load_booking_node("select_time")
confirm_module = load_booking_node("confirm")

select_property = select_property_module.select_property
select_service = select_service_module.select_service
select_date = select_date_module.select_date
select_time = select_time_module.select_time
confirm_booking = confirm_module.confirm_booking

# Import ConversationState type for type hints
from typing import TypedDict, List, Dict, Any, Optional

class ConversationState(TypedDict):
    """State object for testing."""
    chat_id: str
    user_id: str
    owner_profile_id: str
    user_message: str
    flow_state: Dict[str, Any]
    bot_memory: Dict[str, Any]
    messages: List[Dict[str, str]]
    intent: Optional[str]
    response_content: str
    response_type: str
    response_metadata: Dict[str, Any]


# Fixtures for mock data

@pytest.fixture
def base_state() -> ConversationState:
    """Base conversation state for testing."""
    return {
        "chat_id": "test-chat-booking-123",
        "user_id": "1",
        "owner_profile_id": "1",
        "user_message": "",
        "flow_state": {"intent": "booking"},
        "bot_memory": {},
        "messages": [],
        "intent": "booking",
        "response_content": "",
        "response_type": "text",
        "response_metadata": {},
    }


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider for testing."""
    provider = MagicMock()
    provider.api_key = "test-api-key"
    provider.model = "gpt-4"
    provider.temperature = 0.7
    return provider


@pytest.fixture
def mock_properties():
    """Mock property data."""
    return [
        {
            "id": 1,
            "name": "Downtown Sports Center",
            "city": "New York",
            "address": "123 Main St"
        },
        {
            "id": 2,
            "name": "Uptown Tennis Club",
            "city": "New York",
            "address": "456 Park Ave"
        }
    ]


@pytest.fixture
def mock_courts():
    """Mock court data."""
    return [
        {
            "id": 10,
            "name": "Tennis Court A",
            "sport_type": "tennis",
            "surface": "hard"
        },
        {
            "id": 11,
            "name": "Tennis Court B",
            "sport_type": "tennis",
            "surface": "clay"
        }
    ]


@pytest.fixture
def mock_time_slots():
    """Mock available time slots."""
    return {
        "date": "2026-03-10",
        "court_id": 10,
        "court_name": "Tennis Court A",
        "available_slots": [
            {
                "start_time": "09:00:00",
                "end_time": "10:00:00",
                "price_per_hour": 50.0,
                "label": "Morning Rate"
            },
            {
                "start_time": "14:00:00",
                "end_time": "15:00:00",
                "price_per_hour": 75.0,
                "label": "Peak Rate"
            }
        ]
    }


@pytest.fixture
def mock_tools(mock_properties, mock_courts, mock_time_slots):
    """Mock tool registry with all booking tools."""
    async def mock_get_property_details(property_id, owner_id=None):
        for prop in mock_properties:
            if prop["id"] == property_id:
                return prop
        return None
    
    async def mock_get_property_courts(property_id, owner_id=None):
        if property_id == 1:
            return mock_courts
        return []
    
    async def mock_get_available_slots(court_id, date_val):
        if court_id == 10:
            return mock_time_slots
        return {"available_slots": []}
    
    async def mock_create_booking(customer_id, court_id, booking_date, start_time, end_time):
        return {
            "id": 100,
            "customer_id": customer_id,
            "court_id": court_id,
            "booking_date": booking_date,
            "start_time": start_time,
            "end_time": end_time,
            "status": "pending"
        }
    
    return {
        "get_property_details": mock_get_property_details,
        "get_property_courts": mock_get_property_courts,
        "get_available_slots": mock_get_available_slots,
        "create_booking": mock_create_booking,
    }


# Helper function to create mock LLM response

def create_mock_llm_response(content: str):
    """Create a mock LLM response object."""
    response = MagicMock()
    response.content = content
    return response


# Test 1: Complete booking flow from property selection to creation

@pytest.mark.asyncio
async def test_complete_booking_flow(
    base_state,
    mock_llm_provider,
    mock_tools,
    mock_properties,
    mock_courts,
    mock_time_slots
):
    """
    Test complete booking flow from property selection to creation.
    
    Flow:
    1. User starts booking -> Present property options
    2. User selects property -> Present court options
    3. User selects court -> Prompt for date
    4. User provides date -> Present time slots
    5. User selects time -> Present booking summary
    6. User confirms -> Booking created
    
    Requirements: Complete booking flow
    """
    # Step 1: Present property options
    state = base_state.copy()
    state["user_message"] = "I want to book a court"
    state["bot_memory"] = {
        "context": {
            "last_search_results": ["1", "2"]
        }
    }
    
    result = await select_property(state, mock_llm_provider, mock_tools)
    
    assert result["response_type"] == "button"
    assert "buttons" in result["response_metadata"]
    assert len(result["response_metadata"]["buttons"]) == 2
    assert result["flow_state"]["step"] == "select_property"
    
    # Step 2: User selects property
    state = result.copy()
    state["user_message"] = "Downtown Sports Center"
    
    # Mock LLM response for property selection
    with patch.object(select_property_module, 'create_langchain_llm') as mock_create_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=create_mock_llm_response("1"))
        mock_create_llm.return_value = mock_llm
        
        result = await select_property(state, mock_llm_provider, mock_tools)
    
    assert result["flow_state"]["property_id"] == "1"
    assert result["flow_state"]["property_name"] == "Downtown Sports Center"
    assert result["flow_state"]["step"] == "property_selected"
    
    # Step 3: Present court options
    state = result.copy()
    state["user_message"] = "Downtown Sports Center"
    
    result = await select_service(state, mock_llm_provider, mock_tools)
    
    assert result["response_type"] == "list"
    assert "list_items" in result["response_metadata"]
    assert len(result["response_metadata"]["list_items"]) == 2
    assert result["flow_state"]["step"] == "select_service"
    
    # Step 4: User selects court
    state = result.copy()
    state["user_message"] = "Tennis Court A"
    
    # Mock LLM response for service selection
    with patch.object(select_service_module, 'create_langchain_llm') as mock_create_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=create_mock_llm_response("10"))
        mock_create_llm.return_value = mock_llm
        
        result = await select_service(state, mock_llm_provider, mock_tools)
    
    assert result["flow_state"]["service_id"] == "10"
    assert result["flow_state"]["service_name"] == "Tennis Court A"
    assert result["flow_state"]["sport_type"] == "tennis"
    assert result["flow_state"]["step"] == "service_selected"
    
    # Step 5: Prompt for date
    state = result.copy()
    state["user_message"] = "Tennis Court A"
    
    result = await select_date(state, mock_llm_provider, mock_tools)
    
    assert result["response_type"] == "text"
    assert "when would you like" in result["response_content"].lower()
    assert result["flow_state"]["step"] == "select_date"
    
    # Step 6: User provides date
    state = result.copy()
    state["user_message"] = "tomorrow"
    
    # Mock LLM response for date selection
    tomorrow = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")
    with patch.object(select_date_module, 'create_langchain_llm') as mock_create_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=create_mock_llm_response(tomorrow))
        mock_create_llm.return_value = mock_llm
        
        result = await select_date(state, mock_llm_provider, mock_tools)
    
    assert result["flow_state"]["date"] == tomorrow
    assert result["flow_state"]["step"] == "date_selected"
    
    # Step 7: Present time slots
    state = result.copy()
    state["user_message"] = "tomorrow"
    
    result = await select_time(state, mock_llm_provider, mock_tools)
    
    assert result["response_type"] == "list"
    assert "list_items" in result["response_metadata"]
    assert len(result["response_metadata"]["list_items"]) == 2
    assert result["flow_state"]["step"] == "select_time"
    
    # Step 8: User selects time
    state = result.copy()
    state["user_message"] = "14:00"
    
    # Mock LLM response for time selection
    with patch.object(select_time_module, 'create_langchain_llm') as mock_create_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=create_mock_llm_response("14:00:00"))
        mock_create_llm.return_value = mock_llm
        
        result = await select_time(state, mock_llm_provider, mock_tools)
    
    assert result["flow_state"]["start_time"] == "14:00:00"
    assert result["flow_state"]["end_time"] == "15:00:00"
    assert result["flow_state"]["price"] == 75.0
    assert result["flow_state"]["step"] == "time_selected"
    
    # Step 9: Present booking summary
    state = result.copy()
    state["user_message"] = "14:00"
    
    result = await confirm_booking(state, mock_llm_provider, mock_tools)
    
    assert result["response_type"] == "text"
    assert "booking summary" in result["response_content"].lower()
    assert "downtown sports center" in result["response_content"].lower()
    assert "tennis court a" in result["response_content"].lower()
    assert result["flow_state"]["step"] == "confirm"
    
    # Step 10: User confirms
    state = result.copy()
    state["user_message"] = "yes, confirm"
    
    # Mock LLM response for confirmation
    with patch.object(confirm_module, 'create_langchain_llm') as mock_create_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=create_mock_llm_response("CONFIRM"))
        mock_create_llm.return_value = mock_llm
        
        result = await confirm_booking(state, mock_llm_provider, mock_tools)
    
    assert result["flow_state"]["step"] == "confirmed"
    assert "creating your booking" in result["response_content"].lower()


# Test 2: Back navigation between steps

@pytest.mark.asyncio
async def test_back_navigation_between_steps(
    base_state,
    mock_llm_provider,
    mock_tools
):
    """
    Test back navigation between booking steps.
    
    User should be able to go back and change selections at any step.
    
    Requirements: Back navigation support
    """
    # Setup: User has completed all selections and is at confirmation
    state = base_state.copy()
    state["flow_state"] = {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "sport_type": "tennis",
        "date": "2026-03-10",
        "start_time": "14:00:00",
        "end_time": "15:00:00",
        "price": 75.0,
        "step": "confirm"
    }
    state["user_message"] = "change date"
    
    # Mock LLM response for date change request
    with patch.object(confirm_module, 'create_langchain_llm') as mock_create_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=create_mock_llm_response("CHANGE_DATE"))
        mock_create_llm.return_value = mock_llm
        
        result = await confirm_booking(state, mock_llm_provider, mock_tools)
    
    # Verify user is taken back to date selection
    assert result["flow_state"]["step"] == "service_selected"
    assert "date" not in result["flow_state"]
    assert "start_time" not in result["flow_state"]
    assert "end_time" not in result["flow_state"]
    # Property and service should still be selected
    assert result["flow_state"]["property_id"] == "1"
    assert result["flow_state"]["service_id"] == "10"


# Test 3: Cancellation at different steps

@pytest.mark.asyncio
async def test_cancellation_at_different_steps(
    base_state,
    mock_llm_provider,
    mock_tools
):
    """
    Test cancellation at different steps in the booking flow.
    
    User should be able to cancel at any step and flow_state should be cleared.
    
    Requirements: Cancellation support
    """
    # Test cancellation at confirmation step
    state = base_state.copy()
    state["flow_state"] = {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "sport_type": "tennis",
        "date": "2026-03-10",
        "start_time": "14:00:00",
        "end_time": "15:00:00",
        "price": 75.0,
        "step": "confirm"
    }
    state["user_message"] = "cancel"
    
    # Mock LLM response for cancellation
    with patch.object(confirm_module, 'create_langchain_llm') as mock_create_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=create_mock_llm_response("CANCEL"))
        mock_create_llm.return_value = mock_llm
        
        result = await confirm_booking(state, mock_llm_provider, mock_tools)
    
    # Verify all booking fields are cleared
    assert result["flow_state"]["step"] == "cancelled"
    assert result["flow_state"]["intent"] is None
    assert "property_id" not in result["flow_state"]
    assert "service_id" not in result["flow_state"]
    assert "date" not in result["flow_state"]
    assert "start_time" not in result["flow_state"]
    assert "cancelled" in result["response_content"].lower()


# Test 4: Modification requests

@pytest.mark.asyncio
async def test_modification_requests(
    base_state,
    mock_llm_provider,
    mock_tools
):
    """
    Test modification requests at confirmation step.
    
    User should be able to request changes to specific fields.
    
    Requirements: Modification support
    """
    # Test changing property
    state = base_state.copy()
    state["flow_state"] = {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "sport_type": "tennis",
        "date": "2026-03-10",
        "start_time": "14:00:00",
        "end_time": "15:00:00",
        "price": 75.0,
        "step": "confirm"
    }
    state["user_message"] = "change property"
    
    # Mock LLM response for property change
    with patch.object(confirm_module, 'create_langchain_llm') as mock_create_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=create_mock_llm_response("CHANGE_PROPERTY"))
        mock_create_llm.return_value = mock_llm
        
        result = await confirm_booking(state, mock_llm_provider, mock_tools)
    
    # Verify user is taken back to property selection
    assert result["flow_state"]["step"] == "select_property"
    assert "property_id" not in result["flow_state"]
    assert "service_id" not in result["flow_state"]
    assert "date" not in result["flow_state"]
    
    # Test changing court
    state = base_state.copy()
    state["flow_state"] = {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "sport_type": "tennis",
        "date": "2026-03-10",
        "start_time": "14:00:00",
        "end_time": "15:00:00",
        "price": 75.0,
        "step": "confirm"
    }
    state["user_message"] = "change court"
    
    # Mock LLM response for service change
    with patch.object(confirm_module, 'create_langchain_llm') as mock_create_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=create_mock_llm_response("CHANGE_SERVICE"))
        mock_create_llm.return_value = mock_llm
        
        result = await confirm_booking(state, mock_llm_provider, mock_tools)
    
    # Verify user is taken back to service selection
    assert result["flow_state"]["step"] == "property_selected"
    assert result["flow_state"]["property_id"] == "1"  # Property still selected
    assert "service_id" not in result["flow_state"]
    assert "date" not in result["flow_state"]
    
    # Test changing time
    state = base_state.copy()
    state["flow_state"] = {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "service_id": "10",
        "service_name": "Tennis Court A",
        "sport_type": "tennis",
        "date": "2026-03-10",
        "start_time": "14:00:00",
        "end_time": "15:00:00",
        "price": 75.0,
        "step": "confirm"
    }
    state["user_message"] = "change time"
    
    # Mock LLM response for time change
    with patch.object(confirm_module, 'create_langchain_llm') as mock_create_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=create_mock_llm_response("CHANGE_TIME"))
        mock_create_llm.return_value = mock_llm
        
        result = await confirm_booking(state, mock_llm_provider, mock_tools)
    
    # Verify user is taken back to time selection
    assert result["flow_state"]["step"] == "date_selected"
    assert result["flow_state"]["property_id"] == "1"
    assert result["flow_state"]["service_id"] == "10"
    assert result["flow_state"]["date"] == "2026-03-10"  # Date still selected
    assert "start_time" not in result["flow_state"]


# Test 5: Property selection with no search results

@pytest.mark.asyncio
async def test_property_selection_no_search_results(
    base_state,
    mock_llm_provider,
    mock_tools
):
    """
    Test property selection when user has no previous search results.
    
    Should prompt user to search first.
    
    Requirements: Property selection validation
    """
    state = base_state.copy()
    state["user_message"] = "I want to book a court"
    state["bot_memory"] = {}  # No search results
    
    result = await select_property(state, mock_llm_provider, mock_tools)
    
    assert result["response_type"] == "text"
    assert "search" in result["response_content"].lower()
    assert result["flow_state"]["step"] == "awaiting_search"


# Test 6: Service selection with no courts available

@pytest.mark.asyncio
async def test_service_selection_no_courts(
    base_state,
    mock_llm_provider,
    mock_tools
):
    """
    Test service selection when property has no courts.
    
    Should inform user and offer to select different property.
    
    Requirements: Service selection validation
    """
    state = base_state.copy()
    state["user_message"] = "Downtown Sports Center"
    state["flow_state"] = {
        "intent": "booking",
        "property_id": "999",  # Property with no courts
        "property_name": "Empty Facility",
        "step": "property_selected"
    }
    
    result = await select_service(state, mock_llm_provider, mock_tools)
    
    assert result["response_type"] == "text"
    assert "no courts" in result["response_content"].lower() or "couldn't find" in result["response_content"].lower()


# Test 7: Date selection with past date

@pytest.mark.asyncio
async def test_date_selection_past_date(
    base_state,
    mock_llm_provider,
    mock_tools
):
    """
    Test date selection when user provides a past date.
    
    Should reject past date and ask for future date.
    
    Requirements: Date validation
    """
    state = base_state.copy()
    state["user_message"] = "yesterday"
    state["flow_state"] = {
        "intent": "booking",
        "property_id": "1",
        "service_id": "10",
        "step": "select_date"
    }
    
    # Mock LLM response with past date
    yesterday = (datetime.now().date() - timedelta(days=1)).strftime("%Y-%m-%d")
    with patch.object(select_date_module, 'create_langchain_llm') as mock_create_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=create_mock_llm_response(yesterday))
        mock_create_llm.return_value = mock_llm
        
        result = await select_date(state, mock_llm_provider, mock_tools)
    
    assert result["response_type"] == "text"
    assert "past" in result["response_content"].lower()
    assert result["flow_state"]["step"] == "select_date"  # Stay on same step
    assert "date" not in result["flow_state"]  # Date not stored


# Test 8: Time selection with no available slots

@pytest.mark.asyncio
async def test_time_selection_no_slots(
    base_state,
    mock_llm_provider,
    mock_tools
):
    """
    Test time selection when no slots are available for the date.
    
    Should inform user and suggest trying different date.
    
    Requirements: Time slot availability validation
    """
    state = base_state.copy()
    state["user_message"] = "2026-03-10"
    state["flow_state"] = {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        "service_id": "999",  # Court with no available slots
        "service_name": "Busy Court",
        "date": "2026-03-10",
        "step": "date_selected"
    }
    
    result = await select_time(state, mock_llm_provider, mock_tools)
    
    assert result["response_type"] == "text"
    assert "no available" in result["response_content"].lower() or "sorry" in result["response_content"].lower()
    assert result["flow_state"]["step"] == "date_selected"  # Allow date change


# Test 9: Confirmation with missing booking details

@pytest.mark.asyncio
async def test_confirmation_missing_details(
    base_state,
    mock_llm_provider,
    mock_tools
):
    """
    Test confirmation when some booking details are missing.
    
    Should detect missing fields and restart booking flow.
    
    Requirements: Booking validation
    """
    state = base_state.copy()
    state["user_message"] = "confirm"
    state["flow_state"] = {
        "intent": "booking",
        "property_id": "1",
        "property_name": "Downtown Sports Center",
        # Missing service_id, date, time, etc.
        "step": "time_selected"
    }
    
    result = await confirm_booking(state, mock_llm_provider, mock_tools)
    
    assert result["response_type"] == "text"
    assert "missing" in result["response_content"].lower() or "start over" in result["response_content"].lower()
    assert result["flow_state"]["step"] == "select_property"


# Test 10: Manual parsing fallback when LLM fails

@pytest.mark.asyncio
async def test_manual_parsing_fallback(
    base_state,
    mock_llm_provider,
    mock_tools,
    mock_properties
):
    """
    Test manual parsing fallback when LLM creation fails.
    
    Should still be able to parse user selections using manual parsing.
    
    Requirements: Error handling and fallback
    """
    # Test property selection fallback
    state = base_state.copy()
    state["user_message"] = "Downtown Sports Center"
    state["flow_state"] = {"intent": "booking", "step": "select_property"}
    state["bot_memory"] = {
        "context": {
            "property_details": mock_properties
        }
    }
    
    # Mock LLM creation to fail
    with patch.object(select_property_module, 'create_langchain_llm', side_effect=Exception("LLM creation failed")):
        result = await select_property(state, mock_llm_provider, mock_tools)
    
    # Should still successfully parse the selection using manual parsing
    assert result["flow_state"]["property_id"] == "1"
    assert result["flow_state"]["property_name"] == "Downtown Sports Center"
    assert result["flow_state"]["step"] == "property_selected"

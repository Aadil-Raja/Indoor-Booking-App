"""
Unit tests for select_service node.

This module tests the select_service node functionality including:
- Presenting court options as list items with sport type information
- Parsing user selection (court ID or court name)
- Storing selected service_id in flow_state
- Handling invalid selections
- Handling missing property selection
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

from .select_service import (
    select_service,
    _format_courts_as_list,
    _parse_court_selection,
    _store_court_details_in_memory,
)
from ...state.conversation_state import ConversationState


# Test data
SAMPLE_COURTS = [
    {
        "id": 10,
        "name": "Tennis Court A",
        "sport_type": "tennis",
        "property_id": 1
    },
    {
        "id": 11,
        "name": "Tennis Court B",
        "sport_type": "tennis",
        "property_id": 1
    },
    {
        "id": 12,
        "name": "Basketball Court",
        "sport_type": "basketball",
        "property_id": 1
    }
]


@pytest.fixture
def mock_tools():
    """Create mock tools for testing."""
    async def mock_get_property_courts(property_id: int, owner_id=None):
        # Return courts for property_id 1
        if property_id == 1:
            return SAMPLE_COURTS
        return []
    
    return {
        "get_property_courts": mock_get_property_courts
    }


@pytest.fixture
def base_state() -> Dict[str, Any]:
    """Create a base conversation state for testing."""
    return {
        "chat_id": "test-chat-123",
        "user_id": "test-user-456",
        "owner_id": "test-owner-789",
        "user_message": "",
        "flow_state": {
            "intent": "booking",
            "property_id": "1",
            "property_name": "Downtown Sports Center"
        },
        "bot_memory": {},
        "messages": [],
        "intent": "booking",
        "response_content": "",
        "response_type": "text",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }


class TestSelectService:
    """Test suite for select_service node."""
    
    @pytest.mark.asyncio
    async def test_present_options_with_property_selected(
        self, base_state, mock_tools
    ):
        """Test presenting court options when property is selected."""
        base_state["user_message"] = "Downtown Sports Center"
        
        # Call select_service
        result = await select_service(base_state, mock_tools)
        
        # Verify response type is list
        assert result["response_type"] == "list"
        
        # Verify list items are present
        assert "list_items" in result["response_metadata"]
        list_items = result["response_metadata"]["list_items"]
        assert len(list_items) == 3
        
        # Verify list item format
        assert list_items[0]["id"] == "10"
        assert list_items[0]["title"] == "Tennis Court A"
        assert list_items[0]["description"] == "Sport: tennis"
        
        # Verify flow state updated
        assert result["flow_state"]["step"] == "select_service"
        
        # Verify court details stored in bot_memory
        assert "court_details" in result["bot_memory"]["context"]
        assert len(result["bot_memory"]["context"]["court_details"]) == 3
    
    @pytest.mark.asyncio
    async def test_present_options_no_property_selected(
        self, base_state, mock_tools
    ):
        """Test error handling when no property is selected."""
        # Remove property_id from flow_state
        base_state["flow_state"] = {"intent": "booking"}
        base_state["user_message"] = "I want to book a court"
        
        # Call select_service
        result = await select_service(base_state, mock_tools)
        
        # Verify error message
        assert result["response_type"] == "text"
        assert "select a facility first" in result["response_content"].lower()
    
    @pytest.mark.asyncio
    async def test_present_options_no_courts_available(
        self, base_state, mock_tools
    ):
        """Test handling when no courts are available for property."""
        # Set property_id to one with no courts
        base_state["flow_state"]["property_id"] = "999"
        base_state["user_message"] = "Show me courts"
        
        # Call select_service
        result = await select_service(base_state, mock_tools)
        
        # Verify error message
        assert result["response_type"] == "text"
        assert "couldn't find any courts" in result["response_content"].lower()
    
    @pytest.mark.asyncio
    async def test_process_selection_by_court_name(
        self, base_state, mock_tools
    ):
        """Test processing court selection by court name."""
        # Setup state with court details in bot_memory
        base_state["flow_state"]["step"] = "select_service"
        base_state["bot_memory"] = {
            "context": {
                "court_details": SAMPLE_COURTS
            }
        }
        base_state["user_message"] = "Tennis Court A"
        
        # Call select_service
        result = await select_service(base_state, mock_tools)
        
        # Verify service_id stored in flow_state
        assert result["flow_state"]["service_id"] == "10"
        assert result["flow_state"]["service_name"] == "Tennis Court A"
        assert result["flow_state"]["sport_type"] == "tennis"
        assert result["flow_state"]["step"] == "service_selected"
        
        # Verify confirmation message
        assert "Tennis Court A" in result["response_content"]
        assert "tennis" in result["response_content"]
    
    @pytest.mark.asyncio
    async def test_process_selection_by_court_id(
        self, base_state, mock_tools
    ):
        """Test processing court selection by court ID."""
        # Setup state with court details in bot_memory
        base_state["flow_state"]["step"] = "select_service"
        base_state["bot_memory"] = {
            "context": {
                "court_details": SAMPLE_COURTS
            }
        }
        base_state["user_message"] = "12"
        
        # Call select_service
        result = await select_service(base_state, mock_tools)
        
        # Verify service_id stored in flow_state
        assert result["flow_state"]["service_id"] == "12"
        assert result["flow_state"]["service_name"] == "Basketball Court"
        assert result["flow_state"]["sport_type"] == "basketball"
    
    @pytest.mark.asyncio
    async def test_process_selection_by_sport_type(
        self, base_state, mock_tools
    ):
        """Test processing court selection by sport type when only one court of that type."""
        # Setup state with only basketball court
        base_state["flow_state"]["step"] = "select_service"
        base_state["bot_memory"] = {
            "context": {
                "court_details": SAMPLE_COURTS
            }
        }
        base_state["user_message"] = "basketball"
        
        # Call select_service
        result = await select_service(base_state, mock_tools)
        
        # Verify basketball court selected
        assert result["flow_state"]["service_id"] == "12"
        assert result["flow_state"]["sport_type"] == "basketball"
    
    @pytest.mark.asyncio
    async def test_process_selection_invalid(
        self, base_state, mock_tools
    ):
        """Test handling invalid court selection."""
        # Setup state with court details in bot_memory
        base_state["flow_state"]["step"] = "select_service"
        base_state["bot_memory"] = {
            "context": {
                "court_details": SAMPLE_COURTS
            }
        }
        base_state["user_message"] = "Nonexistent Court"
        
        # Call select_service
        result = await select_service(base_state, mock_tools)
        
        # Verify error message
        assert result["response_type"] == "text"
        assert "couldn't find that court" in result["response_content"].lower()
        
        # Verify step remains select_service for retry
        assert result["flow_state"]["step"] == "select_service"
        
        # Verify service_id not set
        assert "service_id" not in result["flow_state"]
    
    @pytest.mark.asyncio
    async def test_service_already_selected(
        self, base_state, mock_tools
    ):
        """Test that node returns immediately if service already selected."""
        # Setup state with service already selected
        base_state["flow_state"]["service_id"] = "10"
        base_state["user_message"] = "Some message"
        
        # Call select_service
        result = await select_service(base_state, mock_tools)
        
        # Verify state unchanged (returns immediately)
        assert result["flow_state"]["service_id"] == "10"


class TestFormatCourtsAsList:
    """Test suite for _format_courts_as_list function."""
    
    def test_format_courts_as_list(self):
        """Test formatting courts as list items."""
        list_items = _format_courts_as_list(SAMPLE_COURTS)
        
        # Verify correct number of items
        assert len(list_items) == 3
        
        # Verify first item format
        assert list_items[0]["id"] == "10"
        assert list_items[0]["title"] == "Tennis Court A"
        assert list_items[0]["description"] == "Sport: tennis"
        
        # Verify second item format
        assert list_items[1]["id"] == "11"
        assert list_items[1]["title"] == "Tennis Court B"
        assert list_items[1]["description"] == "Sport: tennis"
    
    def test_format_courts_empty_list(self):
        """Test formatting empty court list."""
        list_items = _format_courts_as_list([])
        
        # Verify empty list returned
        assert list_items == []
    
    def test_format_courts_missing_fields(self):
        """Test formatting courts with missing fields."""
        courts = [
            {"id": 1},  # Missing name and sport_type
            {"id": 2, "name": "Court B"}  # Missing sport_type
        ]
        
        list_items = _format_courts_as_list(courts)
        
        # Verify defaults used for missing fields
        assert list_items[0]["title"] == "Unknown Court"
        assert list_items[0]["description"] == "Sport: Unknown"
        assert list_items[1]["title"] == "Court B"
        assert list_items[1]["description"] == "Sport: Unknown"


class TestParseCourtSelection:
    """Test suite for _parse_court_selection function."""
    
    def test_parse_by_exact_id(self):
        """Test parsing court selection by exact ID."""
        court = _parse_court_selection("10", SAMPLE_COURTS)
        
        assert court is not None
        assert court["id"] == 10
        assert court["name"] == "Tennis Court A"
    
    def test_parse_by_id_in_sentence(self):
        """Test parsing court selection with ID in sentence."""
        court = _parse_court_selection("I want court 11", SAMPLE_COURTS)
        
        assert court is not None
        assert court["id"] == 11
    
    def test_parse_by_exact_name(self):
        """Test parsing court selection by exact name."""
        court = _parse_court_selection("Tennis Court A", SAMPLE_COURTS)
        
        assert court is not None
        assert court["id"] == 10
    
    def test_parse_by_exact_name_case_insensitive(self):
        """Test parsing court selection by name (case insensitive)."""
        court = _parse_court_selection("tennis court a", SAMPLE_COURTS)
        
        assert court is not None
        assert court["id"] == 10
    
    def test_parse_by_partial_name(self):
        """Test parsing court selection by partial name."""
        court = _parse_court_selection("Basketball", SAMPLE_COURTS)
        
        assert court is not None
        assert court["id"] == 12
    
    def test_parse_by_sport_type_single_match(self):
        """Test parsing by sport type when only one court of that type."""
        court = _parse_court_selection("basketball", SAMPLE_COURTS)
        
        assert court is not None
        assert court["id"] == 12
    
    def test_parse_by_sport_type_multiple_matches(self):
        """Test parsing by sport type when multiple courts of that type."""
        # Tennis has 2 courts, so should not match by sport type alone
        court = _parse_court_selection("tennis", SAMPLE_COURTS)
        
        # Should still match by word overlap
        assert court is not None
        # Should match one of the tennis courts
        assert court["sport_type"] == "tennis"
    
    def test_parse_by_word_overlap(self):
        """Test parsing by word overlap with at least 2 matching words."""
        court = _parse_court_selection("Tennis Court", SAMPLE_COURTS)
        
        assert court is not None
        assert "Tennis Court" in court["name"]
    
    def test_parse_invalid_selection(self):
        """Test parsing invalid court selection."""
        court = _parse_court_selection("Nonexistent Court", SAMPLE_COURTS)
        
        assert court is None
    
    def test_parse_empty_message(self):
        """Test parsing empty message."""
        court = _parse_court_selection("", SAMPLE_COURTS)
        
        assert court is None
    
    def test_parse_whitespace_only(self):
        """Test parsing whitespace-only message."""
        court = _parse_court_selection("   ", SAMPLE_COURTS)
        
        assert court is None


class TestStoreCourtDetailsInMemory:
    """Test suite for _store_court_details_in_memory function."""
    
    def test_store_court_details_empty_memory(self):
        """Test storing court details in empty bot_memory."""
        bot_memory = {}
        
        result = _store_court_details_in_memory(bot_memory, SAMPLE_COURTS)
        
        # Verify context created
        assert "context" in result
        assert "court_details" in result["context"]
        assert result["context"]["court_details"] == SAMPLE_COURTS
    
    def test_store_court_details_existing_context(self):
        """Test storing court details in bot_memory with existing context."""
        bot_memory = {
            "context": {
                "existing_key": "existing_value"
            }
        }
        
        result = _store_court_details_in_memory(bot_memory, SAMPLE_COURTS)
        
        # Verify existing context preserved
        assert result["context"]["existing_key"] == "existing_value"
        
        # Verify court details added
        assert "court_details" in result["context"]
        assert result["context"]["court_details"] == SAMPLE_COURTS
    
    def test_store_court_details_overwrites_existing(self):
        """Test that storing court details overwrites existing court_details."""
        bot_memory = {
            "context": {
                "court_details": [{"id": 999, "name": "Old Court"}]
            }
        }
        
        result = _store_court_details_in_memory(bot_memory, SAMPLE_COURTS)
        
        # Verify court details overwritten
        assert result["context"]["court_details"] == SAMPLE_COURTS
        assert len(result["context"]["court_details"]) == 3

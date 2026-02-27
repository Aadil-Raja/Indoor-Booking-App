"""
Unit tests for select_property node.

This module tests the select_property node functionality including:
- Presenting property options as buttons
- Parsing user selection (property ID or property name)
- Storing selected property_id in flow_state
- Handling invalid selections
- Handling missing search results
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

from .select_property import (
    select_property,
    _format_properties_as_buttons,
    _parse_property_selection,
    _store_property_details_in_memory,
)
from ...state.conversation_state import ConversationState


# Test data
SAMPLE_PROPERTIES = [
    {
        "id": 1,
        "name": "Downtown Sports Center",
        "city": "New York",
        "address": "123 Main St"
    },
    {
        "id": 2,
        "name": "Westside Arena",
        "city": "Los Angeles",
        "address": "456 West Ave"
    },
    {
        "id": 3,
        "name": "Eastside Tennis Club",
        "city": "Boston",
        "address": "789 East Blvd"
    }
]


@pytest.fixture
def mock_tools():
    """Create mock tools for testing."""
    async def mock_get_property_details(property_id: int, owner_id=None):
        # Return property from SAMPLE_PROPERTIES if it exists
        for prop in SAMPLE_PROPERTIES:
            if prop["id"] == property_id:
                return prop
        return None
    
    return {
        "get_property_details": mock_get_property_details
    }


@pytest.fixture
def base_state() -> Dict[str, Any]:
    """Create a base conversation state for testing."""
    return {
        "chat_id": "test-chat-123",
        "user_id": "test-user-456",
        "owner_id": "test-owner-789",
        "user_message": "",
        "flow_state": {"intent": "booking"},
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


class TestSelectProperty:
    """Test suite for select_property node."""
    
    @pytest.mark.asyncio
    async def test_present_options_with_search_results(
        self, base_state, mock_tools
    ):
        """Test presenting property options when search results exist."""
        # Setup state with search results
        base_state["bot_memory"] = {
            "context": {
                "last_search_results": ["1", "2", "3"]
            }
        }
        base_state["user_message"] = "I want to book a court"
        
        # Execute node
        result = await select_property(base_state, tools=mock_tools)
        
        # Verify response
        assert result["response_type"] == "button"
        assert "buttons" in result["response_metadata"]
        assert len(result["response_metadata"]["buttons"]) == 3
        assert result["flow_state"]["step"] == "select_property"
        
        # Verify buttons contain property names
        button_texts = [b["text"] for b in result["response_metadata"]["buttons"]]
        assert "Downtown Sports Center" in button_texts
        assert "Westside Arena" in button_texts
        assert "Eastside Tennis Club" in button_texts
    
    @pytest.mark.asyncio
    async def test_present_options_without_search_results(
        self, base_state, mock_tools
    ):
        """Test presenting options when no search results exist."""
        # Setup state without search results
        base_state["user_message"] = "I want to book a court"
        
        # Execute node
        result = await select_property(base_state, tools=mock_tools)
        
        # Verify response prompts user to search
        assert result["response_type"] == "text"
        assert "search" in result["response_content"].lower()
        assert result["flow_state"]["step"] == "awaiting_search"
    
    @pytest.mark.asyncio
    async def test_process_selection_by_property_id(
        self, base_state, mock_tools
    ):
        """Test processing property selection by property ID."""
        # Setup state with property details and user selection
        base_state["flow_state"]["step"] = "select_property"
        base_state["bot_memory"] = {
            "context": {
                "property_details": SAMPLE_PROPERTIES
            }
        }
        base_state["user_message"] = "1"
        
        # Execute node
        result = await select_property(base_state, tools=mock_tools)
        
        # Verify property was selected
        assert result["flow_state"]["property_id"] == "1"
        assert result["flow_state"]["property_name"] == "Downtown Sports Center"
        assert result["flow_state"]["step"] == "property_selected"
        assert "Downtown Sports Center" in result["response_content"]
    
    @pytest.mark.asyncio
    async def test_process_selection_by_property_name(
        self, base_state, mock_tools
    ):
        """Test processing property selection by property name."""
        # Setup state with property details and user selection
        base_state["flow_state"]["step"] = "select_property"
        base_state["bot_memory"] = {
            "context": {
                "property_details": SAMPLE_PROPERTIES
            }
        }
        base_state["user_message"] = "Westside Arena"
        
        # Execute node
        result = await select_property(base_state, tools=mock_tools)
        
        # Verify property was selected
        assert result["flow_state"]["property_id"] == "2"
        assert result["flow_state"]["property_name"] == "Westside Arena"
        assert result["flow_state"]["step"] == "property_selected"
    
    @pytest.mark.asyncio
    async def test_process_selection_by_partial_name(
        self, base_state, mock_tools
    ):
        """Test processing property selection by partial name match."""
        # Setup state with property details and user selection
        base_state["flow_state"]["step"] = "select_property"
        base_state["bot_memory"] = {
            "context": {
                "property_details": SAMPLE_PROPERTIES
            }
        }
        base_state["user_message"] = "Eastside Tennis"
        
        # Execute node
        result = await select_property(base_state, tools=mock_tools)
        
        # Verify property was selected
        assert result["flow_state"]["property_id"] == "3"
        assert result["flow_state"]["property_name"] == "Eastside Tennis Club"
        assert result["flow_state"]["step"] == "property_selected"
    
    @pytest.mark.asyncio
    async def test_process_invalid_selection(
        self, base_state, mock_tools
    ):
        """Test handling invalid property selection."""
        # Setup state with property details and invalid selection
        base_state["flow_state"]["step"] = "select_property"
        base_state["bot_memory"] = {
            "context": {
                "property_details": SAMPLE_PROPERTIES
            }
        }
        base_state["user_message"] = "Nonexistent Property"
        
        # Execute node
        result = await select_property(base_state, tools=mock_tools)
        
        # Verify error handling
        assert "property_id" not in result["flow_state"]
        assert result["flow_state"]["step"] == "select_property"
        assert "couldn't find" in result["response_content"].lower()
        assert result["response_type"] == "text"
    
    @pytest.mark.asyncio
    async def test_skip_if_property_already_selected(
        self, base_state, mock_tools
    ):
        """Test that node skips if property is already selected."""
        # Setup state with property already selected
        base_state["flow_state"]["property_id"] = "1"
        base_state["flow_state"]["property_name"] = "Downtown Sports Center"
        base_state["user_message"] = "Some message"
        
        # Execute node
        result = await select_property(base_state, tools=mock_tools)
        
        # Verify node returns state unchanged
        assert result["flow_state"]["property_id"] == "1"
        assert result["flow_state"]["property_name"] == "Downtown Sports Center"


class TestFormatPropertiesAsButtons:
    """Test suite for _format_properties_as_buttons function."""
    
    def test_format_single_property(self):
        """Test formatting a single property as button."""
        properties = [SAMPLE_PROPERTIES[0]]
        
        buttons = _format_properties_as_buttons(properties)
        
        assert len(buttons) == 1
        assert buttons[0]["id"] == "1"
        assert buttons[0]["text"] == "Downtown Sports Center"
    
    def test_format_multiple_properties(self):
        """Test formatting multiple properties as buttons."""
        buttons = _format_properties_as_buttons(SAMPLE_PROPERTIES)
        
        assert len(buttons) == 3
        assert buttons[0]["id"] == "1"
        assert buttons[0]["text"] == "Downtown Sports Center"
        assert buttons[1]["id"] == "2"
        assert buttons[1]["text"] == "Westside Arena"
        assert buttons[2]["id"] == "3"
        assert buttons[2]["text"] == "Eastside Tennis Club"
    
    def test_format_empty_list(self):
        """Test formatting empty property list."""
        buttons = _format_properties_as_buttons([])
        
        assert buttons == []
    
    def test_format_property_without_name(self):
        """Test formatting property without name field."""
        properties = [{"id": 99}]
        
        buttons = _format_properties_as_buttons(properties)
        
        assert len(buttons) == 1
        assert buttons[0]["id"] == "99"
        assert buttons[0]["text"] == "Unknown Property"


class TestParsePropertySelection:
    """Test suite for _parse_property_selection function."""
    
    def test_parse_by_exact_id(self):
        """Test parsing selection by exact property ID."""
        result = _parse_property_selection("1", SAMPLE_PROPERTIES)
        
        assert result is not None
        assert result["id"] == 1
        assert result["name"] == "Downtown Sports Center"
    
    def test_parse_by_id_in_sentence(self):
        """Test parsing selection with ID embedded in sentence."""
        result = _parse_property_selection(
            "I want property 2 please",
            SAMPLE_PROPERTIES
        )
        
        assert result is not None
        assert result["id"] == 2
        assert result["name"] == "Westside Arena"
    
    def test_parse_by_exact_name(self):
        """Test parsing selection by exact property name."""
        result = _parse_property_selection(
            "Downtown Sports Center",
            SAMPLE_PROPERTIES
        )
        
        assert result is not None
        assert result["id"] == 1
    
    def test_parse_by_exact_name_case_insensitive(self):
        """Test parsing selection by name with different case."""
        result = _parse_property_selection(
            "downtown sports center",
            SAMPLE_PROPERTIES
        )
        
        assert result is not None
        assert result["id"] == 1
    
    def test_parse_by_partial_name(self):
        """Test parsing selection by partial property name."""
        result = _parse_property_selection(
            "Eastside Tennis",
            SAMPLE_PROPERTIES
        )
        
        assert result is not None
        assert result["id"] == 3
    
    def test_parse_by_word_overlap(self):
        """Test parsing selection by word overlap."""
        result = _parse_property_selection(
            "Tennis Club",
            SAMPLE_PROPERTIES
        )
        
        assert result is not None
        assert result["id"] == 3
        assert "Tennis" in result["name"]
    
    def test_parse_invalid_selection(self):
        """Test parsing invalid selection returns None."""
        result = _parse_property_selection(
            "Nonexistent Property",
            SAMPLE_PROPERTIES
        )
        
        assert result is None
    
    def test_parse_empty_message(self):
        """Test parsing empty message returns None."""
        result = _parse_property_selection("", SAMPLE_PROPERTIES)
        
        assert result is None


class TestStorePropertyDetailsInMemory:
    """Test suite for _store_property_details_in_memory function."""
    
    def test_store_in_empty_memory(self):
        """Test storing property details in empty bot_memory."""
        bot_memory = {}
        
        result = _store_property_details_in_memory(
            bot_memory=bot_memory,
            properties=SAMPLE_PROPERTIES
        )
        
        assert "context" in result
        assert "property_details" in result["context"]
        assert result["context"]["property_details"] == SAMPLE_PROPERTIES
    
    def test_store_in_existing_memory(self):
        """Test storing property details in existing bot_memory."""
        bot_memory = {
            "context": {
                "last_search_results": ["1", "2", "3"]
            },
            "user_preferences": {
                "preferred_sport": "tennis"
            }
        }
        
        result = _store_property_details_in_memory(
            bot_memory=bot_memory,
            properties=SAMPLE_PROPERTIES
        )
        
        # Verify property details added without overwriting existing data
        assert result["context"]["property_details"] == SAMPLE_PROPERTIES
        assert result["context"]["last_search_results"] == ["1", "2", "3"]
        assert result["user_preferences"]["preferred_sport"] == "tennis"
    
    def test_store_overwrites_existing_property_details(self):
        """Test that storing new property details overwrites old ones."""
        bot_memory = {
            "context": {
                "property_details": [{"id": 99, "name": "Old Property"}]
            }
        }
        
        result = _store_property_details_in_memory(
            bot_memory=bot_memory,
            properties=SAMPLE_PROPERTIES
        )
        
        assert result["context"]["property_details"] == SAMPLE_PROPERTIES
        assert len(result["context"]["property_details"]) == 3

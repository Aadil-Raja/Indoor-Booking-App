"""
Unit tests for select_court node.

This module tests the select_court node functionality including:
- Skipping when court already selected
- Auto-selecting single court
- Presenting multiple court options
- Handling no courts available
- Handling missing property_id
"""

import pytest
from unittest.mock import AsyncMock, patch
from typing import Dict, Any

from .select_court import select_court
from ...state.conversation_state import ConversationState


# Test data
SAMPLE_COURTS = [
    {
        "id": 1,
        "name": "Court A",
        "sport_type": "Tennis",
        "surface_type": "Hard",
        "is_indoor": True
    },
    {
        "id": 2,
        "name": "Court B",
        "sport_type": "Basketball",
        "surface_type": "Wood",
        "is_indoor": True
    },
    {
        "id": 3,
        "name": "Court C",
        "sport_type": "Futsal",
        "surface_type": "Turf",
        "is_indoor": False
    }
]


@pytest.fixture
def mock_tools():
    """Create mock tools for testing."""
    return {}


@pytest.fixture
def base_state() -> Dict[str, Any]:
    """Create a base conversation state for testing."""
    return {
        "chat_id": "test-chat-123",
        "user_id": "test-user-456",
        "owner_profile_id": "789",
        "user_message": "",
        "flow_state": {
            "current_intent": "booking",
            "property_id": 1,
            "property_name": "Sports Center"
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


class TestSelectCourt:
    """Test suite for select_court node."""
    
    @pytest.mark.asyncio
    async def test_skip_if_court_already_selected(self, base_state, mock_tools):
        """Test that node skips if court is already selected (Requirement 7.2)."""
        # Setup state with court already selected
        base_state["flow_state"]["court_id"] = 1
        base_state["flow_state"]["court_name"] = "Court A"
        
        # Execute node
        result = await select_court(base_state, tools=mock_tools)
        
        # Verify node skips to next step
        assert result["next_node"] == "select_date"
        assert result["flow_state"]["court_id"] == 1
        assert result["flow_state"]["court_name"] == "Court A"
    
    @pytest.mark.asyncio
    async def test_error_when_no_property_selected(self, base_state, mock_tools):
        """Test error handling when property_id is missing."""
        # Setup state without property_id
        base_state["flow_state"] = {"current_intent": "booking"}
        
        # Execute node
        result = await select_court(base_state, tools=mock_tools)
        
        # Verify error response
        assert result["response_type"] == "text"
        assert "select a property first" in result["response_content"].lower()
        assert result["next_node"] == "select_property"
    
    @pytest.mark.asyncio
    async def test_auto_select_single_court(self, base_state, mock_tools):
        """Test auto-selection when only one court exists (Requirements 14.1, 14.2, 14.3)."""
        # Mock get_property_courts_tool to return single court
        with patch('app.agent.nodes.booking.select_court.get_property_courts_tool') as mock_get_courts:
            mock_get_courts.return_value = [SAMPLE_COURTS[0]]
            
            # Execute node
            result = await select_court(base_state, tools=mock_tools)
            
            # Verify auto-selection
            assert result["flow_state"]["court_id"] == 1
            assert result["flow_state"]["court_name"] == "Court A"
            assert result["flow_state"]["booking_step"] == "court_selected"
            assert result["next_node"] == "select_date"
            assert "Court A" in result["response_content"]
    
    @pytest.mark.asyncio
    async def test_present_multiple_courts(self, base_state, mock_tools):
        """Test presenting options when multiple courts exist."""
        # Mock get_property_courts_tool to return multiple courts
        with patch('app.agent.nodes.booking.select_court.get_property_courts_tool') as mock_get_courts:
            mock_get_courts.return_value = SAMPLE_COURTS
            
            # Execute node
            result = await select_court(base_state, tools=mock_tools)
            
            # Verify response
            assert result["response_type"] == "button"
            assert "buttons" in result["response_metadata"]
            assert len(result["response_metadata"]["buttons"]) == 3
            assert result["flow_state"]["booking_step"] == "awaiting_court_selection"
            assert result["next_node"] == "wait_for_selection"
            
            # Verify buttons contain court names
            button_texts = [b["text"] for b in result["response_metadata"]["buttons"]]
            assert any("Court A" in text for text in button_texts)
            assert any("Court B" in text for text in button_texts)
            assert any("Court C" in text for text in button_texts)
    
    @pytest.mark.asyncio
    async def test_no_courts_available(self, base_state, mock_tools):
        """Test error handling when no courts are available."""
        # Mock get_property_courts_tool to return empty list
        with patch('app.agent.nodes.booking.select_court.get_property_courts_tool') as mock_get_courts:
            mock_get_courts.return_value = []
            
            # Execute node
            result = await select_court(base_state, tools=mock_tools)
            
            # Verify error response
            assert result["response_type"] == "text"
            assert "doesn't have any courts" in result["response_content"].lower()
            assert result["next_node"] == "end"
    
    @pytest.mark.asyncio
    async def test_court_fetch_error(self, base_state, mock_tools):
        """Test error handling when court fetch fails."""
        # Mock get_property_courts_tool to raise exception
        with patch('app.agent.nodes.booking.select_court.get_property_courts_tool') as mock_get_courts:
            mock_get_courts.side_effect = Exception("Database error")
            
            # Execute node
            result = await select_court(base_state, tools=mock_tools)
            
            # Verify error response
            assert result["response_type"] == "text"
            assert "trouble accessing" in result["response_content"].lower()
            assert result["next_node"] == "end"
    
    @pytest.mark.asyncio
    async def test_court_buttons_include_sport_type(self, base_state, mock_tools):
        """Test that court buttons include sport type information."""
        # Mock get_property_courts_tool to return courts with sport types
        with patch('app.agent.nodes.booking.select_court.get_property_courts_tool') as mock_get_courts:
            mock_get_courts.return_value = SAMPLE_COURTS
            
            # Execute node
            result = await select_court(base_state, tools=mock_tools)
            
            # Verify buttons include sport type
            buttons = result["response_metadata"]["buttons"]
            assert any("Tennis" in b["text"] for b in buttons)
            assert any("Basketball" in b["text"] for b in buttons)
            assert any("Futsal" in b["text"] for b in buttons)

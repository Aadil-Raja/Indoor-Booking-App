"""
Unit tests for bot memory manager.

This module tests the update_bot_memory function and its helper functions
that maintain conversation context, user preferences, and recent interactions.

Requirements: 8.1-8.5, 11.2, 11.3
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, Any

# Import memory manager to test
import sys
from pathlib import Path

# Add Backend path for imports
backend_path = Path(__file__).parent.parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from apps.chatbot.app.agent.state.memory_manager import (
    update_bot_memory,
    _handle_search_properties,
    _handle_property_details,
    _handle_court_details,
    _handle_court_availability,
)


# Fixtures for mock data

@pytest.fixture
def empty_bot_memory():
    """Empty bot memory dictionary."""
    return {}


@pytest.fixture
def bot_memory_with_context():
    """Bot memory with existing context."""
    return {
        "context": {
            "last_search_results": ["1", "2", "3"],
            "last_tools_used": ["search_properties"]
        },
        "user_preferences": {
            "preferred_sport": "basketball"
        }
    }


@pytest.fixture
def mock_search_action():
    """Mock LangChain action for search_properties tool."""
    action = MagicMock()
    action.tool = "search_properties"
    action.tool_input = {
        "owner_profile_id": 1,
        "sport_type": "tennis",
        "city": "New York",
        "limit": 10
    }
    return action


@pytest.fixture
def mock_search_observation():
    """Mock observation (result) from search_properties tool."""
    return [
        {"id": 6, "name": "Downtown Tennis Center", "city": "New York"},
        {"id": 12, "name": "Uptown Sports Complex", "city": "New York"},
        {"id": 15, "name": "Central Tennis Club", "city": "New York"}
    ]


@pytest.fixture
def mock_property_details_action():
    """Mock LangChain action for get_property_details tool."""
    action = MagicMock()
    action.tool = "get_property_details"
    action.tool_input = {
        "property_id": 6
    }
    return action


@pytest.fixture
def mock_court_details_action():
    """Mock LangChain action for get_court_details tool."""
    action = MagicMock()
    action.tool = "get_court_details"
    action.tool_input = {
        "court_id": 23
    }
    return action


@pytest.fixture
def mock_availability_action():
    """Mock LangChain action for get_court_availability tool."""
    action = MagicMock()
    action.tool = "get_court_availability"
    action.tool_input = {
        "court_id": 23,
        "date": "2026-03-10"
    }
    return action


# Tests for update_bot_memory with search_properties

def test_update_bot_memory_with_search_results(
    empty_bot_memory,
    mock_search_action,
    mock_search_observation
):
    """Test updating bot_memory with search_properties results."""
    agent_result = {
        "output": "Here are the tennis courts in New York...",
        "intermediate_steps": [
            (mock_search_action, mock_search_observation)
        ]
    }
    
    updated_memory = update_bot_memory(empty_bot_memory, agent_result)
    
    # Verify search results are stored
    assert "context" in updated_memory
    assert "last_search_results" in updated_memory["context"]
    assert updated_memory["context"]["last_search_results"] == ["6", "12", "15"]
    
    # Verify search params are stored (without owner_profile_id)
    assert "last_search_params" in updated_memory["context"]
    assert updated_memory["context"]["last_search_params"]["sport_type"] == "tennis"
    assert updated_memory["context"]["last_search_params"]["city"] == "New York"
    assert "owner_profile_id" not in updated_memory["context"]["last_search_params"]
    
    # Verify tools used are tracked
    assert "last_tools_used" in updated_memory["context"]
    assert updated_memory["context"]["last_tools_used"] == ["search_properties"]


def test_update_bot_memory_extracts_sport_preference(
    empty_bot_memory,
    mock_search_action,
    mock_search_observation
):
    """Test that sport preference is extracted from search parameters."""
    agent_result = {
        "output": "Here are the tennis courts...",
        "intermediate_steps": [
            (mock_search_action, mock_search_observation)
        ]
    }
    
    updated_memory = update_bot_memory(empty_bot_memory, agent_result)
    
    # Verify user preference is stored
    assert "user_preferences" in updated_memory
    assert "preferred_sport" in updated_memory["user_preferences"]
    assert updated_memory["user_preferences"]["preferred_sport"] == "tennis"


def test_update_bot_memory_search_without_sport_type(
    empty_bot_memory,
    mock_search_observation
):
    """Test search without sport_type doesn't create preference."""
    action = MagicMock()
    action.tool = "search_properties"
    action.tool_input = {
        "owner_profile_id": 1,
        "city": "New York",
        "limit": 10
    }
    
    agent_result = {
        "output": "Here are the properties...",
        "intermediate_steps": [
            (action, mock_search_observation)
        ]
    }
    
    updated_memory = update_bot_memory(empty_bot_memory, agent_result)
    
    # Verify search results are stored
    assert "last_search_results" in updated_memory["context"]
    
    # Verify no sport preference is created
    assert "user_preferences" not in updated_memory or \
           "preferred_sport" not in updated_memory.get("user_preferences", {})


def test_update_bot_memory_search_with_empty_results(empty_bot_memory):
    """Test search with no results."""
    action = MagicMock()
    action.tool = "search_properties"
    action.tool_input = {
        "owner_profile_id": 1,
        "sport_type": "cricket",
        "limit": 10
    }
    
    agent_result = {
        "output": "No properties found...",
        "intermediate_steps": [
            (action, [])  # Empty results
        ]
    }
    
    updated_memory = update_bot_memory(empty_bot_memory, agent_result)
    
    # Verify tools used are tracked
    assert updated_memory["context"]["last_tools_used"] == ["search_properties"]
    
    # Verify search params are NOT stored (empty observation means handler not called)
    assert "last_search_params" not in updated_memory["context"]
    
    # Verify preference is NOT extracted (empty observation means handler not called)
    assert "user_preferences" not in updated_memory or \
           "preferred_sport" not in updated_memory.get("user_preferences", {})
    
    # Verify no search results are stored (empty list not stored)
    assert "last_search_results" not in updated_memory["context"]


# Tests for update_bot_memory with property details

def test_update_bot_memory_stores_last_viewed_property(
    empty_bot_memory,
    mock_property_details_action
):
    """Test storing last viewed property."""
    agent_result = {
        "output": "Here are the details for Downtown Tennis Center...",
        "intermediate_steps": [
            (mock_property_details_action, {"id": 6, "name": "Downtown Tennis Center"})
        ]
    }
    
    updated_memory = update_bot_memory(empty_bot_memory, agent_result)
    
    # Verify last viewed property is stored
    assert "context" in updated_memory
    assert "last_viewed_property" in updated_memory["context"]
    assert updated_memory["context"]["last_viewed_property"] == 6
    
    # Verify tools used are tracked
    assert updated_memory["context"]["last_tools_used"] == ["get_property_details"]


def test_update_bot_memory_property_details_updates_existing_context(
    bot_memory_with_context,
    mock_property_details_action
):
    """Test that property details update existing context."""
    agent_result = {
        "output": "Here are the details...",
        "intermediate_steps": [
            (mock_property_details_action, {"id": 6, "name": "Test Property"})
        ]
    }
    
    updated_memory = update_bot_memory(bot_memory_with_context, agent_result)
    
    # Verify existing context is preserved
    assert updated_memory["context"]["last_search_results"] == ["1", "2", "3"]
    
    # Verify new property is added
    assert updated_memory["context"]["last_viewed_property"] == 6
    
    # Verify tools list is updated
    assert updated_memory["context"]["last_tools_used"] == ["get_property_details"]


# Tests for update_bot_memory with court details

def test_update_bot_memory_stores_last_viewed_court(
    empty_bot_memory,
    mock_court_details_action
):
    """Test storing last viewed court."""
    agent_result = {
        "output": "Here are the details for Court 1...",
        "intermediate_steps": [
            (mock_court_details_action, {"id": 23, "name": "Court 1"})
        ]
    }
    
    updated_memory = update_bot_memory(empty_bot_memory, agent_result)
    
    # Verify last viewed court is stored
    assert "context" in updated_memory
    assert "last_viewed_court" in updated_memory["context"]
    assert updated_memory["context"]["last_viewed_court"] == 23
    
    # Verify tools used are tracked
    assert updated_memory["context"]["last_tools_used"] == ["get_court_details"]


# Tests for update_bot_memory with availability check

def test_update_bot_memory_stores_last_availability_check(
    empty_bot_memory,
    mock_availability_action
):
    """Test storing last availability check."""
    agent_result = {
        "output": "Here are the available slots...",
        "intermediate_steps": [
            (mock_availability_action, {"court_id": 23, "date": "2026-03-10", "available_slots": []})
        ]
    }
    
    updated_memory = update_bot_memory(empty_bot_memory, agent_result)
    
    # Verify availability check is stored
    assert "context" in updated_memory
    assert "last_availability_check" in updated_memory["context"]
    assert updated_memory["context"]["last_availability_check"]["court_id"] == 23
    assert updated_memory["context"]["last_availability_check"]["date"] == "2026-03-10"
    
    # Verify tools used are tracked
    assert updated_memory["context"]["last_tools_used"] == ["get_court_availability"]


# Tests for multiple tools in one interaction

def test_update_bot_memory_with_multiple_tools(
    empty_bot_memory,
    mock_search_action,
    mock_search_observation,
    mock_property_details_action
):
    """Test updating memory when multiple tools are used."""
    agent_result = {
        "output": "Here are tennis courts, and details for the first one...",
        "intermediate_steps": [
            (mock_search_action, mock_search_observation),
            (mock_property_details_action, {"id": 6, "name": "Downtown Tennis Center"})
        ]
    }
    
    updated_memory = update_bot_memory(empty_bot_memory, agent_result)
    
    # Verify search results are stored
    assert updated_memory["context"]["last_search_results"] == ["6", "12", "15"]
    
    # Verify property details are stored
    assert updated_memory["context"]["last_viewed_property"] == 6
    
    # Verify both tools are tracked
    assert updated_memory["context"]["last_tools_used"] == ["search_properties", "get_property_details"]
    
    # Verify preference is extracted
    assert updated_memory["user_preferences"]["preferred_sport"] == "tennis"


def test_update_bot_memory_with_complex_interaction(empty_bot_memory):
    """Test complex interaction with search, property details, court details, and availability."""
    # Create mock actions
    search_action = MagicMock()
    search_action.tool = "search_properties"
    search_action.tool_input = {"sport_type": "tennis", "city": "New York"}
    
    property_action = MagicMock()
    property_action.tool = "get_property_details"
    property_action.tool_input = {"property_id": 6}
    
    court_action = MagicMock()
    court_action.tool = "get_court_details"
    court_action.tool_input = {"court_id": 23}
    
    availability_action = MagicMock()
    availability_action.tool = "get_court_availability"
    availability_action.tool_input = {"court_id": 23, "date": "2026-03-10"}
    
    agent_result = {
        "output": "Complex response...",
        "intermediate_steps": [
            (search_action, [{"id": 6, "name": "Test"}]),
            (property_action, {"id": 6}),
            (court_action, {"id": 23}),
            (availability_action, {"court_id": 23, "date": "2026-03-10"})
        ]
    }
    
    updated_memory = update_bot_memory(empty_bot_memory, agent_result)
    
    # Verify all context is stored
    assert updated_memory["context"]["last_search_results"] == ["6"]
    assert updated_memory["context"]["last_viewed_property"] == 6
    assert updated_memory["context"]["last_viewed_court"] == 23
    assert updated_memory["context"]["last_availability_check"]["court_id"] == 23
    assert updated_memory["context"]["last_availability_check"]["date"] == "2026-03-10"
    
    # Verify all tools are tracked
    assert len(updated_memory["context"]["last_tools_used"]) == 4
    assert "search_properties" in updated_memory["context"]["last_tools_used"]
    assert "get_property_details" in updated_memory["context"]["last_tools_used"]
    assert "get_court_details" in updated_memory["context"]["last_tools_used"]
    assert "get_court_availability" in updated_memory["context"]["last_tools_used"]


# Tests for edge cases

def test_update_bot_memory_with_no_intermediate_steps(empty_bot_memory):
    """Test handling of agent result with no intermediate steps."""
    agent_result = {
        "output": "I can help you with that...",
        "intermediate_steps": []
    }
    
    updated_memory = update_bot_memory(empty_bot_memory, agent_result)
    
    # Verify context is initialized but empty
    assert "context" in updated_memory
    assert "last_tools_used" not in updated_memory["context"]


def test_update_bot_memory_with_missing_intermediate_steps(empty_bot_memory):
    """Test handling of agent result without intermediate_steps key."""
    agent_result = {
        "output": "I can help you with that..."
        # No intermediate_steps key
    }
    
    updated_memory = update_bot_memory(empty_bot_memory, agent_result)
    
    # Verify context is initialized but empty
    assert "context" in updated_memory
    assert "last_tools_used" not in updated_memory["context"]


def test_update_bot_memory_preserves_existing_preferences(bot_memory_with_context):
    """Test that existing preferences are preserved when not updated."""
    action = MagicMock()
    action.tool = "get_property_details"
    action.tool_input = {"property_id": 6}
    
    agent_result = {
        "output": "Here are the details...",
        "intermediate_steps": [
            (action, {"id": 6})
        ]
    }
    
    updated_memory = update_bot_memory(bot_memory_with_context, agent_result)
    
    # Verify existing preference is preserved
    assert updated_memory["user_preferences"]["preferred_sport"] == "basketball"


def test_update_bot_memory_overwrites_sport_preference(bot_memory_with_context):
    """Test that sport preference is overwritten with new search."""
    action = MagicMock()
    action.tool = "search_properties"
    action.tool_input = {"sport_type": "tennis"}
    
    agent_result = {
        "output": "Here are tennis courts...",
        "intermediate_steps": [
            (action, [{"id": 6}])
        ]
    }
    
    updated_memory = update_bot_memory(bot_memory_with_context, agent_result)
    
    # Verify preference is updated
    assert updated_memory["user_preferences"]["preferred_sport"] == "tennis"


def test_update_bot_memory_with_invalid_observation_format(empty_bot_memory):
    """Test handling of invalid observation format."""
    action = MagicMock()
    action.tool = "search_properties"
    action.tool_input = {"sport_type": "tennis"}
    
    # Invalid observation (not a list)
    agent_result = {
        "output": "Error occurred...",
        "intermediate_steps": [
            (action, "invalid observation format")
        ]
    }
    
    updated_memory = update_bot_memory(empty_bot_memory, agent_result)
    
    # Verify function handles gracefully
    assert "context" in updated_memory
    assert updated_memory["context"]["last_tools_used"] == ["search_properties"]
    # No search results stored due to invalid format
    assert "last_search_results" not in updated_memory["context"]


def test_update_bot_memory_with_none_observation(empty_bot_memory):
    """Test handling of None observation."""
    action = MagicMock()
    action.tool = "get_property_details"
    action.tool_input = {"property_id": 999}
    
    agent_result = {
        "output": "Property not found...",
        "intermediate_steps": [
            (action, None)
        ]
    }
    
    updated_memory = update_bot_memory(empty_bot_memory, agent_result)
    
    # Verify function handles gracefully
    assert "context" in updated_memory
    assert updated_memory["context"]["last_tools_used"] == ["get_property_details"]
    # Property details handler checks for tool_input, not observation
    assert updated_memory["context"]["last_viewed_property"] == 999


# Tests for bot_memory structure validation

def test_bot_memory_structure_after_search(
    empty_bot_memory,
    mock_search_action,
    mock_search_observation
):
    """Verify bot_memory has correct structure after search."""
    agent_result = {
        "output": "Results...",
        "intermediate_steps": [
            (mock_search_action, mock_search_observation)
        ]
    }
    
    updated_memory = update_bot_memory(empty_bot_memory, agent_result)
    
    # Verify structure
    assert isinstance(updated_memory, dict)
    assert isinstance(updated_memory["context"], dict)
    assert isinstance(updated_memory["context"]["last_search_results"], list)
    assert isinstance(updated_memory["context"]["last_search_params"], dict)
    assert isinstance(updated_memory["context"]["last_tools_used"], list)
    assert isinstance(updated_memory["user_preferences"], dict)
    assert isinstance(updated_memory["user_preferences"]["preferred_sport"], str)


def test_bot_memory_structure_after_availability_check(
    empty_bot_memory,
    mock_availability_action
):
    """Verify bot_memory has correct structure after availability check."""
    agent_result = {
        "output": "Available slots...",
        "intermediate_steps": [
            (mock_availability_action, {"court_id": 23, "date": "2026-03-10"})
        ]
    }
    
    updated_memory = update_bot_memory(empty_bot_memory, agent_result)
    
    # Verify structure
    assert isinstance(updated_memory, dict)
    assert isinstance(updated_memory["context"], dict)
    assert isinstance(updated_memory["context"]["last_availability_check"], dict)
    assert "court_id" in updated_memory["context"]["last_availability_check"]
    assert "date" in updated_memory["context"]["last_availability_check"]
    assert isinstance(updated_memory["context"]["last_availability_check"]["court_id"], int)
    assert isinstance(updated_memory["context"]["last_availability_check"]["date"], str)



# Tests for bot_memory persistence functions

@pytest.mark.asyncio
async def test_load_bot_memory_success():
    """Test loading bot_memory from database successfully."""
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4
    from apps.chatbot.app.agent.state.memory_manager import load_bot_memory
    
    # Mock chat with bot_memory
    chat_id = str(uuid4())
    mock_chat = MagicMock()
    mock_chat.bot_memory = {
        "conversation_history": [{"role": "user", "content": "Hello"}],
        "user_preferences": {"preferred_sport": "tennis"},
        "inferred_information": {"booking_frequency": "regular"},
        "context": {}
    }
    
    # Mock repository
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=mock_chat)
    
    # Mock session
    mock_session = MagicMock()
    
    # Patch ChatRepository
    with patch('apps.chatbot.app.agent.state.memory_manager.ChatRepository', return_value=mock_repo):
        bot_memory = await load_bot_memory(chat_id, mock_session)
    
    # Verify bot_memory was loaded
    assert bot_memory["user_preferences"]["preferred_sport"] == "tennis"
    assert bot_memory["inferred_information"]["booking_frequency"] == "regular"
    assert len(bot_memory["conversation_history"]) == 1


@pytest.mark.asyncio
async def test_load_bot_memory_chat_not_found():
    """Test loading bot_memory when chat doesn't exist."""
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4
    from apps.chatbot.app.agent.state.memory_manager import load_bot_memory
    
    chat_id = str(uuid4())
    
    # Mock repository returning None
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=None)
    
    mock_session = MagicMock()
    
    with patch('apps.chatbot.app.agent.state.memory_manager.ChatRepository', return_value=mock_repo):
        bot_memory = await load_bot_memory(chat_id, mock_session)
    
    # Should return initialized empty bot_memory
    assert bot_memory["conversation_history"] == []
    assert bot_memory["user_preferences"] == {}
    assert bot_memory["inferred_information"] == {}


@pytest.mark.asyncio
async def test_load_bot_memory_empty_memory():
    """Test loading bot_memory when it's empty in database."""
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4
    from apps.chatbot.app.agent.state.memory_manager import load_bot_memory
    
    chat_id = str(uuid4())
    
    # Mock chat with empty bot_memory
    mock_chat = MagicMock()
    mock_chat.bot_memory = {}
    
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=mock_chat)
    
    mock_session = MagicMock()
    
    with patch('apps.chatbot.app.agent.state.memory_manager.ChatRepository', return_value=mock_repo):
        bot_memory = await load_bot_memory(chat_id, mock_session)
    
    # Should return initialized empty bot_memory
    assert bot_memory["conversation_history"] == []
    assert bot_memory["user_preferences"] == {}
    assert bot_memory["inferred_information"] == {}


@pytest.mark.asyncio
async def test_save_bot_memory_success():
    """Test saving bot_memory to database successfully."""
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4
    from apps.chatbot.app.agent.state.memory_manager import save_bot_memory
    
    chat_id = str(uuid4())
    bot_memory = {
        "conversation_history": [],
        "user_preferences": {"preferred_sport": "tennis"},
        "inferred_information": {},
        "context": {}
    }
    
    # Mock chat
    mock_chat = MagicMock()
    
    # Mock repository
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=mock_chat)
    mock_repo.update = AsyncMock(return_value=mock_chat)
    
    mock_session = MagicMock()
    
    with patch('apps.chatbot.app.agent.state.memory_manager.ChatRepository', return_value=mock_repo):
        success = await save_bot_memory(chat_id, bot_memory, mock_session)
    
    # Verify save was successful
    assert success is True
    mock_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_save_bot_memory_chat_not_found():
    """Test saving bot_memory when chat doesn't exist."""
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4
    from apps.chatbot.app.agent.state.memory_manager import save_bot_memory
    
    chat_id = str(uuid4())
    bot_memory = {"user_preferences": {}}
    
    # Mock repository returning None
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=None)
    
    mock_session = MagicMock()
    
    with patch('apps.chatbot.app.agent.state.memory_manager.ChatRepository', return_value=mock_repo):
        success = await save_bot_memory(chat_id, bot_memory, mock_session)
    
    # Should return False
    assert success is False


@pytest.mark.asyncio
async def test_save_bot_memory_invalid_type():
    """Test saving bot_memory with invalid type."""
    from unittest.mock import AsyncMock, MagicMock
    from uuid import uuid4
    from apps.chatbot.app.agent.state.memory_manager import save_bot_memory
    
    chat_id = str(uuid4())
    invalid_memory = "not a dict"
    
    mock_session = MagicMock()
    
    success = await save_bot_memory(chat_id, invalid_memory, mock_session)
    
    # Should return False
    assert success is False


def test_update_bot_memory_preferences():
    """Test updating user preferences in bot_memory."""
    from apps.chatbot.app.agent.state.memory_manager import update_bot_memory_preferences
    
    bot_memory = {
        "user_preferences": {"preferred_sport": "tennis"},
        "inferred_information": {},
        "context": {}
    }
    
    preferences = {
        "preferred_time": "morning",
        "preferred_sport": "basketball"  # Override existing
    }
    
    updated = update_bot_memory_preferences(bot_memory, preferences)
    
    assert updated["user_preferences"]["preferred_time"] == "morning"
    assert updated["user_preferences"]["preferred_sport"] == "basketball"


def test_update_bot_memory_preferences_empty_memory():
    """Test updating preferences with empty bot_memory."""
    from apps.chatbot.app.agent.state.memory_manager import update_bot_memory_preferences
    
    bot_memory = {}
    preferences = {"preferred_sport": "tennis"}
    
    updated = update_bot_memory_preferences(bot_memory, preferences)
    
    assert updated["user_preferences"]["preferred_sport"] == "tennis"


def test_update_bot_memory_inferred():
    """Test updating inferred information in bot_memory."""
    from apps.chatbot.app.agent.state.memory_manager import update_bot_memory_inferred
    
    bot_memory = {
        "user_preferences": {},
        "inferred_information": {"booking_frequency": "regular"},
        "context": {}
    }
    
    inferred_info = {
        "interests": ["tennis", "basketball"],
        "booking_frequency": "occasional"  # Override existing
    }
    
    updated = update_bot_memory_inferred(bot_memory, inferred_info)
    
    assert updated["inferred_information"]["interests"] == ["tennis", "basketball"]
    assert updated["inferred_information"]["booking_frequency"] == "occasional"


def test_update_bot_memory_inferred_empty_memory():
    """Test updating inferred info with empty bot_memory."""
    from apps.chatbot.app.agent.state.memory_manager import update_bot_memory_inferred
    
    bot_memory = {}
    inferred_info = {"booking_frequency": "regular"}
    
    updated = update_bot_memory_inferred(bot_memory, inferred_info)
    
    assert updated["inferred_information"]["booking_frequency"] == "regular"

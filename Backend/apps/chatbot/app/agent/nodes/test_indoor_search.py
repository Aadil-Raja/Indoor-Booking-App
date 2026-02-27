"""
Unit tests for indoor search handler node.

This module tests the indoor_search_handler node functionality including:
- Search parameter extraction from user messages
- Property and court search tool integration
- Result formatting as list messages
- Bot memory updates with search results
- No results handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any, List

from app.agent.nodes.indoor_search import (
    indoor_search_handler,
    _extract_search_params,
    _format_search_results,
    _generate_no_results_response,
    _generate_results_response,
    _update_bot_memory_with_results,
)
from app.agent.state.conversation_state import ConversationState


# Test fixtures

@pytest.fixture
def base_state() -> ConversationState:
    """Create a base conversation state for testing."""
    return {
        "chat_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "user-uuid",
        "owner_id": "owner-uuid",
        "user_message": "",
        "flow_state": {},
        "bot_memory": {},
        "messages": [],
        "intent": "search",
        "response_content": "",
        "response_type": "text",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
    }


@pytest.fixture
def mock_tools() -> Dict[str, Any]:
    """Create mock tools for testing."""
    return {
        "search_properties": AsyncMock(),
        "get_property_courts": AsyncMock(),
    }


@pytest.fixture
def sample_properties() -> List[Dict[str, Any]]:
    """Create sample property data for testing."""
    return [
        {
            "id": 1,
            "name": "Downtown Sports Center",
            "city": "New York",
            "address": "123 Main St",
            "courts_count": 5,
        },
        {
            "id": 2,
            "name": "Westside Arena",
            "city": "New York",
            "address": "456 West Ave",
            "courts_count": 3,
        },
        {
            "id": 3,
            "name": "Tennis Club",
            "city": "Brooklyn",
            "address": "789 Tennis Rd",
            "matching_courts_count": 4,
        },
    ]


# Test search parameter extraction

def test_extract_search_params_tennis():
    """Test extraction of tennis sport type."""
    message = "I'm looking for tennis courts"
    params = _extract_search_params(message)
    assert params["sport_type"] == "tennis"


def test_extract_search_params_basketball():
    """Test extraction of basketball sport type with variations."""
    messages = [
        "find basketball courts",
        "looking for basket ball",
        "show me hoops",
    ]
    for message in messages:
        params = _extract_search_params(message)
        assert params["sport_type"] == "basketball"


def test_extract_search_params_location():
    """Test extraction of location keywords."""
    message = "tennis courts downtown"
    params = _extract_search_params(message)
    assert params["sport_type"] == "tennis"
    assert params["location"] == "downtown"


def test_extract_search_params_multiple_sports():
    """Test that only first sport type is extracted."""
    message = "tennis or basketball courts"
    params = _extract_search_params(message)
    # Should extract tennis (first match)
    assert params["sport_type"] == "tennis"


def test_extract_search_params_no_matches():
    """Test extraction with no recognizable parameters."""
    message = "show me facilities"
    params = _extract_search_params(message)
    assert "sport_type" not in params
    assert "location" not in params


def test_extract_search_params_typos():
    """Test handling of informal language and variations."""
    message = "volley ball courts west side"
    params = _extract_search_params(message)
    assert params["sport_type"] == "volleyball"
    assert params["location"] == "westside"


# Test result formatting

def test_format_search_results_basic(sample_properties):
    """Test basic result formatting."""
    list_items = _format_search_results(sample_properties)
    
    assert len(list_items) == 3
    assert list_items[0]["id"] == "1"
    assert list_items[0]["title"] == "Downtown Sports Center"
    assert "New York" in list_items[0]["description"]


def test_format_search_results_with_court_count(sample_properties):
    """Test formatting with matching courts count."""
    list_items = _format_search_results(sample_properties)
    
    # Third property has matching_courts_count
    assert "4 courts available" in list_items[2]["description"]


def test_format_search_results_limit():
    """Test that results are limited to 5 items."""
    properties = [{"id": i, "name": f"Property {i}", "city": "NYC"} for i in range(10)]
    list_items = _format_search_results(properties)
    
    assert len(list_items) == 5


def test_format_search_results_empty():
    """Test formatting with empty results."""
    list_items = _format_search_results([])
    assert list_items == []


# Test response generation

def test_generate_no_results_response_with_sport():
    """Test no results message with sport type."""
    params = {"sport_type": "tennis"}
    response = _generate_no_results_response(params)
    
    assert "tennis facilities" in response
    assert "couldn't find" in response


def test_generate_no_results_response_with_location():
    """Test no results message with location."""
    params = {"sport_type": "tennis", "location": "downtown"}
    response = _generate_no_results_response(params)
    
    assert "tennis facilities" in response
    assert "downtown" in response


def test_generate_results_response_with_criteria():
    """Test results message with search criteria."""
    params = {"sport_type": "tennis", "location": "downtown"}
    response = _generate_results_response(params, 3)
    
    assert "tennis" in response
    assert "downtown" in response
    assert "available" in response


def test_generate_results_response_with_count():
    """Test results message shows count when limited."""
    params = {"sport_type": "tennis"}
    response = _generate_results_response(params, 10)
    
    assert "showing top 5 of 10" in response


# Test bot memory updates

def test_update_bot_memory_with_results(sample_properties):
    """Test bot memory is updated with search results."""
    bot_memory = {}
    search_params = {"sport_type": "tennis", "location": "downtown"}
    
    updated_memory = _update_bot_memory_with_results(
        bot_memory, sample_properties, search_params
    )
    
    assert "context" in updated_memory
    assert "last_search_results" in updated_memory["context"]
    assert len(updated_memory["context"]["last_search_results"]) == 3
    assert updated_memory["context"]["last_search_results"][0] == "1"


def test_update_bot_memory_preserves_existing():
    """Test that existing bot memory is preserved."""
    bot_memory = {
        "user_preferences": {"preferred_time": "afternoon"},
        "context": {"some_key": "some_value"}
    }
    properties = [{"id": 1, "name": "Test"}]
    search_params = {}
    
    updated_memory = _update_bot_memory_with_results(
        bot_memory, properties, search_params
    )
    
    assert updated_memory["user_preferences"]["preferred_time"] == "afternoon"
    assert updated_memory["context"]["some_key"] == "some_value"


def test_update_bot_memory_with_sport_preference(sample_properties):
    """Test that sport preference is stored in user_preferences."""
    bot_memory = {}
    search_params = {"sport_type": "tennis"}
    
    updated_memory = _update_bot_memory_with_results(
        bot_memory, sample_properties, search_params
    )
    
    assert "user_preferences" in updated_memory
    assert updated_memory["user_preferences"]["preferred_sport"] == "tennis"


# Test indoor search handler integration

@pytest.mark.asyncio
async def test_indoor_search_handler_success(base_state, mock_tools, sample_properties):
    """Test successful search with results."""
    base_state["user_message"] = "find tennis courts downtown"
    mock_tools["search_properties"].return_value = sample_properties
    
    result = await indoor_search_handler(base_state, tools=mock_tools)
    
    # Verify search was called
    mock_tools["search_properties"].assert_called_once()
    call_kwargs = mock_tools["search_properties"].call_args.kwargs
    assert call_kwargs["sport_type"] == "tennis"
    assert call_kwargs["city"] == "downtown"
    
    # Verify response
    assert result["response_type"] == "list"
    assert "list_items" in result["response_metadata"]
    assert len(result["response_metadata"]["list_items"]) == 3
    
    # Verify bot memory updated
    assert "last_search_results" in result["bot_memory"]["context"]
    assert len(result["bot_memory"]["context"]["last_search_results"]) == 3


@pytest.mark.asyncio
async def test_indoor_search_handler_no_results(base_state, mock_tools):
    """Test search with no results."""
    base_state["user_message"] = "find tennis courts"
    mock_tools["search_properties"].return_value = []
    
    result = await indoor_search_handler(base_state, tools=mock_tools)
    
    # Verify response
    assert result["response_type"] == "text"
    assert "couldn't find" in result["response_content"]
    assert result["response_metadata"] == {}


@pytest.mark.asyncio
async def test_indoor_search_handler_with_enrichment(base_state, mock_tools, sample_properties):
    """Test search with court enrichment for sport type."""
    base_state["user_message"] = "tennis courts"
    mock_tools["search_properties"].return_value = sample_properties
    mock_tools["get_property_courts"].return_value = [
        {"id": 1, "sport_type": "tennis", "name": "Court A"},
        {"id": 2, "sport_type": "tennis", "name": "Court B"},
    ]
    
    result = await indoor_search_handler(base_state, tools=mock_tools)
    
    # Verify enrichment was attempted
    assert mock_tools["get_property_courts"].called
    
    # Verify response
    assert result["response_type"] == "list"
    assert len(result["response_metadata"]["list_items"]) > 0


@pytest.mark.asyncio
async def test_indoor_search_handler_preserves_bot_memory(base_state, mock_tools, sample_properties):
    """Test that existing bot memory is preserved."""
    base_state["user_message"] = "find tennis courts"
    base_state["bot_memory"] = {
        "user_preferences": {"preferred_time": "afternoon"},
        "context": {"existing_key": "existing_value"}
    }
    mock_tools["search_properties"].return_value = sample_properties
    
    result = await indoor_search_handler(base_state, tools=mock_tools)
    
    # Verify existing memory preserved
    assert result["bot_memory"]["user_preferences"]["preferred_time"] == "afternoon"
    assert result["bot_memory"]["context"]["existing_key"] == "existing_value"
    
    # Verify new data added
    assert "last_search_results" in result["bot_memory"]["context"]


@pytest.mark.asyncio
async def test_indoor_search_handler_generic_search(base_state, mock_tools, sample_properties):
    """Test generic search without specific parameters."""
    base_state["user_message"] = "show me available facilities"
    mock_tools["search_properties"].return_value = sample_properties
    
    result = await indoor_search_handler(base_state, tools=mock_tools)
    
    # Verify search was called with no filters
    call_kwargs = mock_tools["search_properties"].call_args.kwargs
    assert call_kwargs.get("sport_type") is None
    assert call_kwargs.get("city") is None
    
    # Verify response
    assert result["response_type"] == "list"
    assert "available facilities" in result["response_content"]


@pytest.mark.asyncio
async def test_indoor_search_handler_error_handling(base_state, mock_tools):
    """Test error handling when search fails."""
    base_state["user_message"] = "find tennis courts"
    mock_tools["search_properties"].side_effect = Exception("Search failed")
    
    result = await indoor_search_handler(base_state, tools=mock_tools)
    
    # Should handle error gracefully and return no results
    assert result["response_type"] == "text"
    assert "couldn't find" in result["response_content"]

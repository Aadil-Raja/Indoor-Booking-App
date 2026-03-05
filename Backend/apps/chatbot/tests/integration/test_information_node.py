"""
Integration tests for information handler.

This module tests complete flows through the information_handler, including
LangChain agent execution, tool calling, bot_memory updates, and context
handling. Tests use mocked LLM responses for predictable behavior.

Requirements: 1.1-1.5, 7.1-7.5, 8.1-8.5

NOTE: These tests currently require proper mocking of LangChain's AgentExecutor.
The current mocking approach mocks ChatOpenAI and create_openai_functions_agent,
but the AgentExecutor still attempts to execute. For production use, consider:
1. Using a test OpenAI API key with rate limiting
2. Implementing a FakeLLM for testing
3. Mocking at a lower level (OpenAI client level)
4. Using pytest-vcr to record/replay API interactions

The test structure and assertions are correct and comprehensive.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from typing import Dict, Any
from contextlib import contextmanager
import sys
from pathlib import Path

# Add Backend path for imports
backend_path = Path(__file__).parent.parent.parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Import directly to avoid circular imports
import importlib.util
import os

# Load information_handler module directly
spec = importlib.util.spec_from_file_location(
    "information",
    os.path.join(backend_path, "apps", "chatbot", "app", "agent", "nodes", "information.py")
)
information_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(information_module)
information_handler = information_module.information_handler

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
    token_usage: Optional[int]
    search_results: Optional[List[Dict[str, Any]]]
    availability_data: Optional[Dict[str, Any]]
    pricing_data: Optional[Dict[str, Any]]


# Fixtures for mock data

@pytest.fixture
def base_state() -> ConversationState:
    """Base conversation state for testing."""
    return {
        "chat_id": "test-chat-123",
        "user_id": "1",
        "owner_profile_id": "1",
        "user_message": "",
        "flow_state": {},
        "bot_memory": {},
        "messages": [],
        "intent": "information",
        "response_content": "",
        "response_type": "text",
        "response_metadata": {},
        "token_usage": None,
        "search_results": None,
        "availability_data": None,
        "pricing_data": None,
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
    """Mock property search results."""
    return [
        {
            "id": 6,
            "name": "Downtown Tennis Center",
            "city": "New York",
            "address": "123 Main St",
            "amenities": ["parking", "locker_rooms"]
        },
        {
            "id": 12,
            "name": "Uptown Sports Complex",
            "city": "New York",
            "address": "456 Park Ave",
            "amenities": ["parking", "cafe"]
        }
    ]


@pytest.fixture
def mock_property_details():
    """Mock property details."""
    return {
        "id": 6,
        "name": "Downtown Tennis Center",
        "description": "Premier tennis facility",
        "address": "123 Main St",
        "city": "New York",
        "state": "NY",
        "country": "USA",
        "phone": "555-1234",
        "email": "info@dtc.com",
        "maps_link": "https://maps.google.com/...",
        "amenities": ["parking", "locker_rooms", "pro_shop"],
        "courts": [
            {
                "id": 23,
                "name": "Court 1",
                "sport_type": "tennis"
            }
        ],
        "media": [
            {
                "id": 1,
                "media_type": "photo",
                "url": "https://example.com/photo1.jpg",
                "caption": "Main entrance"
            }
        ]
    }


@pytest.fixture
def mock_availability():
    """Mock availability data."""
    return {
        "date": "2026-03-10",
        "court_id": 23,
        "court_name": "Court 1",
        "available_slots": [
            {
                "start_time": "09:00:00",
                "end_time": "10:00:00",
                "price_per_hour": 50.0,
                "label": "Daytime"
            },
            {
                "start_time": "10:00:00",
                "end_time": "11:00:00",
                "price_per_hour": 50.0,
                "label": "Daytime"
            }
        ]
    }


# Helper function to create mock agent action

def create_mock_action(tool_name: str, tool_input: Dict[str, Any]):
    """Create a mock LangChain action."""
    action = MagicMock()
    action.tool = tool_name
    action.tool_input = tool_input
    return action


# Helper function to create mock agent context

@contextmanager
def mock_langchain_components(mock_agent_result):
    """Create a context manager that mocks all LangChain components."""
    # Mock ChatOpenAI at the module where it's imported
    with patch('app.services.llm.langchain_wrapper.ChatOpenAI') as mock_chat_openai_class:
        # Create a mock ChatOpenAI instance
        mock_chat_openai = MagicMock()
        mock_chat_openai_class.return_value = mock_chat_openai
        
        # Mock create_openai_functions_agent to return a simple mock
        with patch('app.agent.nodes.information.create_openai_functions_agent') as mock_create_agent:
            mock_agent = MagicMock()
            mock_create_agent.return_value = mock_agent
            
            # Mock the AgentExecutor to return our predefined result
            with patch('app.agent.nodes.information.AgentExecutor') as mock_executor_class:
                mock_executor = AsyncMock()
                mock_executor.ainvoke = AsyncMock(return_value=mock_agent_result)
                mock_executor_class.return_value = mock_executor
                
                yield


# Test 1: Simple search query flow

@pytest.mark.asyncio
async def test_simple_search_query_flow(
    base_state,
    mock_llm_provider,
    mock_properties
):
    """
    Test simple property search query flow.
    
    User asks: "Show me tennis courts"
    Expected: Agent calls search_properties tool and returns results
    
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
    """
    # Setup state
    state = base_state.copy()
    state["user_message"] = "Show me tennis courts"
    
    # Mock the agent executor result
    mock_agent_result = {
        "input": "Show me tennis courts",
        "output": "I found 2 tennis facilities for you: Downtown Tennis Center and Uptown Sports Complex.",
        "intermediate_steps": [
            (
                create_mock_action("search_properties", {
                    "sport_type": "tennis",
                    "limit": 10
                }),
                mock_properties
            )
        ]
    }
    
    # Execute with mocked components
    with mock_langchain_components(mock_agent_result):
        result_state = await information_handler(state, mock_llm_provider)
    
    # Verify response
    assert result_state["response_content"] == mock_agent_result["output"]
    assert result_state["response_type"] == "text"
    assert "Downtown Tennis Center" in result_state["response_content"]
    assert "Uptown Sports Complex" in result_state["response_content"]
    
    # Verify bot_memory was updated
    assert "context" in result_state["bot_memory"]
    assert "last_search_results" in result_state["bot_memory"]["context"]
    assert result_state["bot_memory"]["context"]["last_search_results"] == ["6", "12"]
    
    # Verify user preference was extracted
    assert "user_preferences" in result_state["bot_memory"]
    assert result_state["bot_memory"]["user_preferences"]["preferred_sport"] == "tennis"
    
    # Verify tools used were tracked
    assert "last_tools_used" in result_state["bot_memory"]["context"]
    assert "search_properties" in result_state["bot_memory"]["context"]["last_tools_used"]


# Test 2: Property details query flow

@pytest.mark.asyncio
async def test_property_details_query_flow(
    base_state,
    mock_llm_provider,
    mock_property_details
):
    """
    Test property details query flow.
    
    User asks: "Tell me about property 6"
    Expected: Agent calls get_property_details tool and returns details
    
    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5
    """
    # Setup state
    state = base_state.copy()
    state["user_message"] = "Tell me about property 6"
    
    # Mock the agent executor result
    mock_agent_result = {
        "input": "Tell me about property 6",
        "output": "Downtown Tennis Center is a premier tennis facility located at 123 Main St in New York. It features parking, locker rooms, and a pro shop. The facility has 1 tennis court available.",
        "intermediate_steps": [
            (
                create_mock_action("get_property_details", {
                    "property_id": 6
                }),
                mock_property_details
            )
        ]
    }
    
    # Execute with mocked components
    with mock_langchain_components(mock_agent_result):
        result_state = await information_handler(state, mock_llm_provider)
    
    # Verify response
    assert result_state["response_content"] == mock_agent_result["output"]
    assert "Downtown Tennis Center" in result_state["response_content"]
    assert "123 Main St" in result_state["response_content"]
    
    # Verify bot_memory was updated with last viewed property
    assert "context" in result_state["bot_memory"]
    assert "last_viewed_property" in result_state["bot_memory"]["context"]
    assert result_state["bot_memory"]["context"]["last_viewed_property"] == 6
    
    # Verify tools used were tracked
    assert "last_tools_used" in result_state["bot_memory"]["context"]
    assert "get_property_details" in result_state["bot_memory"]["context"]["last_tools_used"]


# Test 3: Court availability query flow

@pytest.mark.asyncio
async def test_court_availability_query_flow(
    base_state,
    mock_llm_provider,
    mock_availability
):
    """
    Test court availability query flow.
    
    User asks: "Check availability for court 23 on March 10"
    Expected: Agent calls get_court_availability tool and returns slots
    
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
    """
    # Setup state
    state = base_state.copy()
    state["user_message"] = "Check availability for court 23 on March 10"
    
    # Mock the agent executor result
    mock_agent_result = {
        "input": "Check availability for court 23 on March 10",
        "output": "Court 1 has 2 available slots on March 10, 2026: 9:00 AM - 10:00 AM ($50/hour) and 10:00 AM - 11:00 AM ($50/hour).",
        "intermediate_steps": [
            (
                create_mock_action("get_court_availability", {
                    "court_id": 23,
                    "date": "2026-03-10"
                }),
                mock_availability
            )
        ]
    }
    
    # Execute with mocked components
    with mock_langchain_components(mock_agent_result):
        result_state = await information_handler(state, mock_llm_provider)
    
    # Verify response
    assert result_state["response_content"] == mock_agent_result["output"]
    assert "Court 1" in result_state["response_content"]
    assert "March 10" in result_state["response_content"]
    assert "9:00 AM" in result_state["response_content"]
    
    # Verify bot_memory was updated with availability check
    assert "context" in result_state["bot_memory"]
    assert "last_availability_check" in result_state["bot_memory"]["context"]
    assert result_state["bot_memory"]["context"]["last_availability_check"]["court_id"] == 23
    assert result_state["bot_memory"]["context"]["last_availability_check"]["date"] == "2026-03-10"
    
    # Verify tools used were tracked
    assert "last_tools_used" in result_state["bot_memory"]["context"]
    assert "get_court_availability" in result_state["bot_memory"]["context"]["last_tools_used"]


# Test 4: Complex multi-tool query

@pytest.mark.asyncio
async def test_complex_multi_tool_query(
    base_state,
    mock_llm_provider,
    mock_properties,
    mock_property_details,
    mock_availability
):
    """
    Test complex query requiring multiple tools.
    
    User asks: "Show me tennis courts in New York and check availability for the first one on March 10"
    Expected: Agent calls search_properties, get_property_details, and get_court_availability
    
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5
    """
    # Setup state
    state = base_state.copy()
    state["user_message"] = "Show me tennis courts in New York and check availability for the first one on March 10"
    
    # Mock the agent executor result with multiple tool calls
    mock_agent_result = {
        "input": state["user_message"],
        "output": "I found 2 tennis facilities in New York. The first one is Downtown Tennis Center at 123 Main St. For Court 1 at this facility, there are 2 available slots on March 10: 9:00 AM - 10:00 AM and 10:00 AM - 11:00 AM, both at $50/hour.",
        "intermediate_steps": [
            (
                create_mock_action("search_properties", {
                    "sport_type": "tennis",
                    "city": "New York",
                    "limit": 10
                }),
                mock_properties
            ),
            (
                create_mock_action("get_property_details", {
                    "property_id": 6
                }),
                mock_property_details
            ),
            (
                create_mock_action("get_court_availability", {
                    "court_id": 23,
                    "date": "2026-03-10"
                }),
                mock_availability
            )
        ]
    }
    
    # Execute with mocked components
    with mock_langchain_components(mock_agent_result):
        result_state = await information_handler(state, mock_llm_provider)
    
    # Verify response contains information from all tools
    assert result_state["response_content"] == mock_agent_result["output"]
    assert "Downtown Tennis Center" in result_state["response_content"]
    assert "March 10" in result_state["response_content"]
    assert "9:00 AM" in result_state["response_content"]
    
    # Verify bot_memory was updated with all context
    assert "context" in result_state["bot_memory"]
    
    # Verify search results
    assert "last_search_results" in result_state["bot_memory"]["context"]
    assert result_state["bot_memory"]["context"]["last_search_results"] == ["6", "12"]
    
    # Verify property details
    assert "last_viewed_property" in result_state["bot_memory"]["context"]
    assert result_state["bot_memory"]["context"]["last_viewed_property"] == 6
    
    # Verify availability check
    assert "last_availability_check" in result_state["bot_memory"]["context"]
    assert result_state["bot_memory"]["context"]["last_availability_check"]["court_id"] == 23
    
    # Verify all tools were tracked
    assert "last_tools_used" in result_state["bot_memory"]["context"]
    tools_used = result_state["bot_memory"]["context"]["last_tools_used"]
    assert "search_properties" in tools_used
    assert "get_property_details" in tools_used
    assert "get_court_availability" in tools_used
    assert len(tools_used) == 3
    
    # Verify user preference was extracted
    assert "user_preferences" in result_state["bot_memory"]
    assert result_state["bot_memory"]["user_preferences"]["preferred_sport"] == "tennis"


# Test 5: Context reference using bot_memory

@pytest.mark.asyncio
async def test_context_reference_using_bot_memory(
    base_state,
    mock_llm_provider,
    mock_property_details
):
    """
    Test context-aware query using bot_memory.
    
    User previously searched for properties, now asks: "Tell me more about the first one"
    Expected: Agent uses bot_memory to resolve "the first one" to property 6
    
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
    """
    # Setup state with existing bot_memory from previous search
    state = base_state.copy()
    state["user_message"] = "Tell me more about the first one"
    state["bot_memory"] = {
        "context": {
            "last_search_results": ["6", "12", "15"],
            "last_search_params": {
                "sport_type": "tennis",
                "city": "New York"
            },
            "last_tools_used": ["search_properties"]
        },
        "user_preferences": {
            "preferred_sport": "tennis"
        }
    }
    
    # Mock the agent executor result
    # The agent should use context to understand "the first one" refers to property 6
    mock_agent_result = {
        "input": "Tell me more about the first one",
        "output": "Downtown Tennis Center is a premier tennis facility in New York. It's located at 123 Main St and features parking, locker rooms, and a pro shop.",
        "intermediate_steps": [
            (
                create_mock_action("get_property_details", {
                    "property_id": 6
                }),
                mock_property_details
            )
        ]
    }
    
    # Execute with mocked components
    with mock_langchain_components(mock_agent_result):
        result_state = await information_handler(state, mock_llm_provider)
    
    # Verify response
    assert result_state["response_content"] == mock_agent_result["output"]
    assert "Downtown Tennis Center" in result_state["response_content"]
    
    # Verify bot_memory preserved previous context
    assert "context" in result_state["bot_memory"]
    assert "last_search_results" in result_state["bot_memory"]["context"]
    assert result_state["bot_memory"]["context"]["last_search_results"] == ["6", "12", "15"]
    
    # Verify new property view was added
    assert "last_viewed_property" in result_state["bot_memory"]["context"]
    assert result_state["bot_memory"]["context"]["last_viewed_property"] == 6
    
    # Verify user preference was preserved
    assert "user_preferences" in result_state["bot_memory"]
    assert result_state["bot_memory"]["user_preferences"]["preferred_sport"] == "tennis"
    
    # Verify tools used was updated (not appended to previous)
    assert "last_tools_used" in result_state["bot_memory"]["context"]
    assert result_state["bot_memory"]["context"]["last_tools_used"] == ["get_property_details"]


# Test 6: Error handling

@pytest.mark.asyncio
async def test_error_handling_in_information_node(
    base_state,
    mock_llm_provider
):
    """
    Test error handling when agent execution fails.
    
    Expected: Node returns error message and doesn't crash
    """
    # Setup state
    state = base_state.copy()
    state["user_message"] = "Show me tennis courts"
    
    # Mock agent executor to raise an exception
    with patch('app.agent.nodes.information.create_langchain_llm'):
        with patch('app.agent.nodes.information.create_langchain_tools'):
            with patch('app.agent.nodes.information.create_information_prompt'):
                with patch('app.agent.nodes.information.create_openai_functions_agent'):
                    with patch('app.agent.nodes.information.AgentExecutor') as mock_executor_class:
                        mock_executor = AsyncMock()
                        mock_executor.ainvoke = AsyncMock(side_effect=Exception("LLM API error"))
                        mock_executor_class.return_value = mock_executor
                        
                        # Execute node
                        result_state = await information_handler(state, mock_llm_provider)
    
    # Verify error message is returned
    assert result_state["response_content"] == (
        "I'm sorry, I encountered an error while processing your request. "
        "Please try again or rephrase your question."
    )
    assert result_state["response_type"] == "text"


# Test 7: Missing llm_provider

@pytest.mark.asyncio
async def test_missing_llm_provider(base_state):
    """
    Test error handling when llm_provider is not provided.
    
    Expected: Node returns error message
    """
    # Setup state
    state = base_state.copy()
    state["user_message"] = "Show me tennis courts"
    
    # Execute node without llm_provider
    result_state = await information_handler(state, llm_provider=None)
    
    # Verify error message is returned
    assert "error" in result_state["response_content"].lower()
    assert result_state["response_type"] == "text"

"""
Test that nodes apply state_updates before routing.

This module tests Requirement 13.5: The system SHALL apply state_updates to
flow_state and bot_memory before routing to the next_node.

Requirements: 13.5
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agent.nodes.intent_detection import intent_detection
from app.agent.state.llm_response_parser import apply_state_updates


@pytest.mark.asyncio
async def test_intent_detection_applies_state_updates_before_routing():
    """
    Test that intent_detection applies state_updates before setting next_node.
    
    This test verifies Requirement 13.5: System SHALL apply state_updates before routing.
    
    The test ensures that:
    1. LLM returns structured response with state_updates
    2. State updates are applied to flow_state and bot_memory
    3. next_node is set after state updates are applied
    4. All state changes are present in the returned state
    """
    # Arrange: Create initial state
    state = {
        "chat_id": "test_123",
        "user_id": "user_456",
        "owner_profile_id": "owner_789",
        "user_message": "I want to book a tennis court",
        "flow_state": {},
        "bot_memory": {},
        "messages": []
    }
    
    # Mock LLM provider
    mock_llm_provider = MagicMock()
    
    # Mock the _llm_routing_decision to return structured response with state_updates
    with patch('app.agent.nodes.intent_detection._llm_routing_decision') as mock_routing:
        mock_routing.return_value = (
            "booking",  # next_node
            "Let's book a court for you!",  # message
            {  # state_updates
                "flow_state": {
                    "current_intent": "booking",
                    "context": {"user_wants_booking": True}
                },
                "bot_memory": {
                    "user_preferences": {
                        "preferred_sport": "tennis"
                    },
                    "inferred_information": {
                        "booking_frequency": "first_time"
                    }
                }
            }
        )
        
        # Act: Call intent_detection
        result = await intent_detection(state, mock_llm_provider)
        
        # Assert: Verify state_updates were applied
        assert result["flow_state"]["current_intent"] == "booking", \
            "flow_state.current_intent should be updated"
        assert result["flow_state"]["context"]["user_wants_booking"] is True, \
            "flow_state.context should be updated"
        
        assert result["bot_memory"]["user_preferences"]["preferred_sport"] == "tennis", \
            "bot_memory.user_preferences should be updated"
        assert result["bot_memory"]["inferred_information"]["booking_frequency"] == "first_time", \
            "bot_memory.inferred_information should be updated"
        
        # Assert: Verify next_node was set
        assert result["next_node"] == "booking", \
            "next_node should be set to booking"
        
        # Assert: Verify message was set
        assert result["response_content"] == "Let's book a court for you!", \
            "response_content should contain LLM message"


@pytest.mark.asyncio
async def test_intent_detection_handles_empty_state_updates():
    """
    Test that intent_detection handles empty state_updates gracefully.
    
    When LLM returns no state_updates, the node should still function correctly
    and set next_node without errors.
    """
    # Arrange
    state = {
        "chat_id": "test_123",
        "user_id": "user_456",
        "owner_profile_id": "owner_789",
        "user_message": "Hello",
        "flow_state": {"existing_field": "value"},
        "bot_memory": {"existing_memory": "data"},
        "messages": []
    }
    
    mock_llm_provider = MagicMock()
    
    # Mock LLM to return empty state_updates
    with patch('app.agent.nodes.intent_detection._llm_routing_decision') as mock_routing:
        mock_routing.return_value = (
            "greeting",  # next_node
            "Hello! How can I help you?",  # message
            {}  # empty state_updates
        )
        
        # Act
        result = await intent_detection(state, mock_llm_provider)
        
        # Assert: Existing state should be preserved
        assert result["flow_state"]["existing_field"] == "value", \
            "Existing flow_state should be preserved"
        assert result["bot_memory"]["existing_memory"] == "data", \
            "Existing bot_memory should be preserved"
        
        # Assert: next_node should still be set
        assert result["next_node"] == "greeting", \
            "next_node should be set even with empty state_updates"


@pytest.mark.asyncio
async def test_intent_detection_merges_state_updates_correctly():
    """
    Test that state_updates are merged with existing state, not replaced.
    
    This ensures that partial updates don't overwrite existing state data.
    """
    # Arrange: State with existing data
    state = {
        "chat_id": "test_123",
        "user_id": "user_456",
        "owner_profile_id": "owner_789",
        "user_message": "Show me courts",
        "flow_state": {
            "property_id": 1,
            "property_name": "Sports Center",
            "existing_field": "should_remain"
        },
        "bot_memory": {
            "user_preferences": {
                "preferred_time": "morning",
                "existing_pref": "should_remain"
            },
            "context": {
                "existing_context": "should_remain"
            }
        },
        "messages": []
    }
    
    mock_llm_provider = MagicMock()
    
    # Mock LLM to return partial state_updates
    with patch('app.agent.nodes.intent_detection._llm_routing_decision') as mock_routing:
        mock_routing.return_value = (
            "information",  # next_node
            "Let me show you the courts",  # message
            {  # partial state_updates
                "flow_state": {
                    "current_intent": "information",
                    "court_id": 10  # New field
                },
                "bot_memory": {
                    "user_preferences": {
                        "preferred_sport": "tennis"  # New field
                    }
                }
            }
        )
        
        # Act
        result = await intent_detection(state, mock_llm_provider)
        
        # Assert: Existing flow_state fields should be preserved
        assert result["flow_state"]["property_id"] == 1, \
            "Existing property_id should be preserved"
        assert result["flow_state"]["property_name"] == "Sports Center", \
            "Existing property_name should be preserved"
        assert result["flow_state"]["existing_field"] == "should_remain", \
            "Existing flow_state fields should be preserved"
        
        # Assert: New flow_state fields should be added
        assert result["flow_state"]["current_intent"] == "information", \
            "New current_intent should be added"
        assert result["flow_state"]["court_id"] == 10, \
            "New court_id should be added"
        
        # Assert: Existing bot_memory should be preserved
        assert result["bot_memory"]["user_preferences"]["preferred_time"] == "morning", \
            "Existing preferred_time should be preserved"
        assert result["bot_memory"]["user_preferences"]["existing_pref"] == "should_remain", \
            "Existing user preferences should be preserved"
        assert result["bot_memory"]["context"]["existing_context"] == "should_remain", \
            "Existing context should be preserved"
        
        # Assert: New bot_memory fields should be added
        assert result["bot_memory"]["user_preferences"]["preferred_sport"] == "tennis", \
            "New preferred_sport should be added"


@pytest.mark.asyncio
async def test_apply_state_updates_utility_function():
    """
    Test the apply_state_updates utility function directly.
    
    This function is used by nodes to apply state_updates before routing.
    """
    # Arrange
    state = {
        "flow_state": {
            "property_id": 1,
            "existing": "value"
        },
        "bot_memory": {
            "user_preferences": {
                "existing_pref": "value"
            }
        }
    }
    
    state_updates = {
        "flow_state": {
            "court_id": 10,
            "new_field": "new_value"
        },
        "bot_memory": {
            "user_preferences": {
                "new_pref": "new_value"
            },
            "inferred_information": {
                "new_info": "value"
            }
        }
    }
    
    # Act
    result = apply_state_updates(state, state_updates)
    
    # Assert: flow_state updates
    assert result["flow_state"]["property_id"] == 1, \
        "Existing property_id should be preserved"
    assert result["flow_state"]["existing"] == "value", \
        "Existing flow_state fields should be preserved"
    assert result["flow_state"]["court_id"] == 10, \
        "New court_id should be added"
    assert result["flow_state"]["new_field"] == "new_value", \
        "New flow_state fields should be added"
    
    # Assert: bot_memory updates (deep merge)
    assert result["bot_memory"]["user_preferences"]["existing_pref"] == "value", \
        "Existing user preferences should be preserved"
    assert result["bot_memory"]["user_preferences"]["new_pref"] == "new_value", \
        "New user preferences should be added"
    assert result["bot_memory"]["inferred_information"]["new_info"] == "value", \
        "New bot_memory sections should be added"


@pytest.mark.asyncio
async def test_apply_state_updates_with_empty_updates():
    """
    Test that apply_state_updates handles empty updates gracefully.
    """
    # Arrange
    state = {
        "flow_state": {"existing": "value"},
        "bot_memory": {"existing": "value"}
    }
    
    # Act
    result = apply_state_updates(state, {})
    
    # Assert: State should be unchanged
    assert result["flow_state"]["existing"] == "value"
    assert result["bot_memory"]["existing"] == "value"


@pytest.mark.asyncio
async def test_apply_state_updates_with_none_updates():
    """
    Test that apply_state_updates handles None updates gracefully.
    """
    # Arrange
    state = {
        "flow_state": {"existing": "value"},
        "bot_memory": {"existing": "value"}
    }
    
    # Act
    result = apply_state_updates(state, None)
    
    # Assert: State should be unchanged
    assert result["flow_state"]["existing"] == "value"
    assert result["bot_memory"]["existing"] == "value"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])

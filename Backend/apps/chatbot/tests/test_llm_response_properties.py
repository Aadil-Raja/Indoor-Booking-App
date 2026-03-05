"""
Property-based tests for LLM response structure.

This module contains property tests that verify universal correctness properties
of LLM responses across all valid inputs using hypothesis library.

Requirements: 2.1, 13.1, 13.3, 13.4
"""

import pytest
from hypothesis import given, settings, strategies as st
from typing import Dict, Any

from apps.chatbot.app.agent.state.llm_response_parser import (
    parse_llm_response,
    validate_llm_response_structure,
    VALID_NEXT_NODES,
    LLMResponseParseError
)


# Strategy for generating valid next_node values
valid_next_node_strategy = st.sampled_from(list(VALID_NEXT_NODES))

# Strategy for generating invalid next_node values
invalid_next_node_strategy = st.text().filter(lambda x: x not in VALID_NEXT_NODES)

# Strategy for generating message strings
message_strategy = st.text(min_size=1)

# Strategy for generating state_updates dictionaries
state_updates_strategy = st.fixed_dictionaries(
    {},
    optional={
        "flow_state": st.dictionaries(st.text(), st.one_of(st.text(), st.integers(), st.none())),
        "bot_memory": st.dictionaries(st.text(), st.one_of(st.text(), st.integers(), st.none()))
    }
)


# Feature: llm-driven-conversation, Property 1: LLM Response Structure Completeness
class TestLLMResponseStructureCompleteness:
    """
    Property 1: LLM Response Structure Completeness
    
    For any LLM invocation in the chatbot system, the response SHALL contain a next_node 
    field with one of the valid values ("greeting", "information", "booking"), a message 
    field containing text for the user, and a state_updates field containing updates to 
    flow_state or bot_memory.
    
    Validates: Requirements 2.1, 13.1, 13.3, 13.4
    """
    
    @given(
        next_node=valid_next_node_strategy,
        message=message_strategy,
        state_updates=state_updates_strategy
    )
    @settings(max_examples=100)
    def test_valid_llm_response_structure(
        self,
        next_node: str,
        message: str,
        state_updates: Dict[str, Any]
    ):
        """
        Test that valid LLM responses with all required fields are parsed correctly.
        
        This test generates random valid LLM responses and verifies that:
        1. The response contains all required fields (next_node, message, state_updates)
        2. The next_node value is one of the valid values
        3. The message is a non-empty string
        4. The state_updates is a dictionary
        """
        llm_response = {
            "next_node": next_node,
            "message": message,
            "state_updates": state_updates
        }
        
        # Parse the response
        parsed_next_node, parsed_message, parsed_state_updates = parse_llm_response(
            llm_response,
            current_node="greeting",
            strict=True
        )
        
        # Verify all fields are present and correct
        assert parsed_next_node == next_node
        assert parsed_next_node in VALID_NEXT_NODES
        assert parsed_message == message
        assert isinstance(parsed_message, str)
        assert len(parsed_message) > 0
        assert parsed_state_updates == state_updates
        assert isinstance(parsed_state_updates, dict)
    
    @given(
        next_node=valid_next_node_strategy,
        message=st.text(min_size=1).filter(lambda x: len(x.strip()) > 0)
    )
    @settings(max_examples=100)
    def test_llm_response_without_state_updates(
        self,
        next_node: str,
        message: str
    ):
        """
        Test that LLM responses without state_updates field default to empty dict.
        
        This verifies that state_updates is optional and defaults to an empty dictionary
        when not provided.
        """
        llm_response = {
            "next_node": next_node,
            "message": message
            # state_updates is missing
        }
        
        # Parse the response (non-strict mode)
        parsed_next_node, parsed_message, parsed_state_updates = parse_llm_response(
            llm_response,
            current_node="greeting",
            strict=False
        )
        
        # Verify state_updates defaults to empty dict
        assert parsed_next_node == next_node
        assert parsed_message == message
        assert parsed_state_updates == {}
        assert isinstance(parsed_state_updates, dict)
    
    @given(
        message=message_strategy,
        state_updates=state_updates_strategy,
        current_node=valid_next_node_strategy
    )
    @settings(max_examples=100)
    def test_missing_next_node_defaults_to_current(
        self,
        message: str,
        state_updates: Dict[str, Any],
        current_node: str
    ):
        """
        Test that missing next_node defaults to current node (Requirement 2.5).
        
        This verifies the fallback behavior when the LLM fails to provide a next_node.
        """
        llm_response = {
            "message": message,
            "state_updates": state_updates
            # next_node is missing
        }
        
        # Parse the response (non-strict mode)
        parsed_next_node, parsed_message, parsed_state_updates = parse_llm_response(
            llm_response,
            current_node=current_node,
            strict=False
        )
        
        # Verify next_node defaults to current_node
        assert parsed_next_node == current_node
        assert parsed_message == message
        assert parsed_state_updates == state_updates
    
    @given(
        invalid_next_node=invalid_next_node_strategy,
        message=message_strategy,
        state_updates=state_updates_strategy
    )
    @settings(max_examples=100)
    def test_invalid_next_node_defaults_to_greeting(
        self,
        invalid_next_node: str,
        message: str,
        state_updates: Dict[str, Any]
    ):
        """
        Test that invalid next_node values default to 'greeting' (Requirement 13.2).
        
        This verifies that the system handles invalid next_node values gracefully
        by defaulting to a safe value.
        """
        llm_response = {
            "next_node": invalid_next_node,
            "message": message,
            "state_updates": state_updates
        }
        
        # Parse the response (non-strict mode)
        parsed_next_node, parsed_message, parsed_state_updates = parse_llm_response(
            llm_response,
            current_node="information",
            strict=False
        )
        
        # Verify invalid next_node defaults to 'greeting'
        assert parsed_next_node == "greeting"
        assert parsed_message == message
        assert parsed_state_updates == state_updates
    
    @given(
        next_node=valid_next_node_strategy,
        state_updates=state_updates_strategy
    )
    @settings(max_examples=100)
    def test_missing_message_defaults_gracefully(
        self,
        next_node: str,
        state_updates: Dict[str, Any]
    ):
        """
        Test that missing message field is handled gracefully (Requirement 13.3).
        
        This verifies that the system provides a default message when the LLM
        fails to provide one.
        """
        llm_response = {
            "next_node": next_node,
            "state_updates": state_updates
            # message is missing
        }
        
        # Parse the response (non-strict mode)
        parsed_next_node, parsed_message, parsed_state_updates = parse_llm_response(
            llm_response,
            current_node="greeting",
            strict=False
        )
        
        # Verify message has a default value
        assert parsed_next_node == next_node
        assert isinstance(parsed_message, str)
        assert len(parsed_message) > 0
        assert parsed_state_updates == state_updates
    
    @given(
        next_node=valid_next_node_strategy,
        message=st.text(min_size=1).filter(lambda x: len(x.strip()) > 0)
    )
    @settings(max_examples=100)
    def test_state_updates_structure_validation(
        self,
        next_node: str,
        message: str
    ):
        """
        Test that state_updates structure is validated (Requirement 13.4).
        
        This verifies that state_updates must be a dictionary and can only contain
        flow_state and bot_memory keys.
        """
        # Test with valid structure
        valid_state_updates = {
            "flow_state": {"property_id": 123},
            "bot_memory": {"preferred_time": "morning"}
        }
        
        llm_response = {
            "next_node": next_node,
            "message": message,
            "state_updates": valid_state_updates
        }
        
        parsed_next_node, parsed_message, parsed_state_updates = parse_llm_response(
            llm_response,
            current_node="greeting",
            strict=True
        )
        
        assert parsed_state_updates == valid_state_updates
        assert "flow_state" in parsed_state_updates
        assert "bot_memory" in parsed_state_updates
    
    @given(
        next_node=valid_next_node_strategy,
        message=message_strategy,
        invalid_state_updates=st.one_of(
            st.text(),
            st.integers(),
            st.lists(st.text()),
            st.none()
        )
    )
    @settings(max_examples=100)
    def test_invalid_state_updates_type_handled(
        self,
        next_node: str,
        message: str,
        invalid_state_updates: Any
    ):
        """
        Test that non-dictionary state_updates are handled gracefully.
        
        This verifies that the system handles invalid state_updates types
        by defaulting to an empty dictionary.
        """
        llm_response = {
            "next_node": next_node,
            "message": message,
            "state_updates": invalid_state_updates
        }
        
        # Parse the response (non-strict mode)
        parsed_next_node, parsed_message, parsed_state_updates = parse_llm_response(
            llm_response,
            current_node="greeting",
            strict=False
        )
        
        # Verify state_updates defaults to empty dict for invalid types
        assert parsed_next_node == next_node
        assert parsed_message == message
        assert parsed_state_updates == {}
        assert isinstance(parsed_state_updates, dict)
    
    @given(
        next_node=valid_next_node_strategy,
        message=message_strategy,
        state_updates=state_updates_strategy
    )
    @settings(max_examples=100)
    def test_validate_llm_response_structure_function(
        self,
        next_node: str,
        message: str,
        state_updates: Dict[str, Any]
    ):
        """
        Test the validate_llm_response_structure utility function.
        
        This verifies that the validation function correctly identifies valid
        and invalid response structures.
        """
        # Test with valid response
        valid_response = {
            "next_node": next_node,
            "message": message,
            "state_updates": state_updates
        }
        
        assert validate_llm_response_structure(valid_response) is True
        
        # Test with invalid response (missing required field)
        invalid_response = {
            "next_node": next_node
            # missing message and state_updates
        }
        
        assert validate_llm_response_structure(invalid_response) is False


class TestLLMResponseParserEdgeCases:
    """
    Additional edge case tests for LLM response parser.
    
    These tests cover specific edge cases that may not be fully covered by
    property-based tests.
    """
    
    def test_empty_message_string(self):
        """Test that empty message strings are handled."""
        llm_response = {
            "next_node": "greeting",
            "message": "",
            "state_updates": {}
        }
        
        # Non-strict mode should provide default
        parsed_next_node, parsed_message, parsed_state_updates = parse_llm_response(
            llm_response,
            current_node="greeting",
            strict=False
        )
        
        assert parsed_next_node == "greeting"
        assert isinstance(parsed_message, str)
        assert len(parsed_message) > 0  # Should have default message
    
    def test_whitespace_only_message(self):
        """Test that whitespace-only messages are handled."""
        llm_response = {
            "next_node": "greeting",
            "message": "   \n\t  ",
            "state_updates": {}
        }
        
        # Non-strict mode should provide default
        parsed_next_node, parsed_message, parsed_state_updates = parse_llm_response(
            llm_response,
            current_node="greeting",
            strict=False
        )
        
        assert parsed_next_node == "greeting"
        assert isinstance(parsed_message, str)
        assert len(parsed_message.strip()) > 0  # Should have default message
    
    def test_non_dict_llm_response(self):
        """Test that non-dictionary LLM responses are handled."""
        # Test with string
        parsed_next_node, parsed_message, parsed_state_updates = parse_llm_response(
            "invalid response",
            current_node="greeting",
            strict=False
        )
        
        assert parsed_next_node == "greeting"
        assert isinstance(parsed_message, str)
        assert isinstance(parsed_state_updates, dict)
        
        # Test with None
        parsed_next_node, parsed_message, parsed_state_updates = parse_llm_response(
            None,
            current_node="information",
            strict=False
        )
        
        assert parsed_next_node == "information"
        assert isinstance(parsed_message, str)
        assert isinstance(parsed_state_updates, dict)
    
    def test_strict_mode_raises_exceptions(self):
        """Test that strict mode raises exceptions for invalid responses."""
        # Missing next_node
        with pytest.raises(LLMResponseParseError, match="next_node"):
            parse_llm_response(
                {"message": "Hello", "state_updates": {}},
                current_node="greeting",
                strict=True
            )
        
        # Invalid next_node
        with pytest.raises(LLMResponseParseError, match="Invalid next_node"):
            parse_llm_response(
                {"next_node": "invalid", "message": "Hello", "state_updates": {}},
                current_node="greeting",
                strict=True
            )
        
        # Missing message
        with pytest.raises(LLMResponseParseError, match="message"):
            parse_llm_response(
                {"next_node": "greeting", "state_updates": {}},
                current_node="greeting",
                strict=True
            )
        
        # Empty message
        with pytest.raises(LLMResponseParseError, match="empty"):
            parse_llm_response(
                {"next_node": "greeting", "message": "", "state_updates": {}},
                current_node="greeting",
                strict=True
            )
    
    def test_state_updates_with_unexpected_keys(self):
        """Test that state_updates with unexpected keys are handled."""
        llm_response = {
            "next_node": "greeting",
            "message": "Hello",
            "state_updates": {
                "flow_state": {"property_id": 123},
                "bot_memory": {"preferred_time": "morning"},
                "unexpected_key": "unexpected_value"
            }
        }
        
        # Non-strict mode should log warning but continue
        parsed_next_node, parsed_message, parsed_state_updates = parse_llm_response(
            llm_response,
            current_node="greeting",
            strict=False
        )
        
        assert parsed_next_node == "greeting"
        assert parsed_message == "Hello"
        assert "flow_state" in parsed_state_updates
        assert "bot_memory" in parsed_state_updates
    
    def test_nested_state_updates_validation(self):
        """Test that nested flow_state and bot_memory are validated."""
        # Invalid flow_state type
        llm_response = {
            "next_node": "greeting",
            "message": "Hello",
            "state_updates": {
                "flow_state": "not a dict"
            }
        }
        
        parsed_next_node, parsed_message, parsed_state_updates = parse_llm_response(
            llm_response,
            current_node="greeting",
            strict=False
        )
        
        # Should convert invalid flow_state to empty dict
        assert parsed_state_updates["flow_state"] == {}
        
        # Invalid bot_memory type
        llm_response = {
            "next_node": "greeting",
            "message": "Hello",
            "state_updates": {
                "bot_memory": ["not", "a", "dict"]
            }
        }
        
        parsed_next_node, parsed_message, parsed_state_updates = parse_llm_response(
            llm_response,
            current_node="greeting",
            strict=False
        )
        
        # Should convert invalid bot_memory to empty dict
        assert parsed_state_updates["bot_memory"] == {}

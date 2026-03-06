# LLM Node Pattern: Applying State Updates Before Routing

## Overview

This document describes the standard pattern for implementing LangGraph nodes that use structured LLM responses with state updates. Following this pattern ensures that state updates are applied before routing to the next node, as required by Requirement 13.5.

## Requirements

- **Requirement 13.5**: The system SHALL apply state_updates to flow_state and bot_memory before routing to the next_node

## Pattern

When a node uses an LLM to make decisions and the LLM returns a structured response containing `next_node`, `message`, and `state_updates`, the node MUST:

1. Parse the LLM response using `parse_llm_response()`
2. Apply state updates using `apply_state_updates()` BEFORE setting `next_node`
3. Set `next_node` for routing
4. Return the updated state

## Code Template

```python
from typing import Optional
import logging

from app.agent.state.conversation_state import ConversationState
from app.services.llm.base import LLMProvider
from app.agent.state.llm_response_parser import parse_llm_response, apply_state_updates

logger = logging.getLogger(__name__)


async def example_node(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState:
    """
    Example node that uses structured LLM responses.
    
    This node demonstrates the correct pattern for applying state updates
    before routing to the next node.
    
    Implements Requirement 13.5: Apply state_updates before routing
    """
    user_message = state["user_message"]
    chat_id = state["chat_id"]
    
    # Step 1: Call LLM and get structured response
    llm_response = await _call_llm(user_message, llm_provider, chat_id)
    
    # Step 2: Parse LLM response to extract next_node, message, and state_updates
    next_node, message, state_updates = parse_llm_response(
        llm_response,
        current_node="example_node",
        strict=False
    )
    
    # Step 3: CRITICAL - Apply state updates BEFORE setting next_node
    # This ensures state is updated before routing to the next node
    state = apply_state_updates(state, state_updates)
    
    # Step 4: Set next_node for routing
    state["next_node"] = next_node
    
    # Step 5: Set response content
    if message:
        state["response_content"] = message
        state["response_type"] = "text"
        state["response_metadata"] = {}
    
    logger.info(
        f"Node completed for chat {chat_id}: next_node={next_node}, "
        f"state_updates_applied={bool(state_updates)}"
    )
    
    return state


async def _call_llm(
    user_message: str,
    llm_provider: LLMProvider,
    chat_id: str
) -> dict:
    """
    Call LLM and return structured response.
    
    The LLM should return a JSON response with the following structure:
    {
        "next_node": "greeting" | "information" | "booking",
        "message": "Response text for the user",
        "state_updates": {
            "flow_state": {
                "current_intent": "booking",
                "property_id": 123,
                ...
            },
            "bot_memory": {
                "user_preferences": {
                    "preferred_time": "morning"
                },
                ...
            }
        }
    }
    """
    # Implementation details...
    pass
```

## Current Implementation

### Nodes Using This Pattern

1. **intent_detection** (`app/agent/nodes/intent_detection.py`)
   - Uses structured LLM responses
   - Applies state_updates before routing
   - ✅ Correctly implements the pattern

### Nodes NOT Using This Pattern

The following nodes use rule-based logic or LangChain agents without structured state_updates:

1. **greeting_handler** - Rule-based, no LLM routing decisions
2. **information_handler** - Uses LangChain agent, determines next_node via rule-based logic
3. **Booking nodes** (select_property, select_court, select_date, select_time, confirm_booking, create_booking)
   - Use rule-based logic for routing
   - Some use LLM for parsing (e.g., date parsing) but not for routing decisions

## Migration Guide

If you need to migrate a node to use structured LLM responses with state_updates:

### Before (Rule-based routing)

```python
async def my_node(state: ConversationState) -> ConversationState:
    # Process logic
    result = process_something(state["user_message"])
    
    # Rule-based routing
    if "book" in state["user_message"].lower():
        state["next_node"] = "booking"
    else:
        state["next_node"] = "information"
    
    return state
```

### After (LLM-based routing with state_updates)

```python
async def my_node(
    state: ConversationState,
    llm_provider: Optional[LLMProvider] = None
) -> ConversationState:
    # Call LLM with structured prompt
    llm_response = await _call_llm_for_routing(
        state["user_message"],
        llm_provider,
        state["chat_id"]
    )
    
    # Parse response
    next_node, message, state_updates = parse_llm_response(
        llm_response,
        current_node="my_node",
        strict=False
    )
    
    # CRITICAL: Apply state updates BEFORE routing
    state = apply_state_updates(state, state_updates)
    
    # Set next_node
    state["next_node"] = next_node
    
    if message:
        state["response_content"] = message
    
    return state
```

## Testing

When testing nodes that use this pattern, verify:

1. State updates are applied before next_node is set
2. flow_state updates are merged correctly
3. bot_memory updates are merged correctly (deep merge for nested dicts)
4. Routing works correctly after state updates are applied

Example test:

```python
async def test_state_updates_applied_before_routing():
    """Test that state_updates are applied before routing (Requirement 13.5)"""
    state = {
        "chat_id": "123",
        "user_message": "I want to book a court",
        "flow_state": {},
        "bot_memory": {},
        ...
    }
    
    # Mock LLM to return structured response with state_updates
    with mock.patch('_call_llm') as mock_llm:
        mock_llm.return_value = {
            "next_node": "booking",
            "message": "Let's book a court",
            "state_updates": {
                "flow_state": {
                    "current_intent": "booking",
                    "property_id": 123
                },
                "bot_memory": {
                    "user_preferences": {
                        "preferred_sport": "tennis"
                    }
                }
            }
        }
        
        result = await my_node(state, llm_provider)
        
        # Verify state updates were applied
        assert result["flow_state"]["current_intent"] == "booking"
        assert result["flow_state"]["property_id"] == 123
        assert result["bot_memory"]["user_preferences"]["preferred_sport"] == "tennis"
        
        # Verify routing
        assert result["next_node"] == "booking"
```

## References

- Design Document: `Indoor-Booking-App/.kiro/specs/llm-driven-conversation/design.md`
- Requirements: `Indoor-Booking-App/.kiro/specs/llm-driven-conversation/requirements.md`
- LLM Response Parser: `app/agent/state/llm_response_parser.py`
- Intent Detection Node (reference implementation): `app/agent/nodes/intent_detection.py`

"""
Check requirements node - determines what's needed for requested actions.

This node checks if all required inputs exist for the requested actions.
If something is missing, it decides which question to ask next.

Important rule: Ask for only ONE missing thing at a time.
"""

import logging
from typing import Dict, Any, Optional

from app.agent.state.conversation_state import ConversationState
from app.agent.utils.llm_logger import get_llm_logger

logger = logging.getLogger(__name__)


# Action requirements map
ACTION_REQUIREMENTS = {
    "property_details": {"property": True, "court": False},
    "court_details": {"property": True, "court": True},
    "pricing": {"property": True, "court": True},
    "media": {"property": True, "court": False},  # Media works with just property (gets property + court media)
}


async def check_requirements(
    state: ConversationState,
    tools: Dict[str, Any] = None
) -> ConversationState:
    """
    Check if all required inputs exist for requested actions.
    
    This node:
    1. Gets requested_actions from flow_state
    2. Checks ACTION_REQUIREMENTS for each action
    3. Determines what's missing (property or court)
    4. Sets next_step to ask for ONE missing thing
    5. Important: Ask for only ONE thing at a time (property first, then court)
    
    Args:
        state: Current conversation state
        tools: Tool registry (not used)
        
    Returns:
        Updated state with next_step set
    """
    chat_id = state.get("chat_id")
    flow_state = state.get("flow_state", {})
    
    logger.info(f"Checking requirements for chat {chat_id}")
    
    # Get current state
    requested_actions = flow_state.get("requested_actions", [])
    property_id = flow_state.get("property_id")
    court_ids = flow_state.get("court_ids", [])
    
    logger.debug(
        f"Current state for chat {chat_id}: "
        f"actions={requested_actions}, property_id={property_id}, court_ids={court_ids}"
    )
    
    # If no actions requested, nothing to check
    if not requested_actions:
        logger.info(f"No actions requested for chat {chat_id}")
        
        # Requirement 4: If property or court is selected and no actions, suggest showing details
        if property_id or court_ids:
            # User has selected property/court but didn't request any specific action
            # Offer to show details, location, media
            flow_state["next_step"] = "show_available_actions"
            flow_state["last_node"] = "information-check_requirements"
            state["flow_state"] = flow_state
            logger.info(f"Property/court selected with no actions, routing to show_available_actions")
            return state
        
        # No property/court selected and no actions - show available options
        flow_state["next_step"] = "show_available_actions"
        flow_state["last_node"] = "information-check_requirements"
        state["flow_state"] = flow_state
        return state
    
    # Split actions into executable now vs needs more info
    executable_now = []
    needs_property_actions = []
    needs_court_actions = []
    
    for action in requested_actions:
        requirements = ACTION_REQUIREMENTS.get(action, {})
        needs_property = requirements.get("property", False)
        needs_court = requirements.get("court", False)
        
        # Check if action can be executed with current state
        can_execute = True
        
        if needs_property and not property_id:
            can_execute = False
            needs_property_actions.append(action)
        elif needs_court and not court_ids:
            can_execute = False
            needs_court_actions.append(action)
        
        if can_execute:
            executable_now.append(action)
    
    logger.debug(
        f"Action split for chat {chat_id}: "
        f"executable_now={executable_now}, "
        f"needs_property={needs_property_actions}, "
        f"needs_court={needs_court_actions}"
    )
    
    # Determine next step with partial execution support
    # Priority: property first, then court, then execute
    
    # Check if user was replying to a question (from router_result)
    router_result = flow_state.get("router_result", {})
    is_replying = router_result.get("reply_target") in ["property_selection", "court_selection"]
    
    # Get old pending actions (before we update)
    old_pending_actions = flow_state.get("pending_actions", [])
    
    if needs_property_actions:
        # Some actions need property
        if executable_now:
            # Execute ready actions first, then ask for property
            logger.info(
                f"Property missing for chat {chat_id}. "
                f"Will execute {executable_now} then ask for property"
            )
            flow_state["next_step"] = "execute_actions"
            flow_state["after_execute"] = "ask_property"
        else:
            # Nothing to execute, just ask
            logger.info(f"Property missing for chat {chat_id}, routing to ask_property")
            flow_state["next_step"] = "ask_property"
            flow_state["after_execute"] = None
        
        # Keep executable actions in requested_actions for immediate execution
        flow_state["requested_actions"] = executable_now
        
        # Set NEW pending actions (actions that need property/court)
        new_pending_actions = needs_property_actions + needs_court_actions
        flow_state["pending_actions"] = new_pending_actions
        
        # Save pending action params for NEW pending actions
        pending_action_params = {}
        if "property_details" in new_pending_actions:
            pending_action_params["property_details"] = {
                "property_detail_fields": flow_state.get("property_detail_fields", ["all"])
            }
        if "court_details" in new_pending_actions:
            pending_action_params["court_details"] = {
                "court_detail_fields": flow_state.get("court_detail_fields", ["all"])
            }
        flow_state["pending_action_params"] = pending_action_params
        
        # SMART CLEAR: If user asked something new (not replying) and we executed something,
        # don't ask about old pending after execution
        if executable_now and not is_replying and old_pending_actions:
            logger.info(
                f"User asked new action with partial execution - will not ask about old pending after execution for chat {chat_id}: "
                f"old_pending={old_pending_actions}, new_pending={new_pending_actions}"
            )
            # Clear after_execute so we don't ask about old pending
            # The NEW pending actions are already set above
            if set(new_pending_actions) == set(old_pending_actions):
                # Same actions, keep asking
                pass
            else:
                # Different actions, user moved on - don't continue old flow
                flow_state["after_execute"] = None
        
    elif needs_court_actions:
        # Some actions need court (property exists)
        if executable_now:
            # Execute ready actions first, then ask for court
            logger.info(
                f"Court missing for chat {chat_id}. "
                f"Will execute {executable_now} then ask for court"
            )
            flow_state["next_step"] = "execute_actions"
            flow_state["after_execute"] = "ask_court"
        else:
            # Nothing to execute, just ask
            logger.info(f"Court missing for chat {chat_id}, routing to ask_court")
            flow_state["next_step"] = "ask_court"
            flow_state["after_execute"] = None
        
        # Keep executable actions in requested_actions for immediate execution
        flow_state["requested_actions"] = executable_now
        
        # Set NEW pending actions (actions that need court)
        new_pending_actions = needs_court_actions
        flow_state["pending_actions"] = new_pending_actions
        
        # Save pending action params for NEW pending actions
        pending_action_params = {}
        if "property_details" in new_pending_actions:
            pending_action_params["property_details"] = {
                "property_detail_fields": flow_state.get("property_detail_fields", ["all"])
            }
        if "court_details" in new_pending_actions:
            pending_action_params["court_details"] = {
                "court_detail_fields": flow_state.get("court_detail_fields", ["all"])
            }
        flow_state["pending_action_params"] = pending_action_params
        
        # SMART CLEAR: If user asked something new (not replying) and we executed something,
        # don't ask about old pending after execution
        if executable_now and not is_replying and old_pending_actions:
            logger.info(
                f"User asked new action with partial execution - will not ask about old pending after execution for chat {chat_id}: "
                f"old_pending={old_pending_actions}, new_pending={new_pending_actions}"
            )
            # Clear after_execute so we don't ask about old pending
            # The NEW pending actions are already set above
            if set(new_pending_actions) == set(old_pending_actions):
                # Same actions, keep asking
                pass
            else:
                # Different actions, user moved on - don't continue old flow
                flow_state["after_execute"] = None
        
    else:
        # All actions can be executed
        logger.info(f"All requirements met for chat {chat_id}, routing to execute")
        flow_state["next_step"] = "execute_actions"
        flow_state["after_execute"] = None
        flow_state["requested_actions"] = executable_now
        
        # Don't clear pending_actions here - let execute_actions handle it after successful execution
        # This ensures pending actions are preserved if execution fails
    
    # Track last node
    flow_state["last_node"] = "information-check_requirements"
    state["flow_state"] = flow_state
    
    # Log requirements check result
    llm_logger = get_llm_logger()
    requirements_summary = (
        f"Requested Actions: {requested_actions}\n"
        f"Action Split:\n"
        f"  Executable Now: {flow_state.get('requested_actions', [])}\n"
        f"  Pending (need more info): {flow_state.get('pending_actions', [])}\n"
        f"Current State:\n"
        f"  Have Property: {property_id is not None}\n"
        f"  Have Court: {len(court_ids) > 0}\n"
        f"Decision: {flow_state.get('next_step')}"
    )
    llm_logger.log_llm_call(
        node_name="check_requirements",
        prompt="[No LLM call - checks requirements and splits actions into executable vs pending]",
        response=requirements_summary,
        parameters=None
    )
    
    logger.info(
        f"[CHECK REQUIREMENTS RESULT] Chat {chat_id}:\n"
        f"  Original Actions: {requested_actions}\n"
        f"  Executable Now: {flow_state.get('requested_actions', [])}\n"
        f"  Pending: {flow_state.get('pending_actions', [])}\n"
        f"  Have Property: {property_id is not None}\n"
        f"  Have Court: {len(court_ids) > 0}\n"
        f"  Next Step: {flow_state.get('next_step')}"
    )
    
    return state

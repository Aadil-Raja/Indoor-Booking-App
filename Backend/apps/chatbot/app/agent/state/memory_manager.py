"""
Bot memory manager for updating conversation context.

This module provides utilities for updating bot_memory based on agent execution results.
It extracts information from LangChain agent intermediate steps to maintain conversation
context, user preferences, and recent interactions.
"""

from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


def update_bot_memory(
    bot_memory: Dict[str, Any],
    agent_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update bot_memory with information from agent execution.
    
    This function extracts intermediate_steps from the agent result to identify
    which tools were called and what data was retrieved. It updates bot_memory
    with relevant context for future interactions.
    
    Stores:
    - Last search results (property IDs)
    - Last search parameters
    - User preferences (sport type)
    - Last viewed property/court
    - Last availability check
    - Last tools used
    
    Args:
        bot_memory: Current bot memory dictionary
        agent_result: Result from LangChain AgentExecutor.ainvoke()
                     Contains 'intermediate_steps' with (action, observation) tuples
    
    Returns:
        Updated bot_memory dictionary
    
    Requirements: 1.2, 1.5, 5.5, 8.1, 8.2, 8.3, 11.2, 11.3
    """
    # Initialize context if not present
    if "context" not in bot_memory:
        bot_memory["context"] = {}
    
    # Extract intermediate steps to see which tools were called
    intermediate_steps = agent_result.get("intermediate_steps", [])
    
    if not intermediate_steps:
        logger.debug("No intermediate steps found in agent result")
        return bot_memory
    
    # Track tools used in this interaction
    tools_used = []
    
    for action, observation in intermediate_steps:
        try:
            # Extract tool information
            tool_name = action.tool
            tool_input = action.tool_input
            
            tools_used.append(tool_name)
            logger.debug(f"Processing tool: {tool_name} with input: {tool_input}")
            
            # Handle search_properties tool
            if tool_name == "search_properties" and observation:
                _handle_search_properties(bot_memory, tool_input, observation)
            
            # Handle get_property_details tool
            elif tool_name == "get_property_details" and tool_input:
                _handle_property_details(bot_memory, tool_input)
            
            # Handle get_court_details tool
            elif tool_name == "get_court_details" and tool_input:
                _handle_court_details(bot_memory, tool_input)
            
            # Handle get_court_availability tool
            elif tool_name == "get_court_availability" and tool_input:
                _handle_court_availability(bot_memory, tool_input)
                
        except Exception as e:
            logger.error(f"Error processing tool {action.tool}: {e}", exc_info=True)
            continue
    
    # Store list of tools used in this interaction
    if tools_used:
        bot_memory["context"]["last_tools_used"] = tools_used
        logger.debug(f"Updated last_tools_used: {tools_used}")
    
    return bot_memory


def _handle_search_properties(
    bot_memory: Dict[str, Any],
    tool_input: Dict[str, Any],
    observation: Any
) -> None:
    """
    Handle search_properties tool results.
    
    Stores:
    - Property IDs from search results
    - Search parameters used
    - User's preferred sport if specified
    
    Args:
        bot_memory: Bot memory dictionary to update
        tool_input: Input parameters passed to the tool
        observation: Tool execution result (list of properties)
    """
    try:
        # Extract property IDs from search results
        if isinstance(observation, list):
            property_ids = [str(p["id"]) for p in observation if isinstance(p, dict) and "id" in p]
            if property_ids:
                bot_memory["context"]["last_search_results"] = property_ids
                logger.info(f"Stored search results: {len(property_ids)} properties")
        
        # Store search parameters for context
        if tool_input:
            bot_memory["context"]["last_search_params"] = {
                k: v for k, v in tool_input.items() 
                if v is not None and k != "owner_profile_id"  # Don't store owner_profile_id
            }
            logger.debug(f"Stored search params: {bot_memory['context']['last_search_params']}")
        
        # Update user preferences if sport type was searched
        if tool_input.get("sport_type"):
            if "user_preferences" not in bot_memory:
                bot_memory["user_preferences"] = {}
            bot_memory["user_preferences"]["preferred_sport"] = tool_input["sport_type"]
            logger.info(f"Updated preferred sport: {tool_input['sport_type']}")
            
    except Exception as e:
        logger.error(f"Error handling search_properties: {e}", exc_info=True)


def _handle_property_details(
    bot_memory: Dict[str, Any],
    tool_input: Dict[str, Any]
) -> None:
    """
    Handle get_property_details tool results.
    
    Stores the last viewed property ID for context reference.
    
    Args:
        bot_memory: Bot memory dictionary to update
        tool_input: Input parameters passed to the tool
    """
    try:
        property_id = tool_input.get("property_id")
        if property_id is not None:
            bot_memory["context"]["last_viewed_property"] = property_id
            logger.info(f"Stored last viewed property: {property_id}")
    except Exception as e:
        logger.error(f"Error handling property_details: {e}", exc_info=True)


def _handle_court_details(
    bot_memory: Dict[str, Any],
    tool_input: Dict[str, Any]
) -> None:
    """
    Handle get_court_details tool results.
    
    Stores the last viewed court ID for context reference.
    
    Args:
        bot_memory: Bot memory dictionary to update
        tool_input: Input parameters passed to the tool
    """
    try:
        court_id = tool_input.get("court_id")
        if court_id is not None:
            bot_memory["context"]["last_viewed_court"] = court_id
            logger.info(f"Stored last viewed court: {court_id}")
    except Exception as e:
        logger.error(f"Error handling court_details: {e}", exc_info=True)


def _handle_court_availability(
    bot_memory: Dict[str, Any],
    tool_input: Dict[str, Any]
) -> None:
    """
    Handle get_court_availability tool results.
    
    Stores the court ID and date for which availability was checked.
    
    Args:
        bot_memory: Bot memory dictionary to update
        tool_input: Input parameters passed to the tool
    """
    try:
        court_id = tool_input.get("court_id")
        date = tool_input.get("date")
        
        if court_id is not None and date is not None:
            bot_memory["context"]["last_availability_check"] = {
                "court_id": court_id,
                "date": date
            }
            logger.info(f"Stored availability check: court {court_id} on {date}")
    except Exception as e:
        logger.error(f"Error handling court_availability: {e}", exc_info=True)

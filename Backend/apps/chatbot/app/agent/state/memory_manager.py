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



async def load_bot_memory(
    chat_id: str,
    db_session
) -> Dict[str, Any]:
    """
    Retrieve bot_memory from database with error handling.
    
    Loads the persistent bot_memory for a chat session from the database.
    If the chat doesn't exist or bot_memory is empty, returns an initialized
    empty bot_memory structure. Includes error handling for deserialization errors.
    
    Args:
        chat_id: UUID string of the chat session
        db_session: AsyncSession for database operations
        
    Returns:
        Dict[str, Any]: Bot memory dictionary with conversation_history,
                       user_preferences, and inferred_information
                       
    Example:
        from uuid import UUID
        bot_memory = await load_bot_memory(
            chat_id=str(chat_id),
            db_session=db
        )
        
    Requirements: 4.1, 4.2, 4.6, 15.2, 15.4, 20.2
    """
    from uuid import UUID
    from app.repositories.chat_repository import ChatRepository
    
    try:
        # Convert string to UUID
        try:
            chat_uuid = UUID(chat_id)
        except ValueError as e:
            logger.error(f"Invalid chat_id format: {chat_id}, error: {e}")
            return _initialize_bot_memory()
        
        # Load chat from database
        chat_repo = ChatRepository(db_session)
        chat = await chat_repo.get_by_id(chat_uuid)
        
        if not chat:
            logger.warning(f"Chat not found: {chat_id}, returning empty bot_memory")
            return _initialize_bot_memory()
        
        # Get bot_memory from chat
        bot_memory = chat.bot_memory
        
        if not bot_memory or not isinstance(bot_memory, dict):
            logger.info(f"Empty or invalid bot_memory for chat {chat_id}, initializing")
            return _initialize_bot_memory()
        
        # Ensure required structure exists
        bot_memory = _ensure_bot_memory_structure(bot_memory)
        
        logger.debug(f"Loaded bot_memory for chat {chat_id}")
        return bot_memory
        
    except Exception as e:
        # Handle deserialization errors (Requirement 20.2)
        logger.error(
            f"Error loading bot_memory for chat {chat_id}: {e}",
            exc_info=True
        )
        logger.warning(
            f"Returning empty bot_memory for chat {chat_id} due to load error"
        )
        return _initialize_bot_memory()


async def save_bot_memory(
    chat_id: str,
    bot_memory: Dict[str, Any],
    db_session
) -> bool:
    """
    Persist bot_memory to database with error handling.
    
    Saves the bot_memory dictionary to the database for the specified chat.
    Updates the chat's bot_memory field and commits the transaction.
    Includes comprehensive error handling for persistence failures.
    
    Args:
        chat_id: UUID string of the chat session
        bot_memory: Bot memory dictionary to persist
        db_session: AsyncSession for database operations
        
    Returns:
        bool: True if save successful, False otherwise
        
    Example:
        success = await save_bot_memory(
            chat_id=str(chat_id),
            bot_memory=updated_memory,
            db_session=db
        )
        
    Requirements: 4.1, 4.2, 4.6, 15.2, 15.4, 20.2
    """
    from uuid import UUID
    from app.repositories.chat_repository import ChatRepository
    
    try:
        # Convert string to UUID
        try:
            chat_uuid = UUID(chat_id)
        except ValueError as e:
            logger.error(f"Invalid chat_id format: {chat_id}, error: {e}")
            return False
        
        # Validate bot_memory structure before saving
        if not isinstance(bot_memory, dict):
            logger.error(
                f"Invalid bot_memory type: {type(bot_memory)}, expected dict"
            )
            return False
        
        # Load chat from database
        chat_repo = ChatRepository(db_session)
        chat = await chat_repo.get_by_id(chat_uuid)
        
        if not chat:
            logger.error(f"Cannot save bot_memory: chat not found: {chat_id}")
            return False
        
        # Update chat with new bot_memory
        await chat_repo.update(chat, {"bot_memory": bot_memory})
        
        # Commit is handled by the session context manager
        logger.debug(f"Saved bot_memory for chat {chat_id}")
        return True
        
    except Exception as e:
        # Log error but don't raise - allow conversation to continue (Requirement 20.2)
        logger.error(
            f"Error saving bot_memory for chat {chat_id}: {e}",
            exc_info=True
        )
        logger.warning(
            f"Bot memory will not be persisted for chat {chat_id}, "
            "but conversation can continue"
        )
        return False


def update_bot_memory_preferences(
    bot_memory: Dict[str, Any],
    preferences: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge preference updates into bot_memory.
    
    Updates the user_preferences section of bot_memory with new preference
    values. Performs a shallow merge, updating only the specified preference
    fields while preserving others.
    
    Args:
        bot_memory: Current bot memory dictionary
        preferences: Dictionary of preference updates
                    (preferred_time, preferred_sport, preferred_property, preferred_court)
        
    Returns:
        Dict[str, Any]: Updated bot_memory
        
    Example:
        updated = update_bot_memory_preferences(
            bot_memory=current_memory,
            preferences={"preferred_time": "morning", "preferred_sport": "tennis"}
        )
        
    Requirements: 4.1, 4.2, 4.3, 4.4
    """
    if not isinstance(bot_memory, dict):
        logger.warning("Bot memory is not a dict, initializing new memory")
        bot_memory = _initialize_bot_memory()
    
    if not isinstance(preferences, dict):
        logger.warning(f"Preferences is not a dict: {type(preferences)}, skipping update")
        return bot_memory
    
    # Ensure user_preferences exists
    if "user_preferences" not in bot_memory:
        bot_memory["user_preferences"] = {}
    
    # Update preferences
    bot_memory["user_preferences"].update(preferences)
    
    logger.debug(f"Updated user preferences: {list(preferences.keys())}")
    return bot_memory


def update_bot_memory_inferred(
    bot_memory: Dict[str, Any],
    inferred_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge inferred information into bot_memory.
    
    Updates the inferred_information section of bot_memory with new inferred
    data. Performs a shallow merge, updating only the specified fields while
    preserving others.
    
    Args:
        bot_memory: Current bot memory dictionary
        inferred_info: Dictionary of inferred information updates
                      (booking_frequency, interests, context_notes)
        
    Returns:
        Dict[str, Any]: Updated bot_memory
        
    Example:
        updated = update_bot_memory_inferred(
            bot_memory=current_memory,
            inferred_info={"booking_frequency": "regular", "interests": ["tennis"]}
        )
        
    Requirements: 4.1, 4.2
    """
    if not isinstance(bot_memory, dict):
        logger.warning("Bot memory is not a dict, initializing new memory")
        bot_memory = _initialize_bot_memory()
    
    if not isinstance(inferred_info, dict):
        logger.warning(f"Inferred info is not a dict: {type(inferred_info)}, skipping update")
        return bot_memory
    
    # Ensure inferred_information exists
    if "inferred_information" not in bot_memory:
        bot_memory["inferred_information"] = {}
    
    # Update inferred information
    bot_memory["inferred_information"].update(inferred_info)
    
    logger.debug(f"Updated inferred information: {list(inferred_info.keys())}")
    return bot_memory


def _initialize_bot_memory() -> Dict[str, Any]:
    """
    Create an empty bot_memory with default structure.
    
    Returns:
        Dict[str, Any]: Empty bot_memory with proper structure
    """
    return {
        "conversation_history": [],
        "user_preferences": {},
        "inferred_information": {},
        "context": {}
    }


def _ensure_bot_memory_structure(bot_memory: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure bot_memory has all required fields.
    
    Adds missing fields to bot_memory if they don't exist.
    This handles backward compatibility with older bot_memory structures.
    
    Args:
        bot_memory: Bot memory dictionary to validate
        
    Returns:
        Dict[str, Any]: Bot memory with all required fields
    """
    if "conversation_history" not in bot_memory:
        bot_memory["conversation_history"] = []
    
    if "user_preferences" not in bot_memory:
        bot_memory["user_preferences"] = {}
    
    if "inferred_information" not in bot_memory:
        bot_memory["inferred_information"] = {}
    
    if "context" not in bot_memory:
        bot_memory["context"] = {}
    
    return bot_memory

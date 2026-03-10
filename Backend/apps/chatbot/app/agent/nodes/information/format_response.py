"""
Format response node - prepares the final user-facing message.

This node formats the final response based on:
- Execution results
- Validation errors
- Property/court lists when asking selection
"""

import logging
from typing import Dict, Any

from app.agent.state.conversation_state import ConversationState
from app.agent.utils.llm_logger import get_llm_logger

logger = logging.getLogger(__name__)


async def format_response(
    state: ConversationState,
    tools: Dict[str, Any] = None
) -> ConversationState:
    """
    Format the final response for the user.
    
    This node:
    1. Reads execution_results from flow_state
    2. Reads validation_error if any
    3. Formats a clean, user-friendly response
    4. Sets response_content and response_type
    
    Args:
        state: Current conversation state
        tools: Tool registry (not used)
        
    Returns:
        Updated state with formatted response
    """
    chat_id = state.get("chat_id")
    flow_state = state.get("flow_state", {})
    
    logger.info(f"Formatting response for chat {chat_id}")
    
    # Check for validation errors first
    validation_error = flow_state.get("validation_error")
    if validation_error:
        if validation_error == "invalid_property":
            response = "I couldn't find that property. Please choose one of the available properties."
        elif validation_error == "invalid_court":
            response = "I couldn't find that court. Please choose one of the available courts."
        elif validation_error == "unclear_message":
            response = "I couldn't understand that. Please try again."
        else:
            response = "Something went wrong. Please try again."
        
        state["response_content"] = response
        state["response_type"] = "text"
        flow_state["last_node"] = "information-format_response"
        state["flow_state"] = flow_state
        return state
    
    # Check for bot_response (legacy - for backward compatibility)
    bot_response = flow_state.get("bot_response")
    if bot_response:
        state["response_content"] = bot_response
        state["response_type"] = "text"
        flow_state["last_node"] = "information-format_response"
        state["flow_state"] = flow_state
        return state
    
    # Build response from execution results and question
    response_parts = []
    
    # Format execution results
    execution_results = flow_state.get("execution_results", {})
    
    if execution_results:
        for action, result in execution_results.items():
            if result.get("status") == "success":
                data = result.get("data")
                
                if action == "property_details" and data:
                    # Format property details
                    response_parts.append(f"📍 **{data.get('name', 'Property')}**")
                    if data.get('description'):
                        response_parts.append(data['description'])
                    if data.get('address'):
                        response_parts.append(f"Location: {data['address']}, {data.get('city', '')}")
                    
                elif action == "court_details" and data:
                    # Format court details
                    response_parts.append(f"🏟️ **{data.get('name', 'Court')}** ({data.get('sport_type', '')})")
                    if data.get('description'):
                        response_parts.append(data['description'])
                    
                elif action == "pricing" and data:
                    # Format pricing
                    if isinstance(data, list) and data:
                        response_parts.append("💰 **Pricing:**")
                        for rule in data:
                            response_parts.append(
                                f"  {rule.get('day_type', 'Day')}: PKR {rule.get('price_per_hour', 0)}/hour"
                            )
                    else:
                        response_parts.append("Pricing information not available.")
                    
                elif action == "media" and data:
                    # Format media
                    if isinstance(data, list) and data:
                        response_parts.append(f"📸 **Media:** {len(data)} items available")
                        for idx, media in enumerate(data[:3], 1):
                            response_parts.append(f"  {idx}. {media.get('media_type', 'image')}: {media.get('url', '')}")
                    else:
                        response_parts.append("No media available.")
                
                elif action == "list_courts" and data:
                    # Format list of courts
                    if isinstance(data, list) and data:
                        response_parts.append(f"🏟️ Available Courts ({len(data)}):")
                        for idx, court in enumerate(data, 1):
                            sport_types = ", ".join(court.get('sport_types', []))
                            court_name = court.get('name', 'Court')
                            
                            # Build court line
                            if sport_types:
                                court_line = f"{idx}. {court_name} ({sport_types})"
                            else:
                                court_line = f"{idx}. {court_name}"
                            
                            # Add description if available (keep it short)
                            if court.get('description'):
                                desc = court['description']
                                # Truncate to first sentence or 100 chars
                                if '.' in desc:
                                    desc = desc.split('.')[0] + '.'
                                if len(desc) > 100:
                                    desc = desc[:100] + "..."
                                court_line += f" - {desc}"
                            
                            response_parts.append(court_line)
                    else:
                        response_parts.append("No courts available for this property.")
                
                else:
                    # Fallback for unknown action
                    response_parts.append(str(data))
            else:
                response_parts.append(f"Error getting {action}: {result.get('error', 'Unknown error')}")
    
    # Add question if exists (from ask_property or ask_court)
    question = flow_state.get("question")
    if question:
        response_parts.append(question)
    
    # Combine all parts
    if response_parts:
        response = "\n\n".join(response_parts)
    else:
        response = "No results to display."
    
    # Set response
    state["response_content"] = response
    state["response_type"] = "text"
    
    # Track last node
    flow_state["last_node"] = "information-format_response"
    state["flow_state"] = flow_state
    
    # Log the formatted response
    llm_logger = get_llm_logger()
    llm_logger.log_llm_call(
        node_name="information_format_response",
        prompt="[No LLM call - response formatted from execution results]",
        response=response,
        parameters=None
    )
    
    logger.info(f"[FORMAT RESPONSE] Chat {chat_id}: Response formatted ({len(response)} chars)")
    
    return state

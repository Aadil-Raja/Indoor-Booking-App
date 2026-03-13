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
from app.agent.utils.media_downloader import download_media_batch

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
                    # Format property details based on included fields
                    fields = result.get("fields", ["all"])
                    
                    # Always show name
                    if data.get('name'):
                        response_parts.append(f"📍 **{data.get('name')}**")
                    
                    # Show description if included
                    if 'description' in data and data.get('description'):
                        response_parts.append(data['description'])
                    
                    # Show location if included
                    if 'address' in data:
                        location_parts = []
                        if data.get('address'):
                            location_parts.append(data['address'])
                        if data.get('city'):
                            location_parts.append(data['city'])
                        if data.get('state'):
                            location_parts.append(data['state'])
                        if location_parts:
                            response_parts.append(f"📍 Location: {', '.join(location_parts)}")
                        if data.get('maps_link'):
                            response_parts.append(f"🗺️ {data['maps_link']}")
                    
                    # Show contact if included
                    if 'phone' in data or 'email' in data:
                        contact_parts = []
                        if data.get('phone'):
                            contact_parts.append(f"📞 Phone: {data['phone']}")
                        if data.get('email'):
                            contact_parts.append(f"📧 Email: {data['email']}")
                        if contact_parts:
                            response_parts.extend(contact_parts)
                    
                    # Show amenities if included
                    if 'amenities' in data and data.get('amenities'):
                        amenities = data['amenities']
                        if isinstance(amenities, list) and amenities:
                            response_parts.append(f"✨ Amenities: {', '.join(amenities)}")
                    
                    # Show courts if included
                    if 'courts' in data and data.get('courts'):
                        courts = data['courts']
                        if isinstance(courts, list) and courts:
                            # Get unique sport types
                            unique_sports = set()
                            for court in courts:
                                sport_types = court.get('sport_types', [])
                                for st in sport_types:
                                    unique_sports.add(st)
                            
                            if unique_sports:
                                response_parts.append(f"🏟️ Available Sports: {', '.join(sorted(unique_sports))}")
                    
                elif action == "court_details" and data:
                    # Format court details based on included fields
                    fields = result.get("fields", ["all"])
                    
                    # Always show name
                    if data.get('name'):
                        response_parts.append(f"🏟️ **{data.get('name')}**")
                    
                    # Show sport types if included
                    if 'sport_types' in data and data.get('sport_types'):
                        sport_types = data['sport_types']
                        if isinstance(sport_types, list):
                            response_parts.append(f"Sports: {', '.join(sport_types)}")
                    
                    # Show description if included
                    if 'description' in data and data.get('description'):
                        response_parts.append(f"\n{data['description']}")
                    
                    # Show specifications if included
                    if 'specifications' in data and data.get('specifications'):
                        specs = data['specifications']
                        # Handle both dict and string formats
                        if isinstance(specs, dict):
                            response_parts.append("\n📐 Specifications:")
                            for key, value in specs.items():
                                response_parts.append(f"  • {key}: {value}")
                        elif isinstance(specs, str):
                            response_parts.append(f"\n📐 Specifications: {specs}")
                    
                    # Show amenities if included
                    if 'amenities' in data and data.get('amenities'):
                        amenities = data['amenities']
                        if isinstance(amenities, list) and amenities:
                            response_parts.append(f"✨ Amenities: {', '.join(str(a) for a in amenities)}")
                        elif isinstance(amenities, str):
                            response_parts.append(f"✨ Amenities: {amenities}")
                    
                    # Show pricing if included
                    if 'pricing' in data and data.get('pricing'):
                        pricing_rules = data['pricing']
                        if isinstance(pricing_rules, list) and pricing_rules:
                            response_parts.append("\n💰 Pricing:")
                            for rule in pricing_rules:
                                # Use the pre-formatted string
                                formatted = rule.get('formatted', '')
                                if formatted:
                                    response_parts.append(f"  • {formatted}")
                    
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
                    # Download and encode media as base64
                    source = result.get("source", "court")
                    
                    if isinstance(data, list) and data:
                        # Prepare media items for download with enhanced captions
                        media_items = []
                        for media in data:
                            url = media.get('url')
                            if url:
                                # Build meaningful caption
                                caption_parts = []
                                
                                # Add court name if available
                                court_name = media.get('court_name')
                                if court_name:
                                    caption_parts.append(court_name)
                                
                                # Add sport types if available (from court data)
                                sport_types = media.get('sport_types')
                                if sport_types and isinstance(sport_types, list):
                                    caption_parts.append(f"({', '.join(sport_types)})")
                                
                                # Use original caption if no court info
                                if not caption_parts and media.get('caption'):
                                    caption_parts.append(media.get('caption'))
                                
                                final_caption = ' '.join(caption_parts) if caption_parts else ''
                                
                                media_items.append({
                                    "url": url,
                                    "type": media.get('media_type', 'image'),
                                    "caption": final_caption
                                })
                        
                        # Download media asynchronously
                        logger.info(f"Downloading {len(media_items)} media items for chat {chat_id}")
                        downloaded_media = await download_media_batch(media_items)
                        
                        if downloaded_media:
                            # Set response type to media
                            state["response_type"] = "media"
                            
                            # Store in response_metadata for frontend
                            state["response_metadata"] = {
                                "media": downloaded_media
                            }
                            
                            # Don't add text response - just show images
                            logger.info(f"Successfully prepared {len(downloaded_media)} media items for chat {chat_id}")
                        else:
                            response_parts.append("Media download failed. Please try again.")
                    else:
                        response_parts.append("No media available.")
                
                elif action == "availability" and data:
                    # New simplified availability response
                    available_slots = data.get("available_slots", [])
                    match_type = data.get("match_type", "")
                    user_guidance = data.get("user_guidance", "")
                    filter_info = data.get("filter_info", {})
                    slots_by_period = data.get("slots_by_period", {})
                    court_name = data.get("court_name", "Court")
                    date_str = result.get("date", "")
                    
                    # Format date for display
                    try:
                        from datetime import datetime
                        date_obj = datetime.fromisoformat(date_str)
                        formatted_date = date_obj.strftime("%A, %B %d, %Y")
                    except:
                        formatted_date = date_str
                    
                    response_parts.append(f"📅 Availability for {court_name} on {formatted_date}:")
                    response_parts.append("")
                    
                    # Show filter info if applicable
                    if filter_info.get("type") == "time_range":
                        start = filter_info.get("start_time")
                        end = filter_info.get("end_time")
                        period = filter_info.get("time_period")
                        filter_desc = f"Searching: {start} to {end}"
                        if period:
                            filter_desc += f" ({period})"
                        response_parts.append(filter_desc)
                        response_parts.append("")
                    
                    # Display results based on match type
                    if match_type == "exact":
                        response_parts.append("✅ Your requested time is available!")
                        response_parts.append("")
                        for slot in available_slots[:10]:
                            formatted_slot = _format_slot(slot)
                            response_parts.append(f"  • {formatted_slot}")
                    
                    elif match_type == "partial":
                        response_parts.append("⚠️ Exact time not available. Here are slots that partially overlap:")
                        response_parts.append("")
                        for slot in available_slots[:10]:
                            formatted_slot = _format_slot(slot)
                            response_parts.append(f"  • {formatted_slot}")
                        
                        if len(available_slots) > 10:
                            response_parts.append(f"  ... and {len(available_slots) - 10} more slots")
                    
                    elif match_type == "nearby":
                        response_parts.append("❌ Requested time not available. Here are nearby alternatives:")
                        response_parts.append("")
                        for slot in available_slots[:5]:
                            formatted_slot = _format_slot(slot)
                            response_parts.append(f"  • {formatted_slot}")
                    
                    elif match_type == "period":
                        response_parts.append("Here are available options:")
                        response_parts.append("")
                        for slot in available_slots[:10]:
                            formatted_slot = _format_slot(slot)
                            response_parts.append(f"  • {formatted_slot}")
                        
                        if len(available_slots) > 10:
                            response_parts.append(f"  ... and {len(available_slots) - 10} more slots")
                    
                    elif match_type == "all":
                        if slots_by_period:
                            # Show grouped by period
                            period_emojis = {
                                "morning": "🌅",
                                "afternoon": "☀️",
                                "evening": "🌆",
                                "night": "🌙"
                            }
                            
                            for period in ["morning", "afternoon", "evening", "night"]:
                                period_slots = slots_by_period.get(period, [])
                                if period_slots:
                                    emoji = period_emojis.get(period, "")
                                    response_parts.append(f"{emoji} {period.capitalize()} slots:")
                                    for slot in period_slots[:5]:
                                        formatted_slot = _format_slot(slot)
                                        response_parts.append(f"  • {formatted_slot}")
                                    if len(period_slots) > 5:
                                        response_parts.append(f"  ... and {len(period_slots) - 5} more")
                                    response_parts.append("")
                        else:
                            # Show all slots without grouping
                            response_parts.append("All available slots:")
                            response_parts.append("")
                            for slot in available_slots[:10]:
                                formatted_slot = _format_slot(slot)
                                response_parts.append(f"  • {formatted_slot}")
                            
                            if len(available_slots) > 10:
                                response_parts.append(f"  ... and {len(available_slots) - 10} more slots")
                    
                    elif match_type == "none":
                        response_parts.append("❌ No available slots for this date and time.")
                    
                    else:
                        # Fallback for any other match type
                        if available_slots:
                            response_parts.append("Available slots:")
                            response_parts.append("")
                            for slot in available_slots[:10]:
                                formatted_slot = _format_slot(slot)
                                response_parts.append(f"  • {formatted_slot}")
                        else:
                            response_parts.append("❌ No available slots for this date.")
                    
                    # Add message if provided by tool
                    message = data.get("message")
                    if message:
                        response_parts.append("")
                        response_parts.append(f"💡 {message}")
                
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
        # If no text parts but media exists, use empty string (media will be in metadata)
        if state.get("response_type") == "media":
            response = ""
        else:
            response = "No results to display."
    
    # Set response (don't override response_type if already set to media)
    state["response_content"] = response
    if "response_type" not in state or state["response_type"] != "media":
        state["response_type"] = "text"
    
    # Ensure response_metadata exists
    if "response_metadata" not in state:
        state["response_metadata"] = {}
    
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



def _format_slot(slot: Dict[str, Any]) -> str:
    """
    Format a single availability slot for display.
    
    Slots are already normalized by the availability tool (XX:59 → XX+1:00).
    
    Args:
        slot: Slot dictionary with start_time, end_time, price_per_hour, label
        
    Returns:
        Formatted string like "6:00 PM - 7:00 PM (PKR 500/hour - Evening Rate)"
    """
    start_time = slot.get("start_time", "")
    end_time = slot.get("end_time", "")
    price = slot.get("price_per_hour", 0)
    label = slot.get("label", "")
    
    # Convert 24-hour to 12-hour format
    try:
        from datetime import datetime
        
        # Parse times (handle both HH:MM and HH:MM:SS formats)
        if len(start_time) == 8:  # HH:MM:SS
            start_obj = datetime.strptime(start_time, "%H:%M:%S")
            end_obj = datetime.strptime(end_time, "%H:%M:%S")
        else:  # HH:MM
            start_obj = datetime.strptime(start_time, "%H:%M")
            end_obj = datetime.strptime(end_time, "%H:%M")
        
        # Format to 12-hour with AM/PM
        start_12h = start_obj.strftime("%I:%M %p").lstrip("0")
        end_12h = end_obj.strftime("%I:%M %p").lstrip("0")
        
        time_str = f"{start_12h} - {end_12h}"
    except:
        # Fallback to original format if parsing fails
        time_str = f"{start_time} - {end_time}"
    
    # Build price string
    price_str = f"PKR {price:.0f}/hour"
    
    # Add label if available
    if label:
        return f"{time_str} ({price_str} - {label})"
    else:
        return f"{time_str} ({price_str})"

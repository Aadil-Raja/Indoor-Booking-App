"""
Validate and update state node - backend validation only.

This node:
1. Reads router_result
2. Validates extracted property/court against available options
3. Updates state only if valid
4. Handles reply resolution
5. Applies context reset rules (if property changes, reset court/date/slot)
6. Prepares requested_actions
7. Handles invalid replies safely

No LLM calls - pure backend logic.
"""

import logging
from typing import Dict, Any, Optional, List

from app.agent.state.conversation_state import ConversationState
from app.agent.utils.llm_logger import get_llm_logger

logger = logging.getLogger(__name__)


# Action requirements map (imported from check_requirements logic)
ACTION_REQUIREMENTS = {
    "property_details": {"property": True, "court": False, "date": False},
    "court_details": {"property": True, "court": True, "date": False},
    "pricing": {"property": True, "court": True, "date": False},
    "media": {"property": True, "court": False, "date": False},
    "availability": {"property": True, "court": True, "date": True},  # NEW: Availability requires all three
}


async def validate_and_update_state(
    state: ConversationState,
    tools: Dict[str, Any] = None
) -> ConversationState:

    chat_id = state.get("chat_id")
    flow_state = state.get("flow_state", {})

    logger.info(f"Validating and updating state for chat {chat_id}")

    router_result = flow_state.get("router_result", {})

    message_type = router_result.get("message_type")
    reply_target = router_result.get("reply_target")
    requested_actions = router_result.get("requested_actions", [])
    property_detail_fields = router_result.get("property_detail_fields", [])
    court_detail_fields = router_result.get("court_detail_fields", [])
    mentioned_property_name = router_result.get("mentioned_property_name")
    mentioned_court_name = router_result.get("mentioned_court_name")
    unclear = router_result.get("unclear")

    available_properties = flow_state.get("available_properties", [])
    available_courts = flow_state.get("available_courts", [])

    current_property_id = flow_state.get("property_id")
    current_court_ids = flow_state.get("court_ids", [])

    flow_state["validation_error"] = None

    # PRIORITY: Check if unclear_reason is set (even if unclear=false)
    # If unclear_reason exists, treat as unclear and show available options
    unclear_reason = router_result.get("unclear_reason")
    if unclear_reason:
        logger.warning(
            f"[UNCLEAR REASON DETECTED] Chat {chat_id}: "
            f"unclear_reason='{unclear_reason}' - treating as unclear"
        )
        unclear = True
        message_type = "unclear"
        router_result["unclear"] = True
        router_result["message_type"] = "unclear"
        flow_state["router_result"] = router_result

    # Handle unclear message early
    if unclear or message_type == "unclear":
        # Use unclear_reason if provided, otherwise use default message
        if unclear_reason:
            flow_state["bot_response"] = unclear_reason
        else:
            flow_state["bot_response"] = "I couldn't understand that. Please try again."
        
        flow_state["validation_error"] = "unclear_message"
        flow_state["last_node"] = "information-validate"
        state["flow_state"] = flow_state
        return state

    property_changed = False
    
    # Track if property/court/date was set in THIS turn (for pending action resume logic)
    property_set_this_turn = False
    court_set_this_turn = False
    date_set_this_turn = False

    # ---------------------------------
    # REPLY TARGET VALIDATION (Hybrid Safety Check)
    # ---------------------------------
    awaiting_input = flow_state.get("awaiting_input")
    
    # Validate reply_target matches awaiting_input
    if reply_target and reply_target != awaiting_input:
        logger.warning(
            f"[VALIDATION MISMATCH] Chat {chat_id}: "
            f"LLM set reply_target='{reply_target}' but awaiting_input='{awaiting_input}'. "
            f"Treating as mention instead of reply."
        )
        # Nullify reply_target - will be handled by mention validation sections
        reply_target = None
    
    # ---------------------------------
    # PENDING_REPLY VALIDATION (Fallback for LLM errors)
    # ---------------------------------
    # If LLM says "pending_reply" but user has requested actions, it's likely a new request
    if message_type == "pending_reply" and requested_actions:
        logger.warning(
            f"[PENDING_REPLY CORRECTION] Chat {chat_id}: "
            f"LLM set message_type='pending_reply' but user requested actions: {requested_actions}. "
            f"Correcting to 'mixed' or 'new_request'."
        )
        # If there's a valid reply_target AND actions, it's mixed
        if reply_target and reply_target == awaiting_input:
            message_type = "mixed"
            logger.info(f"Corrected to 'mixed' for chat {chat_id}")
        else:
            # No valid reply, just new actions
            message_type = "new_request"
            reply_target = None
            logger.info(f"Corrected to 'new_request' for chat {chat_id}")
        
        # Update router_result with corrected message_type
        router_result["message_type"] = message_type
        router_result["reply_target"] = reply_target
        flow_state["router_result"] = router_result
    
    # Additional check: If "mixed" but no mentioned property/court, it's just new_request
    if message_type == "mixed" and not mentioned_property_name and not mentioned_court_name:
        logger.warning(
            f"[MIXED CORRECTION] Chat {chat_id}: "
            f"LLM set message_type='mixed' but no property/court mentioned. "
            f"Correcting to 'new_request'."
        )
        message_type = "new_request"
        reply_target = None
        router_result["message_type"] = message_type
        router_result["reply_target"] = reply_target
        flow_state["router_result"] = router_result
    
    # Additional check: If "new_request" but reply_target is set, clear it
    if message_type == "new_request" and reply_target:
        logger.warning(
            f"[NEW_REQUEST CORRECTION] Chat {chat_id}: "
            f"LLM set message_type='new_request' but reply_target='{reply_target}'. "
            f"Clearing reply_target."
        )
        reply_target = None
        router_result["reply_target"] = reply_target
        flow_state["router_result"] = router_result

    # ---------------------------------
    # PROPERTY REPLY RESOLUTION
    # ---------------------------------
    if reply_target == "property_selection":
        
        # Additional validation: If no property mentioned, it's not really a reply
        if not mentioned_property_name:
            logger.warning(
                f"[PROPERTY REPLY VALIDATION] Chat {chat_id}: "
                f"reply_target='property_selection' but no property mentioned. "
                f"Treating as new_request instead."
            )
            reply_target = None
            message_type = "new_request"
            router_result["message_type"] = message_type
            router_result["reply_target"] = reply_target
            flow_state["router_result"] = router_result
        else:
            # User mentioned a property, validate it
            matched_property = _resolve_property_selection(
                mentioned_property_name,
                available_properties,
                chat_id
            )

            if matched_property:
                if matched_property["id"] != current_property_id:
                    property_changed = True

                flow_state["property_id"] = matched_property["id"]
                flow_state["property_name"] = matched_property.get("name")
                property_set_this_turn = True  # Mark that property was set THIS turn

                flow_state["awaiting_input"] = None

            else:
                flow_state["validation_error"] = "invalid_property"
                flow_state["awaiting_input"] = "property_selection"
                state["flow_state"] = flow_state
                return state

    # ---------------------------------
    # PROPERTY MENTION VALIDATION
    # ---------------------------------
    if mentioned_property_name and not reply_target:

        matched_property = _match_property(
            mentioned_property_name,
            available_properties,
            chat_id
        )

        if matched_property:
            if matched_property["id"] != current_property_id:
                property_changed = True

            flow_state["property_id"] = matched_property["id"]
            flow_state["property_name"] = matched_property.get("name")
            property_set_this_turn = True  # Mark that property was set THIS turn
            
            # Clear awaiting_input if we were waiting for property
            if flow_state.get("awaiting_input") == "property_selection":
                flow_state["awaiting_input"] = None
                logger.info(f"Cleared awaiting_input (property_selection) for chat {chat_id} - user mentioned valid property")

        else:
            flow_state["validation_error"] = "invalid_property"
            flow_state["awaiting_input"] = "property_selection"
            state["flow_state"] = flow_state
            return state

    # ---------------------------------
    # CONTEXT RESET AFTER PROPERTY CHANGE
    # ---------------------------------
    if property_changed:
        logger.info(f"Property changed for chat {chat_id}, checking if court type exists at new property")

        old_court_type = flow_state.get("court_type")
        new_property_id = flow_state.get("property_id")
        
        # Try to find courts with the same sport_type at the new property
        if old_court_type and available_courts:
            matching_court_ids = []
            for court in available_courts:
                # Check if court belongs to new property and has the preferred sport type
                if court.get("property_id") == new_property_id:
                    sport_types = court.get("sport_types", [])
                    if old_court_type in sport_types:
                        matching_court_ids.append(court["id"])
            
            if matching_court_ids:
                # Same court type exists at new property - preserve context
                logger.info(
                    f"Court type '{old_court_type}' exists at new property, "
                    f"updating court_ids to {matching_court_ids}"
                )
                flow_state["court_ids"] = matching_court_ids
                flow_state["court_type"] = old_court_type
                # date and slot remain unchanged
            else:
                # Court type doesn't exist at new property - reset court only
                logger.info(
                    f"Court type '{old_court_type}' not found at new property, "
                    f"resetting court_ids and court_type"
                )
                flow_state["court_ids"] = []
                flow_state["court_type"] = None
                # date and slot remain unchanged
        else:
            # No previous court type - just reset court fields
            flow_state["court_ids"] = []
            flow_state["court_type"] = None
            # date and slot remain unchanged

    active_property_id = flow_state.get("property_id")

    # ---------------------------------
    # COURT REPLY RESOLUTION
    # ---------------------------------
    if reply_target == "court_selection":
        
        # Additional validation: If no court mentioned, it's not really a reply
        if not mentioned_court_name:
            logger.warning(
                f"[COURT REPLY VALIDATION] Chat {chat_id}: "
                f"reply_target='court_selection' but no court mentioned. "
                f"Treating as new_request instead."
            )
            reply_target = None
            message_type = "new_request"
            router_result["message_type"] = message_type
            router_result["reply_target"] = reply_target
            flow_state["router_result"] = router_result
        else:
            # User mentioned a court, validate it
            matched_sport_type, matched_court_ids = _resolve_court_selection(
                mentioned_court_name,
                available_courts,
                active_property_id,
                chat_id
            )

            if matched_court_ids:

                flow_state["court_ids"] = matched_court_ids
                flow_state["court_type"] = matched_sport_type
                court_set_this_turn = True  # Mark that court was set THIS turn

                flow_state["awaiting_input"] = None

            else:
                flow_state["validation_error"] = "invalid_court"
                flow_state["awaiting_input"] = "court_selection"
                state["flow_state"] = flow_state
                return state

    # ---------------------------------
    # COURT MENTION VALIDATION
    # ---------------------------------
    if mentioned_court_name and not reply_target:

        matched_sport_type, matched_court_ids = _match_court(
            mentioned_court_name,
            available_courts,
            active_property_id,
            chat_id
        )

        if matched_court_ids:

            flow_state["court_ids"] = matched_court_ids
            flow_state["court_type"] = matched_sport_type
            court_set_this_turn = True  # Mark that court was set THIS turn
            
            # Clear awaiting_input if we were waiting for court
            if flow_state.get("awaiting_input") == "court_selection":
                flow_state["awaiting_input"] = None
                logger.info(f"Cleared awaiting_input (court_selection) for chat {chat_id} - user mentioned valid court")

        else:
            flow_state["validation_error"] = "invalid_court"
            flow_state["awaiting_input"] = "court_selection"
            state["flow_state"] = flow_state
            return state

    # ---------------------------------
    # DATE REPLY RESOLUTION
    # ---------------------------------
    if reply_target == "date_selection":
        
        # Additional validation: If no date mentioned, it's not really a reply
        if not router_result.get("mentioned_date_text"):
            logger.warning(
                f"[DATE REPLY VALIDATION] Chat {chat_id}: "
                f"reply_target='date_selection' but no date mentioned. "
                f"Treating as new_request instead."
            )
            reply_target = None
            message_type = "new_request"
            router_result["message_type"] = message_type
            router_result["reply_target"] = reply_target
            flow_state["router_result"] = router_result
        else:
            # User mentioned a date, validate and normalize it
            date_interpretation = router_result.get("date_interpretation")
            mentioned_date_text = router_result.get("mentioned_date_text")
            date_status = router_result.get("date_status", "not_provided")
            
            if date_status == "interpretable" and date_interpretation:
                # Validate that date_interpretation is something we can normalize
                valid_interpretations = [
                    "today", "tonight", "tomorrow", "parso", "day_after_tomorrow",
                    "next_monday", "next_tuesday", "next_wednesday", "next_thursday",
                    "next_friday", "next_saturday", "next_sunday",
                    "this_monday", "this_tuesday", "this_wednesday", "this_thursday",
                    "this_friday", "this_saturday", "this_sunday"
                ]
                
                # Check if it's a valid interpretation or ISO date format
                is_valid = (
                    date_interpretation in valid_interpretations or
                    date_interpretation.startswith("next_") or
                    date_interpretation.startswith("this_") or
                    _is_iso_date(date_interpretation)
                )
                
                if not is_valid:
                    # Invalid interpretation like "next_week" - ask for specific date
                    logger.warning(
                        f"Invalid date_interpretation '{date_interpretation}' for chat {chat_id} - "
                        f"asking for specific date"
                    )
                    flow_state["validation_error"] = "invalid_date"
                    flow_state["bot_response"] = (
                        "Please specify a specific date:\n\n"
                        "📅 Relative dates: today, tomorrow, parso, next Monday\n"
                        "📅 Exact date: 2026-03-15 or March 15\n\n"
                        "You can also specify time:\n"
                        "🕐 Time period: morning, afternoon, evening, night\n"
                        "🕐 Exact slot: 6 to 7 PM, 18:00 to 19:00"
                    )
                    flow_state["awaiting_input"] = "date_selection"
                    state["flow_state"] = flow_state
                    return state
                
                # Normalize date to YYYY-MM-DD format
                normalized_date = _normalize_date(
                    date_interpretation,
                    mentioned_date_text,
                    chat_id
                )
                
                if normalized_date:
                    flow_state["selected_date"] = normalized_date
                    date_set_this_turn = True  # Mark that date was set THIS turn
                    flow_state["awaiting_input"] = None
                    
                    logger.info(
                        f"Date reply resolved for chat {chat_id}: "
                        f"'{mentioned_date_text}' → {normalized_date}"
                    )
                else:
                    # Failed to normalize - invalid date
                    flow_state["validation_error"] = "invalid_date"
                    flow_state["awaiting_input"] = "date_selection"
                    state["flow_state"] = flow_state
                    return state
            else:
                # Date status is unclear or not interpretable
                flow_state["validation_error"] = "invalid_date"
                flow_state["awaiting_input"] = "date_selection"
                state["flow_state"] = flow_state
                return state

    # ---------------------------------
    # DATE MENTION VALIDATION
    # ---------------------------------
    mentioned_date_text = router_result.get("mentioned_date_text")
    date_interpretation = router_result.get("date_interpretation")
    date_status = router_result.get("date_status", "not_provided")
    
    if mentioned_date_text and not reply_target:
        # User mentioned a date in their message (not replying to date question)
        
        if date_status == "interpretable" and date_interpretation:
            # Validate that date_interpretation is something we can normalize
            valid_interpretations = [
                "today", "tonight", "tomorrow", "parso", "day_after_tomorrow",
                "next_monday", "next_tuesday", "next_wednesday", "next_thursday",
                "next_friday", "next_saturday", "next_sunday",
                "this_monday", "this_tuesday", "this_wednesday", "this_thursday",
                "this_friday", "this_saturday", "this_sunday"
            ]
            
            # Check if it's a valid interpretation or ISO date format
            is_valid = (
                date_interpretation in valid_interpretations or
                date_interpretation.startswith("next_") or
                date_interpretation.startswith("this_") or
                _is_iso_date(date_interpretation)
            )
            
            if not is_valid:
                # Invalid interpretation like "next_week" - ask for specific date
                logger.warning(
                    f"Invalid date_interpretation '{date_interpretation}' for chat {chat_id} - "
                    f"asking for specific date"
                )
                flow_state["validation_error"] = "invalid_date"
                flow_state["bot_response"] = (
                    "Please specify a specific date like today, tomorrow, "
                    "next Monday, or a date like March 15."
                )
                flow_state["awaiting_input"] = "date_selection"
                state["flow_state"] = flow_state
                return state
            
            # Normalize date to YYYY-MM-DD format
            normalized_date = _normalize_date(
                date_interpretation,
                mentioned_date_text,
                chat_id
            )
            
            if normalized_date:
                flow_state["selected_date"] = normalized_date
                date_set_this_turn = True  # Mark that date was set THIS turn
                
                # Clear awaiting_input if we were waiting for date
                if flow_state.get("awaiting_input") == "date_selection":
                    flow_state["awaiting_input"] = None
                    logger.info(
                        f"Cleared awaiting_input (date_selection) for chat {chat_id} - "
                        f"user mentioned valid date"
                    )
                
                logger.info(
                    f"Date mention validated for chat {chat_id}: "
                    f"'{mentioned_date_text}' → {normalized_date}"
                )
            else:
                # Failed to normalize - invalid date
                flow_state["validation_error"] = "invalid_date"
                flow_state["awaiting_input"] = "date_selection"
                state["flow_state"] = flow_state
                return state
        else:
            # Date status is unclear
            flow_state["validation_error"] = "invalid_date"
            flow_state["awaiting_input"] = "date_selection"
            state["flow_state"] = flow_state
            return state
    
    # ---------------------------------
    # EXTRACT AND STORE TIME INFORMATION
    # ---------------------------------
    # Extract start_time, end_time, and time_period from router result
    start_time = router_result.get("start_time")
    end_time = router_result.get("end_time")
    time_period = router_result.get("time_period")
    
    # Round times to nearest hour: floor start_time, ceil end_time
    # Examples: "1:45" → "01:00", "2:30" → "02:00" for start_time
    #           "1:45" → "02:00", "2:30" → "03:00" for end_time
    if start_time:
        start_time = _floor_time_to_hour(start_time, chat_id)
        flow_state["selected_start_time"] = start_time
        logger.debug(f"Stored and floored start_time: {start_time} for chat {chat_id}")
    
    if end_time:
        end_time = _ceil_time_to_hour(end_time, chat_id)
        flow_state["selected_end_time"] = end_time
        logger.debug(f"Stored and ceiled end_time: {end_time} for chat {chat_id}")
    
    if time_period:
        flow_state["time_period"] = time_period
        logger.debug(f"Stored time_period: {time_period} for chat {chat_id}")

    # ---------------------------------
    # AUTO-ADD AVAILABILITY ACTION
    # ---------------------------------
    # If user provided NEW date/time info IN THIS TURN (validated and saved),
    # AND we have property_id and court_ids,
    # THEN auto-add availability action (even if LLM didn't request it)
    
    # Get pending_actions early (needed for availability check)
    pending_actions = flow_state.get("pending_actions", [])
    
    # Check if user provided NEW date/time info THIS TURN
    # This is detected by checking if router_result has these fields
    date_provided_this_turn = (
        router_result.get("mentioned_date_text") is not None or
        router_result.get("date_interpretation") is not None
    )
    time_provided_this_turn = (
        router_result.get("time_period") is not None or
        router_result.get("start_time") is not None or
        router_result.get("end_time") is not None
    )
    
    # Check if we have the minimum requirements (property + court)
    has_property = flow_state.get("property_id") is not None
    has_court = len(flow_state.get("court_ids", [])) > 0
    
    # Check if availability was pending
    availability_was_pending = "availability" in pending_actions
    
    # Auto-add availability if:
    # 1. User provided date OR time info THIS TURN (validated by this node)
    # 2. We have property and court
    # 3. Availability is not already in requested_actions
    should_add_availability = (
        (date_provided_this_turn or time_provided_this_turn) and
        has_property and
        has_court and
        "availability" not in requested_actions
    )
    
    if should_add_availability:
        requested_actions.append("availability")
        logger.info(
            f"[AUTO-ADD] Added 'availability' action for chat {chat_id} because user provided date/time: "
            f"date_provided={date_provided_this_turn}, time_provided={time_provided_this_turn}, "
            f"selected_date={flow_state.get('selected_date')}, "
            f"time_period={flow_state.get('time_period')}, "
            f"start_time={flow_state.get('selected_start_time')}, "
            f"end_time={flow_state.get('selected_end_time')}, "
            f"was_pending={availability_was_pending}"
        )
        
        # Update router_result
        router_result["requested_actions"] = requested_actions
        flow_state["router_result"] = router_result
    elif date_provided_this_turn or time_provided_this_turn:
        # Log why availability wasn't added (for debugging)
        missing = []
        if not has_property:
            missing.append("property")
        if not has_court:
            missing.append("court")
        if "availability" in requested_actions:
            logger.debug(f"Availability already in requested_actions for chat {chat_id}")
        elif missing:
            logger.debug(
                f"Not auto-adding availability for chat {chat_id} - user provided date/time but missing: {', '.join(missing)}"
            )

    # ---------------------------------
    # VALIDATE AND SAVE PROPERTY_DETAIL_FIELDS
    # ---------------------------------
    VALID_PROPERTY_DETAIL_FIELDS = {"location", "contact", "amenities", "available_courts", "description", "all"}
    
    if property_detail_fields:
        # Validate fields
        validated_fields = []
        for field in property_detail_fields:
            if field in VALID_PROPERTY_DETAIL_FIELDS:
                validated_fields.append(field)
            else:
                logger.warning(f"Invalid property_detail_field '{field}' ignored for chat {chat_id}")
        
        # If no valid fields, default to "all"
        if not validated_fields:
            logger.info(f"No valid property_detail_fields, defaulting to 'all' for chat {chat_id}")
            validated_fields = ["all"]
        
        flow_state["property_detail_fields"] = validated_fields
    else:
        # No fields specified, default to "all"
        flow_state["property_detail_fields"] = ["all"]
    
    logger.debug(f"Property detail fields for chat {chat_id}: {flow_state['property_detail_fields']}")

    # ---------------------------------
    # VALIDATE AND SAVE COURT_DETAIL_FIELDS
    # ---------------------------------
    VALID_COURT_DETAIL_FIELDS = {"basic", "pricing", "all"}
    
    if court_detail_fields:
        # Validate fields
        validated_fields = []
        for field in court_detail_fields:
            if field in VALID_COURT_DETAIL_FIELDS:
                validated_fields.append(field)
            else:
                logger.warning(f"Invalid court_detail_field '{field}' ignored for chat {chat_id}")
        
        # If no valid fields, default to "all"
        if not validated_fields:
            logger.info(f"No valid court_detail_fields, defaulting to 'all' for chat {chat_id}")
            validated_fields = ["all"]
        
        flow_state["court_detail_fields"] = validated_fields
    else:
        # No fields specified, default to "all"
        flow_state["court_detail_fields"] = ["all"]
    
    logger.debug(f"Court detail fields for chat {chat_id}: {flow_state['court_detail_fields']}")

    # ---------------------------------
    # AUTO-ADD MISSING ACTIONS (Backend Safety Net)
    # ---------------------------------
    # If LLM specified fields but forgot to add the corresponding action, add it automatically
    if property_detail_fields and "property_details" not in requested_actions:
        requested_actions.append("property_details")
        logger.warning(
            f"Auto-added 'property_details' action because property_detail_fields were specified "
            f"but action was missing for chat {chat_id}"
        )
    
    if court_detail_fields and "court_details" not in requested_actions:
        requested_actions.append("court_details")
        logger.warning(
            f"Auto-added 'court_details' action because court_detail_fields were specified "
            f"but action was missing for chat {chat_id}"
        )
    
    # If LLM specified action but forgot fields, default to "all"
    if "property_details" in requested_actions and not property_detail_fields:
        flow_state["property_detail_fields"] = ["all"]
        logger.warning(
            f"Defaulting property_detail_fields to ['all'] because property_details action "
            f"was specified but fields were missing for chat {chat_id}"
        )
    
    if "court_details" in requested_actions and not court_detail_fields:
        flow_state["court_detail_fields"] = ["all"]
        logger.warning(
            f"Defaulting court_detail_fields to ['all'] because court_details action "
            f"was specified but fields were missing for chat {chat_id}"
        )

    # ---------------------------------
    # KEYWORD-BASED FALLBACK (Generic Solution)
    # ---------------------------------
    # If LLM returned empty actions and user is NOT replying, try keyword matching
    # This handles cases like "tell courts", "show location", "pricing info" etc.
    if not requested_actions and not reply_target and message_type != "pending_reply":
        user_message = state.get("user_message", "").lower()
        
        # Keyword mappings for common requests
        keyword_mappings = {
            # Property-related keywords
            "location": ("property_details", ["location"]),
            "address": ("property_details", ["location"]),
            "where": ("property_details", ["location"]),
            "map": ("property_details", ["location"]),
            "contact": ("property_details", ["contact"]),
            "phone": ("property_details", ["contact"]),
            "email": ("property_details", ["contact"]),
            "amenities": ("property_details", ["amenities"]),
            "amenity": ("property_details", ["amenities"]),
            "facilities": ("property_details", ["amenities"]),
            "facility": ("property_details", ["amenities"]),
            "courts": ("property_details", ["available_courts"]),
            "court": ("property_details", ["available_courts"]),
            "available": ("property_details", ["available_courts"]),
            "description": ("property_details", ["description"]),
            "about": ("property_details", ["description"]),
            "details": ("property_details", ["all"]),
            
            # Court-related keywords
            "pricing": ("court_details", ["pricing"]),
            "price": ("court_details", ["pricing"]),
            "cost": ("court_details", ["pricing"]),
            "rate": ("court_details", ["pricing"]),
            "fee": ("court_details", ["pricing"]),
            "specification": ("court_details", ["basic"]),
            "specs": ("court_details", ["basic"]),
            "media": ("media", None),
            "image": ("media", None),
            "photo": ("media", None),
            "picture": ("media", None),
            # Availability-related keywords
            "availability": ("availability", None),
            "available": ("availability", None),
            "slot": ("availability", None),
            "slots": ("availability", None),
            "booking": ("availability", None),
            "book": ("availability", None),
            "reserve": ("availability", None),
        }
        
        # Try to match keywords
        matched_action = None
        matched_fields = None
        
        for keyword, (action, fields) in keyword_mappings.items():
            if keyword in user_message:
                matched_action = action
                matched_fields = fields
                logger.info(
                    f"[KEYWORD FALLBACK] Chat {chat_id}: Matched keyword '{keyword}' → "
                    f"action='{action}', fields={fields}"
                )
                break
        
        # Apply fallback if matched
        if matched_action:
            requested_actions = [matched_action]
            
            # Set appropriate fields
            if matched_action == "property_details" and matched_fields:
                flow_state["property_detail_fields"] = matched_fields
            elif matched_action == "court_details" and matched_fields:
                flow_state["court_detail_fields"] = matched_fields
            
            # Update router_result
            router_result["requested_actions"] = requested_actions
            if matched_action == "property_details":
                router_result["property_detail_fields"] = matched_fields
            elif matched_action == "court_details":
                router_result["court_detail_fields"] = matched_fields
            
            flow_state["router_result"] = router_result
            
            logger.info(
                f"[KEYWORD FALLBACK APPLIED] Chat {chat_id}: "
                f"Set requested_actions={requested_actions}, fields={matched_fields}"
            )
        else:
            logger.debug(
                f"[KEYWORD FALLBACK] Chat {chat_id}: No keyword match found in message: {user_message}"
            )

    # ---------------------------------
    # REQUESTED ACTIONS (Smart Pending Logic)
    # ---------------------------------
    # Note: pending_actions already retrieved earlier for availability check

    # RULE: Resume pending actions ONLY if:
    # 1. User provided property/court in THIS TURN (property_set_this_turn or court_set_this_turn)
    #    AND the provided info satisfies requirements for pending actions
    # 2. OR user explicitly asks for the EXACT SAME action that's pending (not just similar)
    # 
    # DON'T resume if:
    # - User asks something completely new (different requested_actions)
    # - User didn't provide any new property/court data this turn
    
    # Check if user is asking for EXACT same action as pending (all requested actions must be in pending)
    user_asking_same_action = False
    if requested_actions and pending_actions:
        # Only consider it "same action" if ALL requested actions are in pending
        # This prevents resuming when user asks for something different
        user_asking_same_action = all(action in pending_actions for action in requested_actions)
    
    # Check if provided info (in THIS turn) satisfies requirements for pending actions
    info_satisfies_pending = False
    if pending_actions and (property_set_this_turn or court_set_this_turn or date_set_this_turn):
        for action in pending_actions:
            action_reqs = ACTION_REQUIREMENTS.get(action, {})
            needs_property = action_reqs.get("property", False)
            needs_court = action_reqs.get("court", False)
            needs_date = action_reqs.get("date", False)
            
            # If action needs property and user just provided property THIS turn
            if needs_property and property_set_this_turn:
                info_satisfies_pending = True
                break
            
            # If action needs court and user just provided court THIS turn
            if needs_court and court_set_this_turn:
                info_satisfies_pending = True
                break
            
            # If action needs date and user just provided date THIS turn
            if needs_date and date_set_this_turn:
                info_satisfies_pending = True
                break
    
    # Decide whether to resume pending actions
    # IMPORTANT: Only resume if info was provided this turn OR asking exact same action
    should_resume_pending = (
        info_satisfies_pending or
        user_asking_same_action
    )

    if should_resume_pending and pending_actions:
        # User provided relevant info THIS turn OR asking for exact same action - restore pending actions
        if requested_actions and not user_asking_same_action:
            # User provided info (property/court) AND has new actions - merge them
            combined = list(requested_actions)
            for action in pending_actions:
                if action not in combined:
                    combined.append(action)
            flow_state["requested_actions"] = combined
            logger.info(
                f"Resuming pending actions for chat {chat_id}: "
                f"new={requested_actions}, pending={pending_actions}, combined={combined}, "
                f"reason=info_satisfies_pending, "
                f"property_set_this_turn={property_set_this_turn}, court_set_this_turn={court_set_this_turn}, "
                f"date_set_this_turn={date_set_this_turn}"
            )
        elif user_asking_same_action:
            # User asking for exact same action - just use requested actions (which are same as pending)
            flow_state["requested_actions"] = requested_actions
            logger.info(
                f"User asking for same action as pending for chat {chat_id}: "
                f"requested={requested_actions}, pending={pending_actions}"
            )
        else:
            # Only pending actions, no new ones
            flow_state["requested_actions"] = pending_actions
            logger.info(
                f"Restored pending actions for chat {chat_id}: {pending_actions}, "
                f"reason=info_satisfies_pending, "
                f"property_set_this_turn={property_set_this_turn}, court_set_this_turn={court_set_this_turn}, "
                f"date_set_this_turn={date_set_this_turn}"
            )
        
        # Restore pending action params
        pending_action_params = flow_state.get("pending_action_params", {})
        if pending_action_params:
            # Restore property_detail_fields if property_details action is resuming
            if "property_details" in flow_state["requested_actions"] and "property_details" in pending_action_params:
                property_params = pending_action_params.get("property_details", {})
                if "property_detail_fields" in property_params:
                    flow_state["property_detail_fields"] = property_params["property_detail_fields"]
                    logger.debug(f"Restored property_detail_fields from pending params: {flow_state['property_detail_fields']}")
            
            # Restore court_detail_fields if court_details action is resuming
            if "court_details" in flow_state["requested_actions"] and "court_details" in pending_action_params:
                court_params = pending_action_params.get("court_details", {})
                if "court_detail_fields" in court_params:
                    flow_state["court_detail_fields"] = court_params["court_detail_fields"]
                    logger.debug(f"Restored court_detail_fields from pending params: {flow_state['court_detail_fields']}")
            
            # Restore availability params if availability action is resuming
            if "availability" in flow_state["requested_actions"] and "availability" in pending_action_params:
                availability_params = pending_action_params.get("availability", {})
                if "selected_start_time" in availability_params:
                    flow_state["selected_start_time"] = availability_params["selected_start_time"]
                    logger.debug(f"Restored selected_start_time from pending params: {flow_state['selected_start_time']}")
                if "selected_end_time" in availability_params:
                    flow_state["selected_end_time"] = availability_params["selected_end_time"]
                    logger.debug(f"Restored selected_end_time from pending params: {flow_state['selected_end_time']}")
                if "time_period" in availability_params:
                    flow_state["time_period"] = availability_params["time_period"]
                    logger.debug(f"Restored time_period from pending params: {flow_state['time_period']}")
        
        # Don't clear pending_actions yet - keep stored until fully executed
        
    else:
        # User asked something new OR didn't provide relevant info this turn - use only new actions
        # Keep pending_actions stored but don't restore them
        if requested_actions:
            flow_state["requested_actions"] = requested_actions
            logger.info(
                f"User asked new action for chat {chat_id}: "
                f"new={requested_actions}, keeping pending={pending_actions} stored (not resuming), "
                f"property_set_this_turn={property_set_this_turn}, court_set_this_turn={court_set_this_turn}, "
                f"date_set_this_turn={date_set_this_turn}"
            )
        else:
            # No new actions and not providing relevant info this turn - don't restore pending
            flow_state["requested_actions"] = []
            logger.debug(
                f"No new actions for chat {chat_id}, pending={pending_actions} not resumed "
                f"(user not providing relevant info this turn)"
            )

    state["flow_state"] = flow_state
    
    # Log validation result
    llm_logger = get_llm_logger()
    validation_summary = (
        f"Router Result: {router_result}\n\n"
        f"Validation Results:\n"
        f"  Property: {flow_state.get('property_name')} (ID: {flow_state.get('property_id')})\n"
        f"  Court: {flow_state.get('court_type')} (IDs: {flow_state.get('court_ids')})\n"
        f"  Date: {flow_state.get('selected_date')}\n"
        f"  Time: {flow_state.get('selected_start_time')} - {flow_state.get('selected_end_time')}\n"
        f"  Period: {flow_state.get('time_period')}\n"
        f"  Requested Actions: {flow_state.get('requested_actions')}\n"
        f"  Awaiting Input: {flow_state.get('awaiting_input')}\n"
        f"  Validation Error: {flow_state.get('validation_error')}"
    )
    llm_logger.log_llm_call(
        node_name="validate_and_update_state",
        prompt="[No LLM call - validates router result and updates flow_state]",
        response=validation_summary,
        parameters=None
    )
    
    # Track last node
    flow_state["last_node"] = "information-validate"
    state["flow_state"] = flow_state

    # Log final validation result
    logger.info(
        f"[VALIDATE FINAL RESULT] Chat {chat_id}:\n"
        f"  Property: {flow_state.get('property_name')} (ID: {flow_state.get('property_id')})\n"
        f"  Court: {flow_state.get('court_type')} (IDs: {flow_state.get('court_ids')})\n"
        f"  Date: {flow_state.get('selected_date')}\n"
        f"  Time: {flow_state.get('selected_start_time')} - {flow_state.get('selected_end_time')}\n"
        f"  Period: {flow_state.get('time_period')}\n"
        f"  Requested Actions: {flow_state.get('requested_actions')}\n"
        f"  Awaiting Input: {flow_state.get('awaiting_input')}\n"
        f"  Validation Error: {flow_state.get('validation_error')}"
    )

    return state


# =====================================================
# MATCH HELPERS
# =====================================================

# Sport name synonyms/aliases for flexible matching
SPORT_SYNONYMS = {
    "football": ["futsal", "soccer"],
    "soccer": ["futsal", "football"],
    "futsal": ["football", "soccer"],
    "badminton": ["shuttle", "shuttlecock"],
    "table tennis": ["ping pong", "tt"],
    "ping pong": ["table tennis", "tt"],
    "basketball": ["basket", "hoops"],
    "tennis": ["lawn tennis"],
    "cricket": ["indoor cricket"],
}


def _normalize_sport_name(name: str) -> str:
    """Normalize sport name for matching (lowercase, strip)."""
    return name.lower().strip()


def _get_sport_aliases(sport_name: str) -> List[str]:
    """Get all aliases for a sport name including the original."""
    normalized = _normalize_sport_name(sport_name)
    aliases = [normalized]
    
    # Add synonyms if they exist
    if normalized in SPORT_SYNONYMS:
        aliases.extend(SPORT_SYNONYMS[normalized])
    
    return aliases

def _resolve_property_selection(
    mentioned_name: Optional[str],
    available_properties: List[Dict],
    chat_id: str
) -> Optional[Dict]:

    if not mentioned_name or not available_properties:
        return None

    try:
        index = int(mentioned_name) - 1
        if 0 <= index < len(available_properties):
            return available_properties[index]
    except (ValueError, TypeError):
        pass

    return _match_property(mentioned_name, available_properties, chat_id)


def _resolve_court_selection(
    mentioned_name: Optional[str],
    available_courts: List[Dict],
    property_id: Optional[int],
    chat_id: str
) -> tuple[Optional[str], List[int]]:
    """
    Resolve court selection to sport type and matching court IDs.
    
    Returns:
        tuple: (sport_type, [court_ids]) or (None, [])
    """
    if not mentioned_name or not available_courts:
        return None, []

    filtered = _filter_courts_by_property(available_courts, property_id)

    try:
        index = int(mentioned_name) - 1
        if 0 <= index < len(filtered):
            # Get unique sport types from filtered courts
            unique_sport_types = []
            for court in filtered:
                sport_types = court.get("sport_types", [])
                for st in sport_types:
                    if st not in unique_sport_types:
                        unique_sport_types.append(st)
            
            # User selected by index - get the sport type at that index
            if 0 <= index < len(unique_sport_types):
                selected_sport = unique_sport_types[index]
                # Find all courts with this sport type
                matching_ids = []
                for court in filtered:
                    if selected_sport in court.get("sport_types", []):
                        matching_ids.append(court["id"])
                return selected_sport, matching_ids
    except (ValueError, TypeError):
        pass

    return _match_court(mentioned_name, available_courts, property_id, chat_id)


def _match_property(
    property_name: str,
    available_properties: List[Dict],
    chat_id: str
) -> Optional[Dict]:
    """
    Match property by name with fuzzy matching.
    
    Matching priority:
    1. Exact name match
    2. Starts-with match
    3. Contains match (partial)
    4. Description match (fallback)
    """
    name_lower = _normalize_sport_name(property_name)

    # Level 1: Exact match
    for prop in available_properties:
        pname = _normalize_sport_name(prop.get("name") or "")
        if pname == name_lower:
            logger.debug(f"Exact property match: '{property_name}' → {prop.get('id')}")
            return prop

    # Level 2: Starts-with match
    for prop in available_properties:
        pname = _normalize_sport_name(prop.get("name") or "")
        if pname.startswith(name_lower):
            logger.debug(f"Starts-with property match: '{property_name}' → {prop.get('id')}")
            return prop

    # Level 3: Contains match (partial)
    for prop in available_properties:
        pname = _normalize_sport_name(prop.get("name") or "")
        if name_lower in pname or pname in name_lower:
            logger.debug(f"Partial property match: '{property_name}' → {prop.get('id')}")
            return prop

    # Level 4: Description match (fallback)
    for prop in available_properties:
        description = _normalize_sport_name(prop.get("description") or "")
        if description and name_lower in description:
            logger.debug(f"Description property match: '{property_name}' → {prop.get('id')}")
            return prop

    logger.warning(f"No property match for '{property_name}' chat {chat_id}")
    return None


def _match_court(
    court_name: str,
    available_courts: List[Dict],
    property_id: Optional[int],
    chat_id: str
) -> Optional[Dict]:
    """
    Match court by sport_type, name, or description with fuzzy matching.
    
    Matching priority:
    1. Exact sport_type match
    2. Synonym sport_type match (football → futsal)
    3. Exact name match
    4. Partial sport_type match (contains)
    5. Partial name match (contains)
    6. Description match (contains)
    """
    name_lower = _normalize_sport_name(court_name)
    user_aliases = _get_sport_aliases(court_name)

    filtered = _filter_courts_by_property(available_courts, property_id)

    # Level 1: Exact sport_type match
    for court in filtered:
        sport_type = _normalize_sport_name(court.get("sport_type") or "")
        if sport_type == name_lower:
            logger.debug(f"Exact sport_type match: '{court_name}' → {court.get('id')}")
            return court

    # Level 2: Synonym sport_type match (football → futsal)
    for court in filtered:
        sport_type = _normalize_sport_name(court.get("sport_type") or "")
        court_aliases = _get_sport_aliases(sport_type)
        
        # Check if any user alias matches any court alias
        if any(alias in court_aliases for alias in user_aliases):
            logger.debug(f"Synonym sport_type match: '{court_name}' → {court.get('id')} (via {sport_type})")
            return court

    # Level 3: Exact name match
    for court in filtered:
        cname = _normalize_sport_name(court.get("name") or "")
        if cname == name_lower:
            logger.debug(f"Exact name match: '{court_name}' → {court.get('id')}")
            return court

    # Level 4: Partial sport_type match (contains)
    for court in filtered:
        sport_type = _normalize_sport_name(court.get("sport_type") or "")
        if name_lower in sport_type or sport_type in name_lower:
            logger.debug(f"Partial sport_type match: '{court_name}' → {court.get('id')}")
            return court

    # Level 5: Partial name match (contains)
    for court in filtered:
        cname = _normalize_sport_name(court.get("name") or "")
        if name_lower in cname or cname in name_lower:
            logger.debug(f"Partial name match: '{court_name}' → {court.get('id')}")
            return court

    # Level 6: Description match (contains) - fallback
    for court in filtered:
        description = _normalize_sport_name(court.get("description") or "")
        if description and name_lower in description:
            logger.debug(f"Description match: '{court_name}' → {court.get('id')}")
            return court

    logger.warning(f"No court match for '{court_name}' chat {chat_id}")
    return None


def _match_court(
    court_name: str,
    available_courts: List[Dict],
    property_id: Optional[int],
    chat_id: str
) -> tuple[Optional[str], List[int]]:
    """
    Match court by sport_type, name, or description with fuzzy matching.
    
    Returns tuple: (sport_type, [court_ids])
    
    Matching priority:
    1. Exact sport_type match in sport_types array
    2. Synonym sport_type match (football → futsal)
    3. Exact name match
    4. Partial sport_type match (contains)
    5. Partial name match (contains)
    6. Description match (contains)
    """
    name_lower = _normalize_sport_name(court_name)
    user_aliases = _get_sport_aliases(court_name)

    filtered = _filter_courts_by_property(available_courts, property_id)

    # Level 1: Exact sport_type match in sport_types array
    for court in filtered:
        sport_types = court.get("sport_types", [])
        for sport_type in sport_types:
            if _normalize_sport_name(sport_type) == name_lower:
                logger.debug(f"Exact sport_type match: '{court_name}' → {sport_type}")
                # Find all courts with this sport type
                matching_ids = []
                for c in filtered:
                    if sport_type in c.get("sport_types", []):
                        matching_ids.append(c["id"])
                return sport_type, matching_ids

    # Level 2: Synonym sport_type match (football → futsal)
    for court in filtered:
        sport_types = court.get("sport_types", [])
        for sport_type in sport_types:
            court_aliases = _get_sport_aliases(sport_type)
            # Check if any user alias matches any court alias
            if any(alias in court_aliases for alias in user_aliases):
                logger.debug(f"Synonym sport_type match: '{court_name}' → {sport_type}")
                # Find all courts with this sport type
                matching_ids = []
                for c in filtered:
                    if sport_type in c.get("sport_types", []):
                        matching_ids.append(c["id"])
                return sport_type, matching_ids

    # Level 3: Exact name match - return first sport type of that court
    for court in filtered:
        cname = _normalize_sport_name(court.get("name") or "")
        if cname == name_lower:
            logger.debug(f"Exact name match: '{court_name}' → {court.get('id')}")
            sport_types = court.get("sport_types", [])
            if sport_types:
                return sport_types[0], [court["id"]]
            return court.get("name"), [court["id"]]

    # Level 4: Partial sport_type match (contains)
    for court in filtered:
        sport_types = court.get("sport_types", [])
        for sport_type in sport_types:
            sport_type_lower = _normalize_sport_name(sport_type)
            if name_lower in sport_type_lower or sport_type_lower in name_lower:
                logger.debug(f"Partial sport_type match: '{court_name}' → {sport_type}")
                # Find all courts with this sport type
                matching_ids = []
                for c in filtered:
                    if sport_type in c.get("sport_types", []):
                        matching_ids.append(c["id"])
                return sport_type, matching_ids

    # Level 5: Partial name match (contains)
    for court in filtered:
        cname = _normalize_sport_name(court.get("name") or "")
        if name_lower in cname or cname in name_lower:
            logger.debug(f"Partial name match: '{court_name}' → {court.get('id')}")
            sport_types = court.get("sport_types", [])
            if sport_types:
                return sport_types[0], [court["id"]]
            return court.get("name"), [court["id"]]

    # Level 6: Description match (contains) - fallback
    for court in filtered:
        description = _normalize_sport_name(court.get("description") or "")
        if description and name_lower in description:
            logger.debug(f"Description match: '{court_name}' → {court.get('id')}")
            sport_types = court.get("sport_types", [])
            if sport_types:
                return sport_types[0], [court["id"]]
            return court.get("name"), [court["id"]]

    logger.warning(f"No court match for '{court_name}' chat {chat_id}")
    return None, []


def _filter_courts_by_property(
    courts: List[Dict],
    property_id: Optional[int]
) -> List[Dict]:

    if not property_id:
        return courts

    return [c for c in courts if c.get("property_id") == property_id]


def _is_iso_date(date_str: str) -> bool:
    """
    Check if a string is a valid ISO date format (YYYY-MM-DD).
    
    Args:
        date_str: String to check
        
    Returns:
        True if valid ISO date, False otherwise
    """
    if not date_str or len(date_str) != 10:
        return False
    
    try:
        from datetime import datetime
        datetime.fromisoformat(date_str)
        return True
    except (ValueError, TypeError):
        return False


def _floor_time_to_hour(time_str: str, chat_id: str) -> str:
    """
    Floor time to nearest hour (round down) ONLY if minutes are specified.
    Also normalizes raw hour numbers to HH:00 format.
    
    Examples:
        "1:45" → "01:00" (has minutes, round down)
        "2:30" → "02:00" (has minutes, round down)
        "14:15" → "14:00" (has minutes, round down)
        "18:00" → "18:00" (already on hour, no change)
        "6" → "06:00" (raw number, normalize to HH:00)
        "18" → "18:00" (raw number, normalize to HH:00)
    
    Args:
        time_str: Time string in various formats (H:MM, HH:MM, H, HH, etc.)
        chat_id: Chat ID for logging
        
    Returns:
        Time string in HH:00 format
    """
    try:
        from datetime import datetime
        
        # Check if time has colon (indicates minutes are specified)
        if ':' not in time_str:
            # No colon means just hour number - normalize to HH:00 format
            try:
                hour = int(time_str)
                if 0 <= hour <= 23:
                    normalized = f"{hour:02d}:00"
                    logger.info(f"Normalized raw hour '{time_str}' → '{normalized}' for chat {chat_id}")
                    return normalized
                else:
                    logger.warning(f"Invalid hour value '{time_str}' for chat {chat_id}")
                    return time_str
            except ValueError:
                logger.warning(f"Could not parse raw hour '{time_str}' for chat {chat_id}")
                return time_str
        
        # Try to parse various time formats with colon
        for fmt in ["%H:%M", "%I:%M", "%H:%M:%S", "%I:%M:%S"]:
            try:
                parsed = datetime.strptime(time_str, fmt)
                # Floor to hour (just take the hour, set minutes to 00)
                floored = f"{parsed.hour:02d}:00"
                if floored != time_str:
                    logger.info(f"Floored start_time '{time_str}' → '{floored}' for chat {chat_id}")
                return floored
            except ValueError:
                continue
        
        # If no format matched, return as-is
        logger.warning(f"Could not parse time '{time_str}' for flooring in chat {chat_id}")
        return time_str
        
    except Exception as e:
        logger.error(f"Error flooring time '{time_str}' for chat {chat_id}: {e}")
        return time_str


def _ceil_time_to_hour(time_str: str, chat_id: str) -> str:
    """
    Ceil time to nearest hour (round up) ONLY if minutes are specified.
    Also normalizes raw hour numbers to HH:00 format.
    
    Examples:
        "1:45" → "02:00" (has minutes, round up)
        "2:30" → "03:00" (has minutes, round up)
        "14:15" → "15:00" (has minutes, round up)
        "18:00" → "18:00" (already on hour, no change)
        "7" → "07:00" (raw number, normalize to HH:00)
        "19" → "19:00" (raw number, normalize to HH:00)
    
    Args:
        time_str: Time string in various formats (H:MM, HH:MM, H, HH, etc.)
        chat_id: Chat ID for logging
        
    Returns:
        Time string in HH:00 format
    """
    try:
        from datetime import datetime
        
        # Check if time has colon (indicates minutes are specified)
        if ':' not in time_str:
            # No colon means just hour number - normalize to HH:00 format
            try:
                hour = int(time_str)
                if 0 <= hour <= 23:
                    normalized = f"{hour:02d}:00"
                    logger.info(f"Normalized raw hour '{time_str}' → '{normalized}' for chat {chat_id}")
                    return normalized
                else:
                    logger.warning(f"Invalid hour value '{time_str}' for chat {chat_id}")
                    return time_str
            except ValueError:
                logger.warning(f"Could not parse raw hour '{time_str}' for chat {chat_id}")
                return time_str
        
        # Try to parse various time formats with colon
        for fmt in ["%H:%M", "%I:%M", "%H:%M:%S", "%I:%M:%S"]:
            try:
                parsed = datetime.strptime(time_str, fmt)
                # Ceil to hour (if minutes > 0, add 1 hour)
                if parsed.minute > 0 or parsed.second > 0:
                    ceiled_hour = (parsed.hour + 1) % 24
                    ceiled = f"{ceiled_hour:02d}:00"
                    logger.info(f"Ceiled end_time '{time_str}' → '{ceiled}' for chat {chat_id}")
                    return ceiled
                else:
                    # Already on the hour
                    return f"{parsed.hour:02d}:00"
            except ValueError:
                continue
        
        # If no format matched, return as-is
        logger.warning(f"Could not parse time '{time_str}' for ceiling in chat {chat_id}")
        return time_str
        
    except Exception as e:
        logger.error(f"Error ceiling time '{time_str}' for chat {chat_id}: {e}")
        return time_str


# =====================================================
# DATE NORMALIZATION HELPERS
# =====================================================

def _normalize_date(
    date_interpretation: Optional[str],
    mentioned_date_text: Optional[str],
    chat_id: str
) -> Optional[str]:
    """
    Convert date interpretation to actual date string in YYYY-MM-DD format.
    Uses Asia/Karachi timezone for "today" and relative dates.
    
    Args:
        date_interpretation: Normalized interpretation from router (e.g., "today", "tomorrow", "next_monday")
        mentioned_date_text: Original text mentioned by user
        chat_id: Chat ID for logging
        
    Returns:
        Date string in YYYY-MM-DD format, or None if invalid
        
    Examples:
        _normalize_date("today", "aaj", "123") → "2026-03-13"
        _normalize_date("tomorrow", "kal", "123") → "2026-03-14"
        _normalize_date("next_monday", "next Monday", "123") → "2026-03-17"
    """
    if not date_interpretation:
        logger.warning(f"No date_interpretation provided for chat {chat_id}")
        return None
    
    try:
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        
        # Use Asia/Karachi timezone
        tz = ZoneInfo("Asia/Karachi")
        now = datetime.now(tz)
        today = now.date()
        
        # Handle different interpretations
        if date_interpretation == "today":
            result = today.isoformat()
            logger.info(f"Normalized 'today' to {result} for chat {chat_id}")
            return result
        
        elif date_interpretation == "tonight":
            # Tonight means today (same date, just evening/night time)
            result = today.isoformat()
            logger.info(f"Normalized 'tonight' to {result} for chat {chat_id}")
            return result
        
        elif date_interpretation == "tomorrow":
            result = (today + timedelta(days=1)).isoformat()
            logger.info(f"Normalized 'tomorrow' to {result} for chat {chat_id}")
            return result
        
        elif date_interpretation == "parso" or date_interpretation == "day_after_tomorrow":
            result = (today + timedelta(days=2)).isoformat()
            logger.info(f"Normalized 'parso/day_after_tomorrow' to {result} for chat {chat_id}")
            return result
        
        elif date_interpretation.startswith("next_"):
            # Extract day name (next_monday → monday)
            day_name = date_interpretation.replace("next_", "")
            return _get_next_weekday(today, day_name, chat_id)
        
        elif date_interpretation.startswith("this_"):
            # Extract day name (this_sunday → sunday)
            day_name = date_interpretation.replace("this_", "")
            return _get_this_weekday(today, day_name, chat_id)
        
        else:
            # Try to parse as ISO date (YYYY-MM-DD)
            try:
                parsed_date = datetime.fromisoformat(date_interpretation).date()
                result = parsed_date.isoformat()
                logger.info(f"Parsed ISO date {date_interpretation} to {result} for chat {chat_id}")
                return result
            except ValueError:
                logger.warning(
                    f"Unknown date_interpretation '{date_interpretation}' for chat {chat_id}"
                )
                return None
    
    except Exception as e:
        logger.error(f"Error normalizing date for chat {chat_id}: {e}", exc_info=True)
        return None


def _get_next_weekday(from_date, day_name: str, chat_id: str) -> Optional[str]:
    """
    Get the next occurrence of a weekday from a given date.
    
    Args:
        from_date: Starting date
        day_name: Name of the day (monday, tuesday, etc.)
        chat_id: Chat ID for logging
        
    Returns:
        Date string in YYYY-MM-DD format
    """
    from datetime import timedelta
    
    # Map day names to weekday numbers (0=Monday, 6=Sunday)
    day_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6
    }
    
    day_name_lower = day_name.lower()
    if day_name_lower not in day_map:
        logger.warning(f"Unknown day name '{day_name}' for chat {chat_id}")
        return None
    
    target_weekday = day_map[day_name_lower]
    current_weekday = from_date.weekday()
    
    # Calculate days until next occurrence
    # If today is Monday (0) and target is Wednesday (2): 2 - 0 = 2 days
    # If today is Wednesday (2) and target is Monday (0): (0 - 2) % 7 = 5 days
    days_ahead = target_weekday - current_weekday
    
    # If the day is today or in the past this week, get next week's occurrence
    if days_ahead <= 0:
        days_ahead += 7
    
    result_date = from_date + timedelta(days=days_ahead)
    result = result_date.isoformat()
    
    logger.info(
        f"Calculated next {day_name} from {from_date} as {result} for chat {chat_id}"
    )
    
    return result


def _get_this_weekday(from_date, day_name: str, chat_id: str) -> Optional[str]:
    """
    Get the occurrence of a weekday in the current week.
    If the day has passed, get next week's occurrence.
    
    Args:
        from_date: Starting date
        day_name: Name of the day (monday, tuesday, etc.)
        chat_id: Chat ID for logging
        
    Returns:
        Date string in YYYY-MM-DD format
    """
    from datetime import timedelta
    
    # Map day names to weekday numbers (0=Monday, 6=Sunday)
    day_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6
    }
    
    day_name_lower = day_name.lower()
    if day_name_lower not in day_map:
        logger.warning(f"Unknown day name '{day_name}' for chat {chat_id}")
        return None
    
    target_weekday = day_map[day_name_lower]
    current_weekday = from_date.weekday()
    
    # Calculate days until target day
    days_ahead = target_weekday - current_weekday
    
    # If the day has passed this week, get next week's occurrence
    if days_ahead < 0:
        days_ahead += 7
    
    result_date = from_date + timedelta(days=days_ahead)
    result = result_date.isoformat()
    
    logger.info(
        f"Calculated this {day_name} from {from_date} as {result} for chat {chat_id}"
    )
    
    return result

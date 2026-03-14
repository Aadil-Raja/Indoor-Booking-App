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
from app.agent.nodes.information.utils.matching_utils import (
    _match_property,
    _match_court,
    _resolve_property_selection,
    _resolve_court_selection,
)
from app.agent.nodes.information.utils.date_time_utils import (
    _is_iso_date,
    _floor_time_to_hour,
    _ceil_time_to_hour,
    _normalize_date,
)

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
        
        # Save property/court related requested_actions as pending so next turn can resume
        # Skip availability (it needs date which is the unclear part)
        non_availability_actions = [a for a in requested_actions if a != "availability"]
        if non_availability_actions:
            existing_pending = flow_state.get("pending_actions", [])
            merged_pending = list(existing_pending)
            for action in non_availability_actions:
                if action not in merged_pending:
                    merged_pending.append(action)
            flow_state["pending_actions"] = merged_pending
            
            # Save field params for property/court actions
            pending_params = flow_state.get("pending_action_params", {})
            if "property_details" in non_availability_actions:
                pending_params["property_details"] = {
                    "property_detail_fields": router_result.get("property_detail_fields") or ["all"]
                }
            if "court_details" in non_availability_actions:
                pending_params["court_details"] = {
                    "court_detail_fields": router_result.get("court_detail_fields") or ["all"]
                }
            flow_state["pending_action_params"] = pending_params
            
            logger.info(f"[UNCLEAR] Saved pending actions for chat {chat_id}: {merged_pending}")
        
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
    # If LLM says "pending_reply" but user has requested actions, it's likely a new request.
    # Exception: "availability" in requested_actions is expected when reply_target="date_selection"
    # because the router always adds "availability" when date/time intent is detected.
    non_availability_requested = [a for a in requested_actions if a != "availability"]
    if message_type == "pending_reply" and non_availability_requested:
        logger.warning(
            f"[PENDING_REPLY CORRECTION] Chat {chat_id}: "
            f"LLM set message_type='pending_reply' but user requested non-availability actions: {non_availability_requested}. "
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
    
    # Additional check: If "mixed" but no mentioned property/court, it's just new_request.
    # Exception: if reply_target="date_selection" with only availability action, that's valid.
    if (
        message_type == "mixed"
        and not mentioned_property_name
        and not mentioned_court_name
        and reply_target != "date_selection"
    ):
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
    # PROPERTY VALIDATION (reply or mention)
    # ---------------------------------
    is_property_reply = reply_target == "property_selection"

    if is_property_reply and not mentioned_property_name:
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

    elif mentioned_property_name and (is_property_reply or not reply_target):
        matched_property = (
            _resolve_property_selection(mentioned_property_name, available_properties, chat_id)
            if is_property_reply
            else _match_property(mentioned_property_name, available_properties, chat_id)
        )

        if matched_property:
            if matched_property["id"] != current_property_id:
                property_changed = True
            flow_state["property_id"] = matched_property["id"]
            flow_state["property_name"] = matched_property.get("name")
            property_set_this_turn = True
            if is_property_reply or flow_state.get("awaiting_input") == "property_selection":
                flow_state["awaiting_input"] = None
                logger.info(f"Cleared awaiting_input (property_selection) for chat {chat_id}")
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
    # COURT VALIDATION (reply or mention)
    # ---------------------------------
    is_court_reply = reply_target == "court_selection"

    if is_court_reply and not mentioned_court_name:
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

    elif mentioned_court_name and (is_court_reply or not reply_target):
        matched_sport_type, matched_court_ids = (
            _resolve_court_selection(mentioned_court_name, available_courts, active_property_id, chat_id)
            if is_court_reply
            else _match_court(mentioned_court_name, available_courts, active_property_id, chat_id)
        )

        if matched_court_ids:
            flow_state["court_ids"] = matched_court_ids
            flow_state["court_type"] = matched_sport_type
            court_set_this_turn = True
            if is_court_reply or flow_state.get("awaiting_input") == "court_selection":
                flow_state["awaiting_input"] = None
                logger.info(f"Cleared awaiting_input (court_selection) for chat {chat_id}")
        else:
            flow_state["validation_error"] = "invalid_court"
            flow_state["awaiting_input"] = "court_selection"
            state["flow_state"] = flow_state
            return state

    # ---------------------------------
    # DATE VALIDATION (reply or mention)
    # ---------------------------------
    mentioned_date_text = router_result.get("mentioned_date_text")
    date_interpretation = router_result.get("date_interpretation")
    date_status = router_result.get("date_status", "not_provided")

    is_date_reply = reply_target == "date_selection"

    if is_date_reply and not mentioned_date_text:
        # LLM said reply_target=date_selection but no date in message — treat as new request
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

    elif mentioned_date_text and (is_date_reply or not reply_target):
        _VALID_DATE_INTERPRETATIONS = {
            "today", "tonight", "tomorrow", "parso", "day_after_tomorrow",
            "next_monday", "next_tuesday", "next_wednesday", "next_thursday",
            "next_friday", "next_saturday", "next_sunday",
            "this_monday", "this_tuesday", "this_wednesday", "this_thursday",
            "this_friday", "this_saturday", "this_sunday",
        }

        def _fail_date(bot_response: str = None):
            _save_non_availability_as_pending(flow_state, router_result, chat_id)
            flow_state["validation_error"] = "invalid_date"
            flow_state["awaiting_input"] = "date_selection"
            if bot_response:
                flow_state["bot_response"] = bot_response
            state["flow_state"] = flow_state

        if date_status == "interpretable" and date_interpretation:
            is_valid = (
                date_interpretation in _VALID_DATE_INTERPRETATIONS or
                date_interpretation.startswith("next_") or
                date_interpretation.startswith("this_") or
                _is_iso_date(date_interpretation)
            )

            if not is_valid:
                logger.warning(
                    f"Invalid date_interpretation '{date_interpretation}' for chat {chat_id} - "
                    f"asking for specific date"
                )
                _fail_date(
                    "Please specify a specific date:\n\n"
                    "📅 Relative dates: today, tomorrow, parso, next Monday\n"
                    "📅 Exact date: 2026-03-15 or March 15\n\n"
                    "You can also specify time:\n"
                    "🕐 Time period: morning, afternoon, evening, night\n"
                    "🕐 Exact slot: 6 to 7 PM, 18:00 to 19:00"
                )
                return state

            normalized_date = _normalize_date(date_interpretation, mentioned_date_text, chat_id)

            if normalized_date:
                flow_state["selected_date"] = normalized_date
                date_set_this_turn = True
                if is_date_reply or flow_state.get("awaiting_input") == "date_selection":
                    flow_state["awaiting_input"] = None
                logger.info(
                    f"Date validated for chat {chat_id}: "
                    f"'{mentioned_date_text}' → {normalized_date} (reply={is_date_reply})"
                )
            else:
                _fail_date()
                return state
        else:
            _fail_date()
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
        # TODO: consider adding `and not availability_was_pending` to let pending
        # resume logic handle it exclusively instead of both paths firing
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
    if not requested_actions and not reply_target and message_type != "pending_reply" and not mentioned_court_name and not mentioned_property_name:
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


def _save_non_availability_as_pending(
    flow_state: Dict[str, Any],
    router_result: Dict[str, Any],
    chat_id: str
) -> None:
    """
    Save property_details / court_details / media actions as pending when
    an invalid_date early return occurs. Availability is intentionally excluded
    because the date is the unclear part — it will be re-requested next turn.
    """
    requested_actions = router_result.get("requested_actions", [])
    non_avail_actions = [a for a in requested_actions if a != "availability"]

    if not non_avail_actions:
        return

    existing_pending = flow_state.get("pending_actions", [])
    merged_pending = list(existing_pending)
    for action in non_avail_actions:
        if action not in merged_pending:
            merged_pending.append(action)
    flow_state["pending_actions"] = merged_pending

    pending_params = flow_state.get("pending_action_params", {})
    if "property_details" in non_avail_actions:
        pending_params["property_details"] = {
            "property_detail_fields": router_result.get("property_detail_fields") or ["all"]
        }
    if "court_details" in non_avail_actions:
        pending_params["court_details"] = {
            "court_detail_fields": router_result.get("court_detail_fields") or ["all"]
        }
    flow_state["pending_action_params"] = pending_params

    logger.info(
        f"[INVALID DATE] Saved non-availability pending actions for chat {chat_id}: {merged_pending}"
    )



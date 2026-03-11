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

    # Handle unclear message early
    if unclear or message_type == "unclear":
        flow_state["validation_error"] = "unclear_message"
        flow_state["bot_response"] = "I couldn't understand that. Please try again."
        flow_state["last_node"] = "information-validate"
        state["flow_state"] = flow_state
        return state

    property_changed = False

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

        else:
            flow_state["validation_error"] = "invalid_court"
            flow_state["awaiting_input"] = "court_selection"
            state["flow_state"] = flow_state
            return state

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

    pending_actions = flow_state.get("pending_actions", [])

    # RULE: Only restore pending actions if user is replying to our question
    # If user asks something new, don't restore (will be cleared in check_requirements if we execute)
    is_replying_to_question = reply_target in ["property_selection", "court_selection"]

    if is_replying_to_question and pending_actions:
        # User is answering our question - restore pending actions
        if requested_actions:
            # Merge: new actions first, then add pending actions (deduplicated)
            combined = list(requested_actions)
            for action in pending_actions:
                if action not in combined:
                    combined.append(action)
            flow_state["requested_actions"] = combined
            logger.debug(
                f"User replied to question - merged actions for chat {chat_id}: "
                f"new={requested_actions}, pending={pending_actions}, combined={combined}"
            )
        else:
            # Only pending actions, no new ones
            flow_state["requested_actions"] = pending_actions
            logger.debug(f"User replied to question - restored pending actions for chat {chat_id}: {pending_actions}")
        
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
    else:
        # User asked something new (not replying) - use only new actions
        # Don't clear pending yet - let check_requirements decide based on whether we execute
        if requested_actions:
            flow_state["requested_actions"] = requested_actions
            logger.debug(
                f"User asked new action for chat {chat_id}: "
                f"new={requested_actions}, pending will be evaluated in check_requirements"
            )
        else:
            # No new actions and not replying - use pending if exists, else empty
            if pending_actions:
                flow_state["requested_actions"] = []
                logger.debug(f"No new actions for chat {chat_id}, pending={pending_actions} will be evaluated")

    state["flow_state"] = flow_state
    
    # Log validation result
    llm_logger = get_llm_logger()
    validation_summary = (
        f"Router Result: {router_result}\n\n"
        f"Validation Results:\n"
        f"  Property: {flow_state.get('property_name')} (ID: {flow_state.get('property_id')})\n"
        f"  Court: {flow_state.get('court_type')} (IDs: {flow_state.get('court_ids')})\n"
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
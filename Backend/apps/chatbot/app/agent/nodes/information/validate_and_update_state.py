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
    mentioned_property_name = router_result.get("mentioned_property_name")
    mentioned_court_name = router_result.get("mentioned_court_name")
    unclear = router_result.get("unclear")

    available_properties = flow_state.get("available_properties", [])
    available_courts = flow_state.get("available_courts", [])

    current_property_id = flow_state.get("property_id")
    current_court_id = flow_state.get("court_id")

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
    # PROPERTY REPLY RESOLUTION
    # ---------------------------------
    if reply_target == "property_selection":
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
        
        # Try to find a court with the same sport_type at the new property
        if old_court_type and available_courts:
            matching_court = None
            for court in available_courts:
                if (court.get("property_id") == new_property_id and 
                    court.get("sport_type") == old_court_type):
                    matching_court = court
                    break
            
            if matching_court:
                # Same court type exists at new property - preserve context
                logger.info(
                    f"Court type '{old_court_type}' exists at new property, "
                    f"updating court_id to {matching_court['id']}"
                )
                flow_state["court_id"] = matching_court["id"]
                flow_state["court_type"] = old_court_type
                # date and slot remain unchanged
            else:
                # Court type doesn't exist at new property - reset court only
                logger.info(
                    f"Court type '{old_court_type}' not found at new property, "
                    f"resetting court_id and court_type"
                )
                flow_state["court_id"] = None
                flow_state["court_type"] = None
                # date and slot remain unchanged
        else:
            # No previous court type - just reset court fields
            flow_state["court_id"] = None
            flow_state["court_type"] = None
            # date and slot remain unchanged

    active_property_id = flow_state.get("property_id")

    # ---------------------------------
    # COURT REPLY RESOLUTION
    # ---------------------------------
    if reply_target == "court_selection":

        matched_court = _resolve_court_selection(
            mentioned_court_name,
            available_courts,
            active_property_id,
            chat_id
        )

        if matched_court:

            flow_state["court_id"] = matched_court["id"]
            flow_state["court_type"] = (
                matched_court.get("sport_type")
                or matched_court.get("name")
            )

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

        matched_court = _match_court(
            mentioned_court_name,
            available_courts,
            active_property_id,
            chat_id
        )

        if matched_court:

            flow_state["court_id"] = matched_court["id"]
            flow_state["court_type"] = (
                matched_court.get("sport_type")
                or matched_court.get("name")
            )

        else:
            flow_state["validation_error"] = "invalid_court"
            flow_state["awaiting_input"] = "court_selection"
            state["flow_state"] = flow_state
            return state

    # ---------------------------------
    # REQUESTED ACTIONS (Merge with Pending)
    # ---------------------------------

    pending_actions = flow_state.get("pending_actions", [])

    if requested_actions and pending_actions:
        # Merge: new actions first, then add pending actions (deduplicated)
        combined = list(requested_actions)
        for action in pending_actions:
            if action not in combined:
                combined.append(action)
        flow_state["requested_actions"] = combined
        logger.debug(
            f"Merged actions for chat {chat_id}: "
            f"new={requested_actions}, pending={pending_actions}, combined={combined}"
        )
    elif pending_actions:
        # Only pending actions, no new ones
        flow_state["requested_actions"] = pending_actions
        logger.debug(f"Restored pending actions for chat {chat_id}: {pending_actions}")
    else:
        # Only new actions, no pending
        flow_state["requested_actions"] = requested_actions

    state["flow_state"] = flow_state
    
    # Log validation result
    llm_logger = get_llm_logger()
    validation_summary = (
        f"Router Result: {router_result}\n\n"
        f"Validation Results:\n"
        f"  Property: {flow_state.get('property_name')} (ID: {flow_state.get('property_id')})\n"
        f"  Court: {flow_state.get('court_type')} (ID: {flow_state.get('court_id')})\n"
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
        f"  Court: {flow_state.get('court_type')} (ID: {flow_state.get('court_id')})\n"
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
) -> Optional[Dict]:

    if not mentioned_name or not available_courts:
        return None

    filtered = _filter_courts_by_property(available_courts, property_id)

    try:
        index = int(mentioned_name) - 1
        if 0 <= index < len(filtered):
            return filtered[index]
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


def _filter_courts_by_property(
    courts: List[Dict],
    property_id: Optional[int]
) -> List[Dict]:

    if not property_id:
        return courts

    return [c for c in courts if c.get("property_id") == property_id]
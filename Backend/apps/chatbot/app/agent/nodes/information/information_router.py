"""
Information router node - analyzes user message and extracts intent.

Flow:
1. Run INFORMATION_ROUTER_PROMPT → extracts property/court/media intent + needs_availability_check signal
2. If needs_availability_check=true → run AVAILABILITY_ROUTER_PROMPT → extracts date/time fields
3. Merge both results into a single router_result and store in flow_state

Everything downstream (validate_and_update_state, check_requirements, etc.) is unchanged.
"""

import logging
import json
from typing import Dict, Any

from app.agent.state.conversation_state import ConversationState
from app.agent.prompts.information_prompts import (
    get_information_router_prompt,
    get_availability_router_prompt,
)
from app.agent.utils.llm_logger import get_llm_logger
from app.agent.utils.json_parser import parse_llm_json_response

logger = logging.getLogger(__name__)


def _deduplicate_list(items: list, chat_id: str, field_name: str) -> list:
    if not items or not isinstance(items, list):
        return items
    original = items
    deduplicated = list(dict.fromkeys(items))
    if len(original) != len(deduplicated):
        logger.info(f"Deduplicated {field_name} for chat {chat_id}: {original} -> {deduplicated}")
    return deduplicated


def _simplify_fields_with_all(fields: list, chat_id: str, field_name: str) -> list:
    if not fields or not isinstance(fields, list):
        return fields
    if "all" in fields:
        if len(fields) > 1:
            logger.info(f"Simplified {field_name} to ['all'] for chat {chat_id}: original={fields}")
        return ["all"]
    return fields


def _merge_router_results(info_result: Dict[str, Any], avail_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge information router result with availability router result.

    The information result owns: message_type, reply_target, requested_actions,
    property_detail_fields, court_detail_fields, mentioned_property_name,
    mentioned_court_name, unclear, unclear_reason.

    The availability result contributes: mentioned_date_text, date_interpretation,
    date_status, start_time, end_time, time_period.
    If availability reply_target is "date_selection" and info reply_target is null,
    promote it.
    """
    merged = dict(info_result)

    # Merge date/time fields from availability result
    merged["mentioned_date_text"] = avail_result.get("mentioned_date_text")
    merged["date_interpretation"] = avail_result.get("date_interpretation")
    merged["date_status"] = avail_result.get("date_status", "not_provided")
    merged["start_time"] = avail_result.get("start_time")
    merged["end_time"] = avail_result.get("end_time")
    merged["time_period"] = avail_result.get("time_period")

    # Promote date_selection reply_target if info prompt didn't catch it
    if avail_result.get("reply_target") == "date_selection" and not merged.get("reply_target"):
        merged["reply_target"] = "date_selection"

    return merged


async def information_router(
    state: ConversationState,
    llm_provider: Any
) -> ConversationState:
    """
    Route and analyze user message for information requests.

    Step 1: Run information prompt (property/court/media + availability signal).
    Step 2: If needs_availability_check=true, run availability prompt and merge.
    Step 3: Store merged result in flow_state["router_result"].
    """
    chat_id = state.get("chat_id")
    user_message = state.get("user_message", "")
    flow_state = state.get("flow_state", {})
    llm_logger = get_llm_logger()

    logger.info(f"Information router analyzing message for chat {chat_id}")

    # ------------------------------------------------------------------
    # STEP 1: Information prompt (property / court / media)
    # ------------------------------------------------------------------
    try:
        info_prompt = get_information_router_prompt(user_message, flow_state)
        logger.debug(f"Info router prompt for chat {chat_id}: {info_prompt[:200]}...")

        info_response = await llm_provider.generate(info_prompt)

        llm_logger.log_llm_call(
            node_name="information_router/info",
            prompt=info_prompt,
            response=info_response,
            parameters=None,
        )
        logger.info(f"[INFO ROUTER LLM RESPONSE] Chat {chat_id}:\n{info_response}")

        info_result = parse_llm_json_response(
            response=info_response,
            fallback={
                "message_type": "unclear",
                "reply_target": None,
                "requested_actions": [],
                "property_detail_fields": [],
                "court_detail_fields": [],
                "mentioned_property_name": None,
                "mentioned_court_name": None,
                "needs_availability_check": False,
                "unclear": True,
                "unclear_reason": "Failed to parse response",
            },
            context=f"information_router/info for chat {chat_id}",
        )

    except Exception as e:
        logger.error(f"Error in information_router (info step) for chat {chat_id}: {e}", exc_info=True)
        info_result = {
            "message_type": "unclear",
            "reply_target": None,
            "requested_actions": [],
            "property_detail_fields": [],
            "court_detail_fields": [],
            "mentioned_property_name": None,
            "mentioned_court_name": None,
            "needs_availability_check": False,
            "unclear": True,
            "unclear_reason": f"Error processing message: {str(e)}",
        }

    # ------------------------------------------------------------------
    # STEP 2: Availability prompt (date / time) — only if signalled
    # ------------------------------------------------------------------
    needs_availability_check = info_result.get("needs_availability_check", False)

    # Also trigger if awaiting_input is date_selection (user may be replying with a date)
    awaiting_input = flow_state.get("awaiting_input")
    if awaiting_input == "date_selection":
        needs_availability_check = True

    avail_result: Dict[str, Any] = {
        "reply_target": None,
        "mentioned_date_text": None,
        "date_interpretation": None,
        "date_status": "not_provided",
        "start_time": None,
        "end_time": None,
        "time_period": None,
    }

    if needs_availability_check:
        try:
            avail_prompt = get_availability_router_prompt(user_message, flow_state)
            logger.debug(f"Availability router prompt for chat {chat_id}: {avail_prompt[:200]}...")

            avail_response = await llm_provider.generate(avail_prompt)

            llm_logger.log_llm_call(
                node_name="information_router/availability",
                prompt=avail_prompt,
                response=avail_response,
                parameters=None,
            )
            logger.info(f"[AVAIL ROUTER LLM RESPONSE] Chat {chat_id}:\n{avail_response}")

            avail_result = parse_llm_json_response(
                response=avail_response,
                fallback=avail_result,
                context=f"information_router/availability for chat {chat_id}",
            )

        except Exception as e:
            logger.error(f"Error in information_router (availability step) for chat {chat_id}: {e}", exc_info=True)
            # Keep default avail_result (all nulls / not_provided)

    # ------------------------------------------------------------------
    # STEP 3: Merge results
    # ------------------------------------------------------------------
    if needs_availability_check:
        router_result = _merge_router_results(info_result, avail_result)
        logger.info(f"[ROUTER] Merged info + availability results for chat {chat_id}")
    else:
        # No availability — add the null date/time fields so downstream code doesn't break
        router_result = dict(info_result)
        router_result.update({
            "mentioned_date_text": None,
            "date_interpretation": None,
            "date_status": "not_provided",
            "start_time": None,
            "end_time": None,
            "time_period": None,
        })

    # ------------------------------------------------------------------
    # Clean up: deduplicate and simplify field lists
    # ------------------------------------------------------------------
    if "requested_actions" in router_result:
        router_result["requested_actions"] = _deduplicate_list(
            router_result["requested_actions"], chat_id, "requested_actions"
        )

    if "property_detail_fields" in router_result:
        fields = _deduplicate_list(router_result["property_detail_fields"], chat_id, "property_detail_fields")
        router_result["property_detail_fields"] = _simplify_fields_with_all(fields, chat_id, "property_detail_fields")

    if "court_detail_fields" in router_result:
        fields = _deduplicate_list(router_result["court_detail_fields"], chat_id, "court_detail_fields")
        router_result["court_detail_fields"] = _simplify_fields_with_all(fields, chat_id, "court_detail_fields")

    logger.info(f"[ROUTER FINAL RESULT] Chat {chat_id}: {json.dumps(router_result, indent=2)}")

    # Store in flow_state
    flow_state["router_result"] = router_result
    flow_state["last_node"] = "information-router"
    state["flow_state"] = flow_state

    logger.info(
        f"Router analysis complete for chat {chat_id}: "
        f"message_type={router_result.get('message_type')}, "
        f"actions={router_result.get('requested_actions')}, "
        f"needs_availability_check={needs_availability_check}"
    )

    return state

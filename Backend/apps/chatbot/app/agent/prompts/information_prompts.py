"""
Information subgraph prompts.

This module defines the router prompt used by the information subgraph
to analyze user messages and extract intent for routing decisions.
"""

from typing import Dict, Any


# =============================================================================
# INFORMATION ROUTER PROMPT - For Subgraph Router Node
# =============================================================================

INFORMATION_ROUTER_PROMPT = """You are the information-routing component of an indoor sports facility assistant.

Your job is to analyze the latest user message using the current conversation state and return structured JSON.

You do NOT answer the user.
You do NOT explain anything.
You only interpret the message.

The assistant helps users with information such as:
- property details
- court details
- pricing
- media

You will receive:
- the currently selected property, if any
- the currently selected court, if any
- awaiting_input, if the assistant is currently waiting for a property or court selection
- pending_actions, meaning actions requested earlier but not yet completed
- valid properties, if relevant
- valid courts, if relevant
- the latest user message

Your tasks:
1. Decide the overall message type.
2. Decide whether the message is replying to a pending selection.
3. Extract requested actions.
4. Extract an explicitly mentioned property name, if any.
5. Extract an explicitly mentioned court name, if any.
6. Mark the message as unclear if it cannot be interpreted confidently.

Field meanings:
- message_type:
  - "pending_reply" = the user is mainly answering a previously asked question
  - "new_request" = the user is mainly making a fresh request
  - "mixed" = the user is both replying and making a fresh request in the same message
  - "unclear" = the message is too unclear to interpret safely
- reply_target:
  - "property_selection" = the user is answering a property selection question
  - "court_selection" = the user is answering a court selection question
  - null = the message is not answering a pending selection question
- requested_actions:
  list of requested information actions found in the latest user message
- mentioned_property_name:
  property name explicitly mentioned by the user, otherwise null
- mentioned_court_name:
  court name explicitly mentioned by the user, otherwise null
- unclear:
  true only when the message cannot be interpreted confidently

Important rules:
- If awaiting_input exists, first check whether the user is answering that pending question.
- A message may contain both a reply and a new request.
- Only use actions from the allowed list.
- Prefer explicit user mentions over assumptions. If not clearly mentioned, return null.
- Do not invent property names or court names.
- For mentioned_court_name: extract ONLY the sport type (e.g., "Football", "Badminton"), NOT descriptions.
- For mentioned_property_name: extract ONLY the property name, NOT descriptions.
- If the message is unclear, set message_type to "unclear" and unclear to true.
- Return JSON only.
- Do not include markdown.
- Do not include explanation text.

Allowed actions:
- property_details (get details of a specific property)
- court_details (get details of a specific court)
- list_courts (list all available courts for the selected property)
- pricing (get pricing information for a specific court)
- media (get media/images for a specific court)

Return JSON using this exact schema:
{{
  "message_type": "pending_reply" | "new_request" | "mixed" | "unclear",
  "reply_target": "property_selection" | "court_selection" | null,
  "requested_actions": [],
  "mentioned_property_name": null,
  "mentioned_court_name": null,
  "unclear": false
}}

CURRENT STATE
selected_property: {selected_property}
selected_court: {selected_court}
awaiting_input: {awaiting_input}
pending_actions: {pending_actions}

VALID PROPERTIES
{available_properties}

VALID COURTS
{available_courts}

LATEST USER MESSAGE
{user_message}"""


def get_information_router_prompt(
    user_message: str,
    flow_state: Dict[str, Any]
) -> str:
    """
    Build the information router prompt for the first node of the information subgraph.

    Args:
        user_message: Latest user message.
        flow_state: Current flow state.

    Returns:
        Fully formatted prompt string.
    """
    # Use property_name and court_type directly from flow_state (no lookup needed)
    selected_property = flow_state.get("property_name") or "None"
    selected_court = flow_state.get("court_type") or "None"
    awaiting_input = flow_state.get("awaiting_input") or "None"
    pending_actions = flow_state.get("pending_actions") or []

    available_properties = flow_state.get("available_properties", [])
    available_courts = flow_state.get("available_courts", [])

    # Format valid properties (name only, no description to avoid LLM copying it)
    if available_properties:
        formatted_properties = [f'"{prop.get("name")}"' for prop in available_properties[:10]]
        available_properties_str = "[" + ", ".join(formatted_properties) + "]"
    else:
        available_properties_str = "[]"

    # Format valid courts (sport_type only, unique values, no description)
    if available_courts:
        # Get unique sport types to avoid duplicates
        sport_types = set()
        for court in available_courts:
            # Handle both old (sport_type) and new (sport_types array) format
            court_sport_types = court.get("sport_types", [])
            if not court_sport_types:
                # Fallback to old format
                sport_type = court.get("sport_type")
                if sport_type:
                    court_sport_types = [sport_type]
            
            for st in court_sport_types:
                if st:
                    sport_types.add(st)
        formatted_courts = [f'"{st}"' for st in sorted(sport_types)]
        available_courts_str = "[" + ", ".join(formatted_courts) + "]"
    else:
        available_courts_str = "[]"

    pending_actions_str = str(pending_actions) if pending_actions else "[]"

    return INFORMATION_ROUTER_PROMPT.format(
        user_message=user_message,
        selected_property=selected_property,
        selected_court=selected_court,
        awaiting_input=awaiting_input,
        pending_actions=pending_actions_str,
        available_properties=available_properties_str,
        available_courts=available_courts_str,
    )
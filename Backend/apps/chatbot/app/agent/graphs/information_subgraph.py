"""
Information subgraph for LangGraph conversation management.

This module implements the information flow subgraph that handles information
requests about properties, courts, pricing, and media.

Flow:
information_router → validate_and_update_state → check_requirements
  → [ask_property | ask_court | execute_actions] → format_response → END
"""

from typing import Dict, Any
import logging

from langgraph.graph import StateGraph, END

from app.agent.state.conversation_state import ConversationState
from app.agent.nodes.information import (
    information_router,
    validate_and_update_state,
    check_requirements,
    ask_property,
    ask_court,
    execute_actions,
    format_response,
)

logger = logging.getLogger(__name__)


def create_information_subgraph(llm_provider: Any) -> StateGraph:
    """
    Create the information flow subgraph.
    
    This function creates a LangGraph StateGraph that manages information
    requests about properties, courts, pricing, and media.
    
    Nodes:
    - information_router: Analyzes user message and extracts intent
    - validate_and_update_state: Validates and updates state
    - check_requirements: Checks what's needed for actions
    - ask_property: Asks user to select a property
    - ask_court: Asks user to select a court
    - execute_actions: Executes the requested actions
    - format_response: Formats the final response
    
    Args:
        llm_provider: LLM provider for router node
        
    Returns:
        Compiled StateGraph ready for execution
    """
    logger.info("Creating information subgraph")
    
    # Initialize graph with ConversationState
    graph = StateGraph(ConversationState)
    
    # Add all nodes with async wrappers
    async def information_router_node(state):
        return await information_router(state, llm_provider)
    
    async def validate_and_update_state_node(state):
        return await validate_and_update_state(state)
    
    async def check_requirements_node(state):
        return await check_requirements(state)
    
    async def ask_property_node(state):
        return await ask_property(state)
    
    async def ask_court_node(state):
        return await ask_court(state)
    
    async def execute_actions_node(state):
        return await execute_actions(state)
    
    async def format_response_node(state):
        return await format_response(state)
    
    graph.add_node("information_router", information_router_node)
    graph.add_node("validate_and_update_state", validate_and_update_state_node)
    graph.add_node("check_requirements", check_requirements_node)
    graph.add_node("ask_property", ask_property_node)
    graph.add_node("ask_court", ask_court_node)
    graph.add_node("execute_actions", execute_actions_node)
    graph.add_node("format_response", format_response_node)
    
    # Set entry point
    graph.set_entry_point("information_router")
    
    # Connect nodes: router → validate → check_requirements
    graph.add_edge("information_router", "validate_and_update_state")
    graph.add_edge("validate_and_update_state", "check_requirements")
    
    # Conditional routing from check_requirements based on next_step
    graph.add_conditional_edges(
        "check_requirements",
        route_check_requirements,
        {
            "ask_property": "ask_property",
            "ask_court": "ask_court",
            "execute_actions": "execute_actions"
        }
    )
    
    # ask_property and ask_court go to format_response
    graph.add_edge("ask_property", "format_response")
    graph.add_edge("ask_court", "format_response")
    
    # execute_actions goes to format_response
    graph.add_edge("execute_actions", "format_response")
    
    # format_response goes to END
    graph.add_edge("format_response", END)
    
    logger.info("Information subgraph created successfully")
    
    # Compile and return the graph
    return graph.compile()


def route_check_requirements(state: ConversationState) -> str:
    """
    Route based on next_step from check_requirements.
    
    This function reads flow_state["next_step"] and routes to:
    - "ask_property" if property is missing
    - "ask_court" if court is missing
    - "execute_actions" if all requirements met
    
    Args:
        state: ConversationState containing flow_state
        
    Returns:
        Next node name
    """
    flow_state = state.get("flow_state", {})
    next_step = flow_state.get("next_step", "execute_actions")
    
    logger.debug(f"Routing from check_requirements: next_step={next_step}")
    
    if next_step in ["ask_property", "ask_court", "execute_actions"]:
        return next_step
    else:
        logger.warning(f"Unknown next_step '{next_step}', defaulting to execute_actions")
        return "execute_actions"

"""
Main conversation graph - defines the flow of nodes.

Flow:
START → load_chat → intent_detection → [handler] → END

Handlers: greeting, information, booking, unavailable_service
"""

from typing import Dict, Any
import logging

from langgraph.graph import StateGraph, END

from app.agent.state.conversation_state import ConversationState
from app.agent.nodes.basic_nodes import load_chat
from app.agent.nodes.intent_detection import intent_detection
from app.agent.nodes.greeting import greeting_handler
from app.agent.nodes.unavailable_service import unavailable_service_handler
from app.agent.graphs.information_subgraph import create_information_subgraph
from app.agent.graphs.booking_subgraph import create_booking_subgraph

logger = logging.getLogger(__name__)


def create_main_graph(
    llm_provider: Any,
    tools: Dict[str, Any],
    chat_service: Any = None,
    message_service: Any = None
) -> StateGraph:
    """
    Create the conversation flow graph.
    
    What it does:
    1. Sets up all nodes (load, intent_detection, handlers)
    2. Connects them in order
    3. Routes to correct handler based on LLM's decision
    
    Flow:
    load_chat → intent_detection
      ↓
    LLM decides: "greeting" or "information" or "booking" or "unavailable_service"
      ↓
    Route to that handler → END
    """
    logger.info("Creating main graph")
    
    # Create graph
    graph = StateGraph(ConversationState)
    
    # Add basic nodes (load history) - use async lambda for async functions
    async def load_chat_wrapper(s):
        return await load_chat(s, chat_service, message_service)
    graph.add_node("load_chat", load_chat_wrapper)
    
    # Add intent detection (asks LLM where to route)
    async def intent_detection_wrapper(s):
        return await intent_detection(s, llm_provider)
    graph.add_node("intent_detection", intent_detection_wrapper)
    
    # Add handler nodes
    async def greeting_wrapper(s):
        return await greeting_handler(s, llm_provider)
    graph.add_node("greeting", greeting_wrapper)
    
    # Add unavailable service handler
    async def unavailable_service_wrapper(s):
        return await unavailable_service_handler(s, llm_provider)
    graph.add_node("unavailable_service", unavailable_service_wrapper)
    
    # Add information subgraph
    information_subgraph = create_information_subgraph(llm_provider)
    graph.add_node("information", information_subgraph)
    
    # Add booking subgraph
    booking_subgraph = create_booking_subgraph(tools)
    graph.add_node("booking", booking_subgraph)
    
    # Connect nodes in order (start at load_chat)
    graph.set_entry_point("load_chat")
    graph.add_edge("load_chat", "intent_detection")
    
    # Route based on LLM's decision
    graph.add_conditional_edges(
        "intent_detection",
        route_by_next_node,
        {
            "greeting": "greeting",
            "information": "information",
            "booking": "booking",
            "unavailable_service": "unavailable_service",
            "END": END  # For validation failures and irrelevant messages
        }
    )
    
    # All handlers go to END
    graph.add_edge("greeting", END)
    graph.add_edge("information", END)
    graph.add_edge("booking", END)
    graph.add_edge("unavailable_service", END)
    
    logger.info("Main graph created")
    return graph.compile()


def route_by_next_node(state: ConversationState) -> str:
    """
    Route to handler based on LLM's decision.
    
    LLM sets state["next_node"] to "greeting", "information", "booking", "unavailable_service", or None
    This function returns that value to route to the correct handler.
    
    If None (validation failed or irrelevant), returns END to stop processing.
    If unknown value, defaults to "information".
    """
    next_node = state.get("next_node", "information")
    
    # Handle None (validation failed or irrelevant message)
    if next_node is None:
        logger.info("next_node is None (validation/relevancy failed), ending conversation")
        return "END"
    
    valid_nodes = ["greeting", "information", "booking", "unavailable_service"]
    
    if next_node in valid_nodes:
        return next_node
    else:
        logger.warning(f"Unknown next_node '{next_node}', routing to information")
        return "information"

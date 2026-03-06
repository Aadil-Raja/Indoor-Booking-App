"""
Main conversation graph - defines the flow of nodes.

Flow:
START → load_chat → intent_detection → [handler] → END

Handlers: greeting, information, booking
"""

from typing import Dict, Any
import logging

from langgraph.graph import StateGraph, END

from app.agent.state.conversation_state import ConversationState
from app.agent.nodes.basic_nodes import load_chat
from app.agent.nodes.intent_detection import intent_detection
from app.agent.nodes.greeting import greeting_handler
# from app.agent.nodes.indoor_search import indoor_search_handler  # Replaced by information_handler
from app.agent.nodes.information import information_handler  # New LangChain agent-based node
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
    LLM decides: "greeting" or "information" or "booking"
      ↓
    Route to that handler → END
    """
    logger.info("Creating main graph")
    
    # Create graph
    graph = StateGraph(ConversationState)
    
    # Add basic nodes (load history)
    graph.add_node("load_chat", lambda s: load_chat(s, chat_service, message_service))
    
    # Add intent detection (asks LLM where to route)
    graph.add_node("intent_detection", lambda s: intent_detection(s, llm_provider))
    
    # Add handler nodes
    graph.add_node("greeting", lambda s: greeting_handler(s, llm_provider))
    graph.add_node("information", lambda s: information_handler(s, llm_provider))
    
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
        {"greeting": "greeting", "information": "information", "booking": "booking"}
    )
    
    # All handlers go to END
    graph.add_edge("greeting", END)
    graph.add_edge("information", END)
    graph.add_edge("booking", END)
    
    logger.info("Main graph created")
    return graph.compile()


def route_by_next_node(state: ConversationState) -> str:
    """
    Route to handler based on LLM's decision.
    
    LLM sets state["next_node"] to "greeting", "information", or "booking"
    This function returns that value to route to the correct handler.
    
    If unknown value, defaults to "information".
    """
    next_node = state.get("next_node", "information")
    
    valid_nodes = ["greeting", "information", "booking"]
    
    if next_node in valid_nodes:
        return next_node
    else:
        logger.warning(f"Unknown next_node '{next_node}', routing to information")
        return "information"

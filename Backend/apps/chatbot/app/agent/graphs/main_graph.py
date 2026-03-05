"""
Main conversation graph for LangGraph conversation management.

This module implements the main conversation flow graph that orchestrates the
entire chatbot interaction. The graph wires together all top-level nodes with
conditional routing based on detected intent.

The main graph includes:
- Basic flow nodes (receive_message, load_chat, append_user_message)
- Intent detection node
- Handler nodes (greeting, information)
- Booking subgraph (integrated as a node)

Requirements: 6.1-6.8
"""

from typing import Dict, Any
import logging

from langgraph.graph import StateGraph, END

from app.agent.state.conversation_state import ConversationState
from app.agent.nodes.basic_nodes import receive_message, load_chat, append_user_message
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
    Create the main conversation flow graph.
    
    This function creates the top-level LangGraph StateGraph that manages the
    entire conversation flow. The graph orchestrates:
    
    Flow:
    1. receive_message: Entry point, validates incoming message
    2. load_chat: Loads chat history and context
    3. append_user_message: Adds user message to bot_memory
    4. intent_detection: Uses LLM to determine next_node routing decision
    5. [Handler nodes]: Routes to appropriate handler based on LLM's next_node
       - greeting: Handles greetings
       - information: Handles facility search, availability, pricing, media (LangChain agent)
       - booking: Handles booking flow (subgraph)
    6. END: Terminates the graph execution
    
    Routing:
    - LLM-driven routing from intent_detection based on next_node decision
    - All handler nodes route to END
    - Unknown next_node values default to greeting handler
    
    Implements Requirements:
    - 2.1: LLM SHALL return next_node field
    - 2.2: Remove rule-based logic for intent determination
    - 2.3: LLM makes routing decisions
    - 2.4: Route to node specified by LLM's next_node decision
    - 6.1: LangGraph high-level graph with all required nodes
    - 6.2: Intent_Detection node routes to appropriate handler
    - 6.3: Booking_Subgraph integrated as a node
    - 6.4-6.5: Read and update flow_state and bot_memory
    - 6.6: Call tools to interact with existing services
    - 6.7: Invoke LLM_Provider for natural language generation
    - 6.8: Maintain state persistence between node transitions
    
    Args:
        llm_provider: LLMProvider instance for natural language generation
        tools: Tool registry containing all agent tools
        chat_service: Optional ChatService for dependency injection
        message_service: Optional MessageService for dependency injection
        
    Returns:
        Compiled StateGraph ready for execution
        
    Example:
        from ...services.llm.openai_provider import OpenAIProvider
        from ..tools import TOOL_REGISTRY
        
        llm = OpenAIProvider(api_key="...")
        tools = TOOL_REGISTRY
        
        main_graph = create_main_graph(llm, tools)
        
        # Execute the graph
        state = {
            "chat_id": "123",
            "user_id": "456",
            "owner_profile_id": "789",
            "user_message": "Hello",
            "flow_state": {},
            "bot_memory": {},
            "messages": [],
            ...
        }
        result = await main_graph.ainvoke(state)
    """
    logger.info("Creating main conversation graph")
    
    # Initialize graph with ConversationState
    graph = StateGraph(ConversationState)
    
    # Add basic flow nodes
    async def receive_message_node(state):
        return await receive_message(state, chat_service, message_service)
    
    async def load_chat_node(state):
        return await load_chat(state, chat_service, message_service)
    
    async def append_user_message_node(state):
        return await append_user_message(state, chat_service, message_service)
    
    graph.add_node("receive_message", receive_message_node)
    graph.add_node("load_chat", load_chat_node)
    graph.add_node("append_user_message", append_user_message_node)
    
    # Add intent detection node
    async def intent_detection_node(state):
        return await intent_detection(state, llm_provider)
    
    graph.add_node("intent_detection", intent_detection_node)
    
    # Add handler nodes
    async def greeting_node(state):
        return await greeting_handler(state, llm_provider)
    
    async def information_handler_node(state):
        return await information_handler(state, llm_provider)
    
    graph.add_node("greeting", greeting_node)
    graph.add_node("information", information_handler_node)
    
    # Add booking subgraph as a node
    booking_subgraph = create_booking_subgraph(tools)
    graph.add_node("booking", booking_subgraph)
    
    # Define the main flow edges
    graph.set_entry_point("receive_message")
    graph.add_edge("receive_message", "load_chat")
    graph.add_edge("load_chat", "append_user_message")
    graph.add_edge("append_user_message", "intent_detection")
    
    # Add conditional routing from intent detection based on LLM's next_node decision
    graph.add_conditional_edges(
        "intent_detection",
        route_by_next_node,
        {
            "greeting": "greeting",
            "information": "information",
            "booking": "booking"
        }
    )
    
    # All handler nodes route to END
    graph.add_edge("greeting", END)
    graph.add_edge("information", END)
    graph.add_edge("booking", END)
    
    logger.info("Main conversation graph created successfully")
    
    # Compile and return the graph
    return graph.compile()


def route_by_next_node(state: ConversationState) -> str:
    """
    Route to appropriate handler based on LLM's next_node decision.
    
    This function examines the next_node field in the ConversationState (set by
    the intent_detection node) and returns the corresponding handler node name.
    It's used as the routing function for the conditional edge from intent_detection.
    
    The function handles:
    - greeting: Route to greeting handler
    - information: Route to information node (LangChain agent)
    - booking: Route to booking subgraph
    - unknown/missing: Default to information handler (handles all informational queries)
    
    Implements Requirements:
    - 1.1: Remove FAQ node from conversation flow
    - 1.2: Route FAQ-like queries to information handler
    - 1.3: Route all informational queries to information handler
    - 2.1: LLM SHALL return next_node field
    - 2.4: Route to node specified by LLM's next_node decision
    
    Args:
        state: ConversationState containing the next_node decision
        
    Returns:
        Handler node name: "greeting", "information", or "booking"
        
    Example:
        state = {"next_node": "booking", ...}
        route = route_by_next_node(state)
        # Returns: "booking"
        
        state = {"next_node": "information", ...}
        route = route_by_next_node(state)
        # Returns: "information"
        
        state = {}  # Missing next_node
        route = route_by_next_node(state)
        # Returns: "information" (handles unknown intents)
    """
    next_node = state.get("next_node", "information")
    
    logger.debug(
        f"Routing by next_node for chat {state.get('chat_id')}: {next_node}"
    )
    
    # Validate next_node is one of the expected values
    valid_nodes = ["greeting", "information", "booking"]
    
    if next_node in valid_nodes:
        return next_node
    else:
        # Unknown or invalid next_node, default to information handler
        # This ensures FAQ-like queries and unknown intents are handled by information
        logger.warning(
            f"Unknown next_node '{next_node}' for chat {state.get('chat_id')}, "
            f"routing to information handler"
        )
        return "information"

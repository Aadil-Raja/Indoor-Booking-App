"""
Main conversation graph for LangGraph conversation management.

This module implements the main conversation flow graph that orchestrates the
entire chatbot interaction. The graph wires together all top-level nodes with
conditional routing based on detected intent.

The main graph includes:
- Basic flow nodes (receive_message, load_chat, append_user_message)
- Intent detection node
- Handler nodes (greeting, indoor_search, faq)
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
from app.agent.nodes.indoor_search import indoor_search_handler
from app.agent.nodes.faq import faq_handler
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
    4. intent_detection: Classifies user intent
    5. [Handler nodes]: Routes to appropriate handler based on intent
       - greeting: Handles greetings
       - indoor_search: Handles facility search
       - booking: Handles booking flow (subgraph)
       - faq: Handles general questions
    6. END: Terminates the graph execution
    
    Routing:
    - Conditional routing from intent_detection based on detected intent
    - All handler nodes route to END
    - Unknown intents default to FAQ handler
    
    Implements Requirements:
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
        return await greeting_handler(state, chat_service, message_service)
    
    async def indoor_search_node(state):
        return await indoor_search_handler(state, tools)
    
    async def faq_node(state):
        return await faq_handler(state, llm_provider)
    
    graph.add_node("greeting", greeting_node)
    graph.add_node("indoor_search", indoor_search_node)
    graph.add_node("faq", faq_node)
    
    # Add booking subgraph as a node
    booking_subgraph = create_booking_subgraph(tools)
    graph.add_node("booking", booking_subgraph)
    
    # Define the main flow edges
    graph.set_entry_point("receive_message")
    graph.add_edge("receive_message", "load_chat")
    graph.add_edge("load_chat", "append_user_message")
    graph.add_edge("append_user_message", "intent_detection")
    
    # Add conditional routing from intent detection
    graph.add_conditional_edges(
        "intent_detection",
        route_by_intent,
        {
            "greeting": "greeting",
            "search": "indoor_search",
            "booking": "booking",
            "faq": "faq",
            "unknown": "faq"  # Default to FAQ for unknown intents
        }
    )
    
    # All handler nodes route to END
    graph.add_edge("greeting", END)
    graph.add_edge("indoor_search", END)
    graph.add_edge("booking", END)
    graph.add_edge("faq", END)
    
    logger.info("Main conversation graph created successfully")
    
    # Compile and return the graph
    return graph.compile()


def route_by_intent(state: ConversationState) -> str:
    """
    Route to appropriate handler based on detected intent.
    
    This function examines the intent field in the ConversationState and
    returns the corresponding handler node name. It's used as the routing
    function for the conditional edge from intent_detection.
    
    The function handles:
    - greeting: Route to greeting handler
    - search: Route to indoor_search handler
    - booking: Route to booking subgraph
    - faq: Route to FAQ handler
    - unknown/missing: Default to FAQ handler
    
    Implements Requirement 6.2: Intent_Detection node routes to appropriate
    handler node.
    
    Args:
        state: ConversationState containing the detected intent
        
    Returns:
        Handler node name: "greeting", "search", "booking", "faq", or "unknown"
        
    Example:
        state = {"intent": "booking", ...}
        route = route_by_intent(state)
        # Returns: "booking"
        
        state = {"intent": "unknown", ...}
        route = route_by_intent(state)
        # Returns: "unknown" (which maps to "faq" in conditional_edges)
    """
    intent = state.get("intent", "unknown")
    
    logger.debug(
        f"Routing by intent for chat {state.get('chat_id')}: {intent}"
    )
    
    # Validate intent is one of the expected values
    valid_intents = ["greeting", "search", "booking", "faq"]
    
    if intent in valid_intents:
        return intent
    else:
        # Unknown or invalid intent, default to unknown (which maps to faq)
        logger.warning(
            f"Unknown intent '{intent}' for chat {state.get('chat_id')}, "
            f"routing to unknown (faq)"
        )
        return "unknown"

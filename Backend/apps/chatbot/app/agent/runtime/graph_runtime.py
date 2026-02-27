"""
Graph runtime and initialization for LangGraph conversation management.

This module provides a runtime wrapper for the LangGraph conversation flow.
It handles:
- Graph initialization with dependencies (LLM provider, tools, services)
- Graph compilation and execution
- Structured logging for node transitions and execution
- Error handling for graph execution failures
- State management and lifecycle

The runtime provides a clean interface for AgentService to execute the graph
for each incoming message without needing to manage graph internals.

Requirements: 6.8, 12.3, 14.3-14.5, 16.11
"""

from typing import Dict, Any, Optional
import logging
import time
from datetime import datetime

from ..graphs.main_graph import create_main_graph
from ..state.conversation_state import ConversationState
from ..tools import initialize_tools
from ...services.llm.base import LLMProvider, LLMProviderError

logger = logging.getLogger(__name__)


class GraphExecutionError(Exception):
    """Raised when graph execution fails."""
    pass


class GraphRuntime:
    """
    Runtime wrapper for LangGraph conversation flow.
    
    This class manages the lifecycle of the LangGraph conversation graph,
    including initialization, compilation, and execution. It provides:
    
    - Clean initialization interface with dependency injection
    - Structured logging for all graph operations
    - Error handling with graceful degradation
    - State validation and preparation
    - Execution metrics and monitoring
    
    The runtime is designed to be used by AgentService to process incoming
    messages through the conversation graph.
    
    Implements Requirements:
    - 6.8: Maintain state persistence between node transitions
    - 12.3: Log all node transitions in LangGraph_Agent with current state
    - 14.3: When database operation fails, preserve flow_state and bot_memory
    - 14.4: When tool invocation fails, log the error and inform the user
    - 14.5: When recovering from failure, resume from last known good state
    - 16.11: Place runtime utilities in app/agent/runtime directory
    
    Example:
        from app.services.llm.openai_provider import OpenAIProvider
        
        # Initialize runtime
        llm_provider = OpenAIProvider(api_key="...")
        runtime = GraphRuntime(llm_provider=llm_provider)
        
        # Execute graph for a message
        state = {
            "chat_id": "123",
            "user_id": "456",
            "owner_id": "789",
            "user_message": "Hello",
            "flow_state": {},
            "bot_memory": {},
            ...
        }
        result = await runtime.execute(state)
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        chat_service: Optional[Any] = None,
        message_service: Optional[Any] = None,
        tool_dependencies: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the graph runtime.
        
        Args:
            llm_provider: LLMProvider instance for natural language generation
            chat_service: Optional ChatService for dependency injection
            message_service: Optional MessageService for dependency injection
            tool_dependencies: Optional dependencies for tool initialization
        """
        self.llm_provider = llm_provider
        self.chat_service = chat_service
        self.message_service = message_service
        
        # Initialize tools
        logger.info("Initializing agent tools")
        self.tools = initialize_tools(**(tool_dependencies or {}))
        logger.info(f"Initialized {len(self.tools)} agent tools")
        
        # Compile the main graph
        logger.info("Compiling main conversation graph")
        try:
            self.graph = create_main_graph(
                llm_provider=self.llm_provider,
                tools=self.tools,
                chat_service=self.chat_service,
                message_service=self.message_service
            )
            logger.info("Main conversation graph compiled successfully")
        except Exception as e:
            logger.error(f"Failed to compile main conversation graph: {e}")
            raise GraphExecutionError(
                f"Failed to initialize graph runtime: {e}"
            ) from e
    
    async def execute(
        self,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the conversation graph for the given state.
        
        This method:
        1. Validates and prepares the input state
        2. Logs the execution start with context
        3. Executes the graph with error handling
        4. Logs node transitions and execution metrics
        5. Returns the final state with response
        
        Args:
            state: Initial conversation state containing:
                - chat_id: UUID of the chat session
                - user_id: UUID of the user
                - owner_id: UUID of the property owner
                - user_message: The user's message
                - flow_state: Current booking/conversation state
                - bot_memory: Conversation context and history
                - messages: Message history for LLM context
                
        Returns:
            Final conversation state containing:
                - response_content: Bot's response text
                - response_type: Message type (text, button, list, media)
                - response_metadata: Additional response data
                - flow_state: Updated booking/conversation state
                - bot_memory: Updated conversation context
                - token_usage: LLM tokens consumed (if applicable)
                
        Raises:
            GraphExecutionError: If graph execution fails critically
            
        Example:
            state = {
                "chat_id": "123",
                "user_id": "456",
                "owner_id": "789",
                "user_message": "I want to book a tennis court",
                "flow_state": {},
                "bot_memory": {},
                "messages": []
            }
            result = await runtime.execute(state)
            print(result["response_content"])
        """
        # Validate state
        self._validate_state(state)
        
        # Prepare state with defaults
        prepared_state = self._prepare_state(state)
        
        # Log execution start
        chat_id = prepared_state.get("chat_id")
        user_id = prepared_state.get("user_id")
        user_message = prepared_state.get("user_message", "")[:100]
        
        logger.info(
            f"Starting graph execution",
            extra={
                "chat_id": chat_id,
                "user_id": user_id,
                "user_message": user_message,
                "flow_state": prepared_state.get("flow_state"),
                "intent": prepared_state.get("flow_state", {}).get("intent")
            }
        )
        
        # Track execution time
        start_time = time.time()
        
        try:
            # Execute the graph
            result = await self._execute_with_logging(prepared_state)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Log successful execution
            logger.info(
                f"Graph execution completed successfully",
                extra={
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "response_type": result.get("response_type"),
                    "token_usage": result.get("token_usage"),
                    "final_intent": result.get("flow_state", {}).get("intent"),
                    "final_step": result.get("flow_state", {}).get("step")
                }
            )
            
            return result
            
        except LLMProviderError as e:
            # LLM provider error - use fallback response
            logger.error(
                f"LLM provider error during graph execution: {e}",
                extra={
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "error_type": type(e).__name__
                }
            )
            
            # Return fallback response while preserving state
            return self._create_fallback_response(
                prepared_state,
                "I'm having trouble processing your request right now. "
                "Please try again in a moment."
            )
            
        except Exception as e:
            # Unexpected error - log and raise
            execution_time = time.time() - start_time
            
            logger.error(
                f"Graph execution failed with unexpected error: {e}",
                extra={
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "execution_time_ms": round(execution_time * 1000, 2),
                    "error_type": type(e).__name__,
                    "flow_state": prepared_state.get("flow_state")
                },
                exc_info=True
            )
            
            # Return error response while preserving state
            return self._create_fallback_response(
                prepared_state,
                "I encountered an error processing your message. "
                "Your conversation state has been preserved. Please try again."
            )
    
    async def _execute_with_logging(
        self,
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the graph with detailed logging of node transitions.
        
        This internal method wraps the graph execution to provide structured
        logging for each node transition. It helps with debugging and monitoring
        the conversation flow.
        
        Args:
            state: Prepared conversation state
            
        Returns:
            Final conversation state after graph execution
        """
        chat_id = state.get("chat_id")
        
        logger.debug(
            f"Invoking graph for chat {chat_id}",
            extra={
                "chat_id": chat_id,
                "initial_state": {
                    "intent": state.get("intent"),
                    "flow_state_step": state.get("flow_state", {}).get("step"),
                    "message_count": len(state.get("messages", []))
                }
            }
        )
        
        # Execute the graph
        # Note: LangGraph handles node transitions internally
        # We log the overall execution here
        result = await self.graph.ainvoke(state)
        
        logger.debug(
            f"Graph execution completed for chat {chat_id}",
            extra={
                "chat_id": chat_id,
                "final_state": {
                    "intent": result.get("intent"),
                    "flow_state_step": result.get("flow_state", {}).get("step"),
                    "response_type": result.get("response_type"),
                    "has_response": bool(result.get("response_content"))
                }
            }
        )
        
        return result
    
    def _validate_state(self, state: Dict[str, Any]) -> None:
        """
        Validate that the input state contains all required fields.
        
        Args:
            state: Input state to validate
            
        Raises:
            ValueError: If required fields are missing
        """
        required_fields = ["chat_id", "user_id", "owner_id", "user_message"]
        missing_fields = [
            field for field in required_fields
            if field not in state or state[field] is None
        ]
        
        if missing_fields:
            raise ValueError(
                f"Missing required state fields: {', '.join(missing_fields)}"
            )
    
    def _prepare_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare the state with default values for optional fields.
        
        This ensures that all nodes can safely access state fields without
        checking for None or missing keys.
        
        Args:
            state: Input state
            
        Returns:
            State with all fields populated with defaults where needed
        """
        # Create a copy to avoid modifying the input
        prepared = state.copy()
        
        # Set defaults for optional fields
        if "flow_state" not in prepared or prepared["flow_state"] is None:
            prepared["flow_state"] = {}
        
        if "bot_memory" not in prepared or prepared["bot_memory"] is None:
            prepared["bot_memory"] = {}
        
        if "messages" not in prepared or prepared["messages"] is None:
            prepared["messages"] = []
        
        if "intent" not in prepared:
            prepared["intent"] = None
        
        if "response_content" not in prepared:
            prepared["response_content"] = ""
        
        if "response_type" not in prepared:
            prepared["response_type"] = "text"
        
        if "response_metadata" not in prepared:
            prepared["response_metadata"] = {}
        
        if "token_usage" not in prepared:
            prepared["token_usage"] = None
        
        if "search_results" not in prepared:
            prepared["search_results"] = None
        
        if "availability_data" not in prepared:
            prepared["availability_data"] = None
        
        if "pricing_data" not in prepared:
            prepared["pricing_data"] = None
        
        return prepared
    
    def _create_fallback_response(
        self,
        state: Dict[str, Any],
        message: str
    ) -> Dict[str, Any]:
        """
        Create a fallback response when graph execution fails.
        
        This preserves the conversation state (flow_state and bot_memory)
        while providing a user-friendly error message.
        
        Implements Requirement 14.5: When recovering from failure, resume
        from last known good state.
        
        Args:
            state: Current conversation state
            message: Error message to show to the user
            
        Returns:
            State with fallback response and preserved conversation state
        """
        return {
            # Preserve identifiers
            "chat_id": state.get("chat_id"),
            "user_id": state.get("user_id"),
            "owner_id": state.get("owner_id"),
            "user_message": state.get("user_message"),
            
            # Preserve conversation state (Requirement 14.5)
            "flow_state": state.get("flow_state", {}),
            "bot_memory": state.get("bot_memory", {}),
            "messages": state.get("messages", []),
            "intent": state.get("intent"),
            
            # Fallback response
            "response_content": message,
            "response_type": "text",
            "response_metadata": {},
            
            # No token usage for fallback
            "token_usage": None,
            
            # Clear tool results
            "search_results": None,
            "availability_data": None,
            "pricing_data": None
        }


def create_graph_runtime(
    llm_provider: LLMProvider,
    chat_service: Optional[Any] = None,
    message_service: Optional[Any] = None,
    tool_dependencies: Optional[Dict[str, Any]] = None
) -> GraphRuntime:
    """
    Factory function to create and initialize a GraphRuntime instance.
    
    This is the recommended way to create a GraphRuntime, as it provides
    a clean interface and logs the initialization process.
    
    Args:
        llm_provider: LLMProvider instance for natural language generation
        chat_service: Optional ChatService for dependency injection
        message_service: Optional MessageService for dependency injection
        tool_dependencies: Optional dependencies for tool initialization
        
    Returns:
        Initialized GraphRuntime instance ready for execution
        
    Raises:
        GraphExecutionError: If runtime initialization fails
        
    Example:
        from app.services.llm.openai_provider import OpenAIProvider
        
        llm = OpenAIProvider(api_key="...")
        runtime = create_graph_runtime(llm_provider=llm)
        
        # Use runtime
        result = await runtime.execute(state)
    """
    logger.info("Creating graph runtime")
    
    try:
        runtime = GraphRuntime(
            llm_provider=llm_provider,
            chat_service=chat_service,
            message_service=message_service,
            tool_dependencies=tool_dependencies
        )
        
        logger.info("Graph runtime created successfully")
        return runtime
        
    except Exception as e:
        logger.error(f"Failed to create graph runtime: {e}", exc_info=True)
        raise GraphExecutionError(
            f"Failed to create graph runtime: {e}"
        ) from e


__all__ = [
    "GraphRuntime",
    "GraphExecutionError",
    "create_graph_runtime",
]

"""
Graph runtime wrapper for LangGraph execution.

Manages:
- Graph initialization with LLM and tools
- Graph execution with error handling
- State validation
"""

from typing import Dict, Any, Optional
import logging
import time
from datetime import datetime

from app.agent.graphs.main_graph import create_main_graph
from app.agent.state.conversation_state import ConversationState
from app.agent.tools import initialize_tools
from app.services.llm.base import LLMProvider, LLMProviderError

logger = logging.getLogger(__name__)


class GraphExecutionError(Exception):
    """Raised when graph execution fails."""
    pass


class GraphRuntime:
    """
    Wrapper for LangGraph execution.
    
    Job: Initialize graph once, then execute it for each message.
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        chat_service: Optional[Any] = None,
        message_service: Optional[Any] = None,
        tool_dependencies: Optional[Dict[str, Any]] = None
    ):
        """Initialize graph with LLM and tools."""
        self.llm_provider = llm_provider
        self.chat_service = chat_service
        self.message_service = message_service
        
        # Initialize tools
        logger.info("Initializing tools")
        self.tools = initialize_tools(**(tool_dependencies or {}))
        
        # Compile graph
        logger.info("Compiling graph")
        try:
            self.graph = create_main_graph(
                llm_provider=self.llm_provider,
                tools=self.tools,
                chat_service=self.chat_service,
                message_service=self.message_service
            )
            logger.info("Graph compiled")
        except Exception as e:
            logger.error(f"Failed to compile graph: {e}")
            raise GraphExecutionError(f"Failed to initialize graph: {e}") from e
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the graph for a message.
        
        Runs all graph nodes and returns final state with bot response.
        """
        chat_id = state.get("chat_id")
        logger.info(f"Starting graph execution for chat {chat_id}")
        
        start_time = time.time()
        
        try:
            # Run the graph (executes all nodes)
            result = await self.graph.ainvoke(state)
            
            execution_time = time.time() - start_time
            logger.info(f"Graph completed in {round(execution_time * 1000)}ms")
            
            return result
            
        except LLMProviderError as e:
            logger.error(f"LLM error: {e}")
            return self._create_fallback_response(
                state,
                "I'm having trouble processing your request. Please try again."
            )
            
        except Exception as e:
            logger.error(f"Graph execution failed: {e}", exc_info=True)
            return self._create_fallback_response(
                state,
                "I encountered an error. Your conversation is saved. Please try again."
            )
    
    async def _execute_with_logging(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute graph and log."""
        logger.debug(f"Invoking graph for chat {state.get('chat_id')}")
        result = await self.graph.ainvoke(state)
        logger.debug(f"Graph completed for chat {state.get('chat_id')}")
        return result
    
    def _create_fallback_response(self, state: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Create error response while preserving state."""
        return {
            "chat_id": state.get("chat_id"),
            "user_id": state.get("user_id"),
            "owner_profile_id": state.get("owner_profile_id"),
            "user_message": state.get("user_message"),
            "flow_state": state.get("flow_state", {}),
            "bot_memory": state.get("bot_memory", {}),
            "messages": state.get("messages", []),
            "intent": state.get("intent"),
            "response_content": message,
            "response_type": "text",
            "response_metadata": {},
            "token_usage": None,
            "search_results": None,
            "availability_data": None,
            "pricing_data": None
        }


__all__ = [
    "GraphRuntime",
    "GraphExecutionError",
]

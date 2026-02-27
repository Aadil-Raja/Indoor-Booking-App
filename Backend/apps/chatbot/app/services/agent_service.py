"""
Agent service for orchestrating LangGraph conversation flow.

This service implements the core business logic for processing user messages
through the LangGraph conversation agent. It:
- Stores incoming user messages
- Prepares conversation state from chat data
- Executes the main graph through GraphRuntime
- Updates chat state with new flow_state and bot_memory
- Stores bot responses with token usage
- Handles errors gracefully with proper logging

The service acts as the orchestration layer between the API endpoints and
the LangGraph agent, managing the complete message processing lifecycle.

Requirements: 6.1-6.8, 11.1-11.5, 12.1-12.3, 13.1-13.3, 15.1-15.5
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from uuid import UUID
import logging

from .chat_service import ChatService
from .message_service import MessageService
from ..agent.runtime.graph_runtime import GraphRuntime, GraphExecutionError
from ..models.chat import Chat

logger = logging.getLogger(__name__)


class AgentService:
    """
    Service for orchestrating LangGraph conversation flow.
    
    This service manages the complete lifecycle of processing a user message:
    1. Store user message in database
    2. Prepare conversation state from chat data
    3. Execute LangGraph through GraphRuntime
    4. Update chat state with results
    5. Store bot response
    6. Return response to caller
    
    All operations are async and use transaction management through the
    provided database session. The service handles errors gracefully and
    ensures conversation state is preserved across failures.
    
    Implements Requirements:
    - 6.1-6.8: LangGraph architecture and state management
    - 11.1-11.5: Async service layer
    - 12.1-12.3: Structured logging
    - 13.1-13.3: Token usage tracking
    - 15.1-15.5: Transaction management
    
    Attributes:
        session: AsyncSession for database operations
        chat_service: ChatService for chat state management
        message_service: MessageService for message operations
        graph_runtime: GraphRuntime for LangGraph execution
    """
    
    def __init__(
        self,
        session: AsyncSession,
        chat_service: ChatService,
        message_service: MessageService,
        graph_runtime: GraphRuntime
    ):
        """
        Initialize AgentService with dependencies.
        
        Args:
            session: AsyncSession for database operations
            chat_service: ChatService instance
            message_service: MessageService instance
            graph_runtime: GraphRuntime instance for graph execution
        """
        self.session = session
        self.chat_service = chat_service
        self.message_service = message_service
        self.graph_runtime = graph_runtime
        
        logger.info("AgentService initialized")
    
    async def process_message(
        self,
        chat: Chat,
        user_message: str
    ) -> Dict[str, Any]:
        """
        Process user message through LangGraph and return bot response.
        
        This is the main entry point for message processing. It orchestrates
        the complete flow:
        
        1. Store user message in database (Requirement 5.1)
        2. Prepare conversation state from chat data (Requirement 6.4-6.5)
        3. Execute main graph via GraphRuntime (Requirement 6.1-6.8)
        4. Update chat state with new flow_state and bot_memory (Requirement 20.1-20.8)
        5. Store bot response with token usage (Requirement 13.1-13.3)
        6. Return response dict to caller
        
        The method uses transaction management to ensure data consistency.
        If any step fails, the transaction is rolled back and an error
        response is returned while preserving conversation state.
        
        Args:
            chat: Chat instance for the conversation session
            user_message: User's message content
            
        Returns:
            Dict containing:
                - content: Bot's response text
                - message_type: Response format (text, button, list, media)
                - metadata: Additional response data (buttons, lists, etc.)
                - message_id: UUID of the stored bot message
                
        Raises:
            Exception: If critical errors occur during processing
            
        Example:
            response = await agent_service.process_message(
                chat=chat,
                user_message="I want to book a tennis court"
            )
            
            print(response["content"])  # Bot's response
            print(response["message_type"])  # "text", "button", "list", etc.
            print(response["message_id"])  # UUID of bot message
        """
        chat_id = chat.id
        user_id = chat.user_id
        owner_id = chat.owner_id
        
        # Log incoming message (Requirement 12.1)
        logger.info(
            f"Processing message for chat {chat_id}",
            extra={
                "chat_id": str(chat_id),
                "user_id": str(user_id),
                "owner_id": str(owner_id),
                "message_preview": user_message[:100],
                "current_intent": chat.flow_state.get("intent"),
                "current_step": chat.flow_state.get("step")
            }
        )
        
        try:
            # Step 1: Store user message (Requirement 5.1)
            user_msg = await self.message_service.create_message(
                chat_id=chat_id,
                sender_type="user",
                content=user_message
            )
            
            logger.debug(
                f"Stored user message {user_msg.id} for chat {chat_id}"
            )
            
            # Step 2: Prepare conversation state (Requirement 6.4-6.5)
            state = self._prepare_conversation_state(
                chat=chat,
                user_message=user_message
            )
            
            logger.debug(
                f"Prepared conversation state for chat {chat_id}",
                extra={
                    "chat_id": str(chat_id),
                    "flow_state": state["flow_state"],
                    "message_history_length": len(state["messages"])
                }
            )
            
            # Step 3: Execute graph (Requirement 6.1-6.8)
            result = await self.graph_runtime.execute(state)
            
            logger.info(
                f"Graph execution completed for chat {chat_id}",
                extra={
                    "chat_id": str(chat_id),
                    "response_type": result.get("response_type"),
                    "token_usage": result.get("token_usage"),
                    "new_intent": result.get("flow_state", {}).get("intent"),
                    "new_step": result.get("flow_state", {}).get("step")
                }
            )
            
            # Step 4: Update chat state (Requirement 20.1-20.8, 15.1-15.5)
            await self.chat_service.update_chat_state(
                chat=chat,
                flow_state=result.get("flow_state"),
                bot_memory=result.get("bot_memory")
            )
            
            logger.debug(
                f"Updated chat state for {chat_id}",
                extra={
                    "chat_id": str(chat_id),
                    "flow_state_updated": result.get("flow_state") is not None,
                    "bot_memory_updated": result.get("bot_memory") is not None
                }
            )
            
            # Step 5: Store bot response (Requirement 13.1-13.3)
            bot_message = await self.message_service.create_message(
                chat_id=chat_id,
                sender_type="bot",
                content=result["response_content"],
                message_type=result.get("response_type", "text"),
                metadata=result.get("response_metadata", {}),
                token_usage=result.get("token_usage")
            )
            
            logger.info(
                f"Stored bot response {bot_message.id} for chat {chat_id}",
                extra={
                    "chat_id": str(chat_id),
                    "message_id": str(bot_message.id),
                    "message_type": bot_message.message_type,
                    "token_usage": bot_message.token_usage
                }
            )
            
            # Step 6: Return response dict
            response = {
                "content": result["response_content"],
                "message_type": result.get("response_type", "text"),
                "metadata": result.get("response_metadata", {}),
                "message_id": bot_message.id
            }
            
            logger.info(
                f"Message processing completed successfully for chat {chat_id}",
                extra={
                    "chat_id": str(chat_id),
                    "message_id": str(bot_message.id),
                    "response_length": len(response["content"])
                }
            )
            
            return response
            
        except GraphExecutionError as e:
            # Graph execution failed - log and return error response
            logger.error(
                f"Graph execution error for chat {chat_id}: {e}",
                extra={
                    "chat_id": str(chat_id),
                    "user_id": str(user_id),
                    "error_type": type(e).__name__,
                    "flow_state": chat.flow_state
                },
                exc_info=True
            )
            
            # Store error message for user
            error_message = (
                "I encountered an error processing your message. "
                "Please try again or rephrase your request."
            )
            
            bot_message = await self.message_service.create_message(
                chat_id=chat_id,
                sender_type="bot",
                content=error_message,
                message_type="text",
                metadata={"error": True}
            )
            
            return {
                "content": error_message,
                "message_type": "text",
                "metadata": {"error": True},
                "message_id": bot_message.id
            }
            
        except Exception as e:
            # Unexpected error - log and return generic error response
            logger.error(
                f"Unexpected error processing message for chat {chat_id}: {e}",
                extra={
                    "chat_id": str(chat_id),
                    "user_id": str(user_id),
                    "owner_id": str(owner_id),
                    "error_type": type(e).__name__,
                    "flow_state": chat.flow_state
                },
                exc_info=True
            )
            
            # Store error message for user
            error_message = (
                "I'm having trouble right now. "
                "Your conversation has been saved. Please try again."
            )
            
            try:
                bot_message = await self.message_service.create_message(
                    chat_id=chat_id,
                    sender_type="bot",
                    content=error_message,
                    message_type="text",
                    metadata={"error": True, "error_type": type(e).__name__}
                )
                
                return {
                    "content": error_message,
                    "message_type": "text",
                    "metadata": {"error": True},
                    "message_id": bot_message.id
                }
            except Exception as store_error:
                # Even storing error message failed - log and re-raise
                logger.critical(
                    f"Failed to store error message for chat {chat_id}: {store_error}",
                    extra={
                        "chat_id": str(chat_id),
                        "original_error": str(e),
                        "store_error": str(store_error)
                    },
                    exc_info=True
                )
                raise
    
    def _prepare_conversation_state(
        self,
        chat: Chat,
        user_message: str
    ) -> Dict[str, Any]:
        """
        Prepare conversation state from chat data for graph execution.
        
        This method transforms the database chat model into the ConversationState
        format expected by the LangGraph nodes. It includes:
        - Chat identifiers (chat_id, user_id, owner_id)
        - Current user message
        - Persistent state (flow_state, bot_memory)
        - Message history for LLM context
        
        Implements Requirement 6.4-6.5: When executing a node, the LangGraph_Agent
        shall read current flow_state and bot_memory.
        
        Args:
            chat: Chat instance with current state
            user_message: User's message content
            
        Returns:
            Dict containing ConversationState fields ready for graph execution
        """
        # Extract message history from bot_memory for LLM context
        bot_memory = chat.bot_memory or {}
        conversation_history = bot_memory.get("conversation_history", [])
        
        # Prepare state dict
        state = {
            # Identifiers
            "chat_id": str(chat.id),
            "user_id": str(chat.user_id),
            "owner_id": str(chat.owner_id),
            
            # Current message
            "user_message": user_message,
            
            # Persistent state
            "flow_state": chat.flow_state or {},
            "bot_memory": bot_memory,
            
            # Message history for LLM context
            "messages": conversation_history,
            
            # Processing state (will be populated by nodes)
            "intent": None,
            
            # Response fields (will be populated by nodes)
            "response_content": "",
            "response_type": "text",
            "response_metadata": {},
            
            # Metrics
            "token_usage": None,
            
            # Tool results (will be populated by nodes)
            "search_results": None,
            "availability_data": None,
            "pricing_data": None
        }
        
        logger.debug(
            f"Prepared conversation state",
            extra={
                "chat_id": str(chat.id),
                "has_flow_state": bool(chat.flow_state),
                "has_bot_memory": bool(bot_memory),
                "message_history_length": len(conversation_history),
                "current_intent": chat.flow_state.get("intent") if chat.flow_state else None,
                "current_step": chat.flow_state.get("step") if chat.flow_state else None
            }
        )
        
        return state


__all__ = ["AgentService"]

"""
Agent service for processing messages through LangGraph.

Orchestrates the complete message flow:
- Save user message
- Run LangGraph (intent detection → handler → response)
- Save bot response
- Update chat state
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from uuid import UUID
import logging

from app.services.chat_service import ChatService
from app.services.message_service import MessageService
from app.agent.runtime.graph_runtime import GraphRuntime, GraphExecutionError
from app.models.chat import Chat

logger = logging.getLogger(__name__)


class AgentService:
    """
    Orchestrates message processing through LangGraph.
    
    Main job: Take user message → Run graph → Return bot response
    """
    
    def __init__(
        self,
        session: AsyncSession,
        chat_service: ChatService,
        message_service: MessageService,
        graph_runtime: GraphRuntime
    ):
        self.session = session
        self.chat_service = chat_service
        self.message_service = message_service
        self.graph_runtime = graph_runtime
    
    async def process_message(self, chat: Chat, user_message: str) -> Dict[str, Any]:
        """
        Process user message and return bot response.
        
        What it does:
        1. Save user message to database
        2. Prepare state (chat history, flow_state, bot_memory)
        3. Run LangGraph (intent detection → handler → response)
        4. Update chat state with results
        5. Save bot response
        6. Return response
        
        Returns:
            {
                "content": "Bot's response text",
                "message_type": "text",
                "metadata": {},
                "message_id": "uuid"
            }
        """
        chat_id = chat.id
        logger.info(f"Processing message for chat {chat_id}")
        
        try:
            # 1. Save user message
            user_msg = await self.message_service.create_message(
                chat_id=chat_id,
                sender_type="user",
                content=user_message
            )
            
            # 2. Prepare state (chat history + flow_state + bot_memory)
            state = self._prepare_conversation_state(chat=chat, user_message=user_message)
            
            # 3. Run graph (intent detection → handler → response)
            result = await self.graph_runtime.execute(state)
            
            # 4. Update chat state
            await self.chat_service.update_chat_state(
                chat=chat,
                flow_state=result.get("flow_state"),
                bot_memory=result.get("bot_memory")
            )
            
            # 5. Save bot response
            bot_message = await self.message_service.create_message(
                chat_id=chat_id,
                sender_type="bot",
                content=result["response_content"],
                message_type=result.get("response_type", "text"),
                metadata=result.get("response_metadata", {}),
                token_usage=result.get("token_usage")
            )
            
            # 6. Return response
            logger.info(f"Message processed successfully for chat {chat_id}")
            
            return {
                "content": result["response_content"],
                "message_type": result.get("response_type", "text"),
                "metadata": result.get("response_metadata", {}),
                "message_id": bot_message.id
            }
            
        except GraphExecutionError as e:
            logger.error(f"Graph error for chat {chat_id}: {e}", exc_info=True)
            
            error_message = "I encountered an error. Please try again."
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
            logger.error(f"Error processing message for chat {chat_id}: {e}", exc_info=True)
            
            error_message = "I'm having trouble right now. Please try again."
            
            try:
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
            except Exception as store_error:
                logger.critical(f"Failed to store error message: {store_error}", exc_info=True)
                raise
    
    def _prepare_conversation_state(self, chat: Chat, user_message: str) -> Dict[str, Any]:
        """
        Prepare state for graph execution.
        
        Ensures all required fields are initialized:
        - Chat IDs (from chat object)
        - Current message
        - flow_state (properly initialized with all fields)
        - bot_memory (properly initialized with all fields)
        - All response fields with defaults
        """
        # Initialize bot_memory with proper structure
        from app.agent.state.memory_manager import _initialize_bot_memory, _ensure_bot_memory_structure
        
        bot_memory = chat.bot_memory or {}
        if not bot_memory or not isinstance(bot_memory, dict):
            bot_memory = _initialize_bot_memory()
            logger.info(f"Initialized bot_memory for chat {chat.id}")
        else:
            # Ensure bot_memory has proper structure
            bot_memory = _ensure_bot_memory_structure(bot_memory)
        
        # Initialize flow_state properly with all fields
        from app.agent.state.flow_state_manager import initialize_flow_state, ensure_flow_state_fields
        
        flow_state = chat.flow_state or {}
        if not flow_state:
            # New chat - initialize fresh
            flow_state = initialize_flow_state()
            logger.info(f"Initialized flow_state for new chat {chat.id}")
        else:
            # Existing chat - ensure all fields exist without losing data
            flow_state = ensure_flow_state_fields(flow_state)
            logger.debug(f"Ensured flow_state fields for chat {chat.id}")
        
        return {
            # IDs (always present from chat object)
            "chat_id": str(chat.id),
            "user_id": str(chat.user_id),
            "owner_profile_id": str(chat.owner_profile_id),
            
            # Current message
            "user_message": user_message,
            
            # State from database (with defaults)
            "flow_state": flow_state,
            "bot_memory": bot_memory,
            "messages": [],  # Will be loaded by load_chat node
            
            # Response fields (will be filled by nodes)
            "intent": None,
            "response_content": "",
            "response_type": "text",
            "response_metadata": {},
            "token_usage": None,
            
            # Tool results (will be filled by nodes)
            "search_results": None,
            "availability_data": None,
            "pricing_data": None
        }


__all__ = ["AgentService"]

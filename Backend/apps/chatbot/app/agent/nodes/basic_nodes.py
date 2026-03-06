"""
Basic flow nodes for LangGraph conversation management.

This module implements the foundational nodes that handle the basic conversation
flow in the LangGraph agent:

1. receive_message: Entry point that receives and validates the user's message
2. load_chat: Loads chat history and context from the database
3. append_user_message: Adds the user's message to the conversation history in bot_memory

These nodes work with the ConversationState TypedDict and integrate with
ChatService and MessageService for database operations. They manage the
message history in the bot_memory field for LLM context.

Requirements: 6.1, 6.4-6.5, 20.1-20.8
"""

from typing import Dict, Any
import logging
from datetime import datetime

from app.agent.state.conversation_state import ConversationState
from app.services.chat_service import ChatService
from app.services.message_service import MessageService
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_repository import MessageRepository

logger = logging.getLogger(__name__)


async def receive_message(
    state: ConversationState,
    chat_service: ChatService = None,
    message_service: MessageService = None
) -> ConversationState:
    """
    Entry point node that receives and validates the user's message.
    
    This node is the first in the LangGraph flow. It performs initial
    validation and logging of the incoming message. The node ensures
    all required fields are present in the state and logs the message
    for observability.
    
    Implements Requirements:
    - 6.1: LangGraph high-level graph with Receive_Message node
    - 12.1: Log all incoming messages with chat_id, user_id, and owner_id
    
    Args:
        state: ConversationState containing the user message and identifiers
        chat_service: Optional ChatService for dependency injection (unused in this node)
        message_service: Optional MessageService for dependency injection (unused in this node)
        
    Returns:
        ConversationState: Unchanged state after validation and logging
        
    Example:
        state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "223e4567-e89b-12d3-a456-426614174000",
            "owner_profile_id": "323e4567-e89b-12d3-a456-426614174000",
            "user_message": "I want to book a tennis court",
            "flow_state": {},
            "bot_memory": {},
            "messages": [],
            ...
        }
        
        result = await receive_message(state)
    """
    # Validate required fields
    required_fields = ["chat_id", "user_id", "owner_profile_id", "user_message"]
    missing_fields = [field for field in required_fields if not state.get(field)]
    
    if missing_fields:
        logger.error(
            f"Missing required fields in state: {missing_fields}"
        )
        raise ValueError(
            f"ConversationState missing required fields: {missing_fields}"
        )
    
    # Log incoming message for observability (Requirement 12.1)
    logger.info(
        f"Received message - chat_id={state['chat_id']}, "
        f"user_id={state['user_id']}, owner_profile_id={state['owner_profile_id']}, "
        f"message_preview={state['user_message'][:50]}..."
    )
    
    # Validate message is not empty
    if not state["user_message"].strip():
        logger.warning(
            f"Empty message received for chat {state['chat_id']}"
        )
        # Allow empty messages to pass through - they may be handled by downstream nodes
    
    return state


async def load_chat(
    state: ConversationState,
    chat_service: ChatService = None,
    message_service: MessageService = None
) -> ConversationState:
    """
    Load chat history and context from the database.
    
    This node retrieves the chat's message history and prepares it for
    LLM context. It loads recent messages and formats them into the
    messages list for the agent to use. The node also ensures flow_state
    and bot_memory are properly initialized.
    
    Implements Requirements:
    - 6.1: LangGraph high-level graph with Load_Chat node
    - 6.4: Read current flow_state and bot_memory when executing a node
    - 4.8: Load flow_state and bot_memory when continuing a session
    - 20.1-20.8: Flow state management
    
    Args:
        state: ConversationState with chat_id and existing flow_state/bot_memory
        chat_service: Optional ChatService for dependency injection (unused in this node)
        message_service: MessageService for retrieving chat history
        
    Returns:
        ConversationState: State with populated messages list for LLM context
        
    Note:
        The flow_state and bot_memory are already loaded into the state by
        the caller (AgentService) from the Chat model. This node focuses on
        loading the message history for LLM context.
        
    Example:
        state = {
            "chat_id": "123e4567-e89b-12d3-a456-426614174000",
            "flow_state": {"intent": "booking", "step": "select_property"},
            "bot_memory": {"conversation_history": [...]},
            "messages": [],
            ...
        }
        
        result = await load_chat(state, message_service=msg_service)
        # result["messages"] now contains formatted message history
    """
    chat_id = state["chat_id"]
    
    logger.info(f"Loading chat history for chat {chat_id}")
    
    # Initialize messages list if not present
    if "messages" not in state:
        state["messages"] = []
    
    # Ensure flow_state and bot_memory are initialized
    if "flow_state" not in state or state["flow_state"] is None:
        state["flow_state"] = {}
        logger.debug(f"Initialized empty flow_state for chat {chat_id}")
    
    if "bot_memory" not in state or state["bot_memory"] is None:
        state["bot_memory"] = {}
        logger.debug(f"Initialized empty bot_memory for chat {chat_id}")
    
    # Load message history if message_service is provided
    if message_service:
        try:
            # Retrieve recent message history (last 20 messages for context)
            # This provides enough context without overwhelming the LLM
            from uuid import UUID
            chat_uuid = UUID(chat_id)
            
            messages = await message_service.get_chat_history(
                chat_id=chat_uuid,
                limit=20
            )
            
            # Format messages for LLM context
            # Convert Message objects to dict format with role and content
            formatted_messages = []
            for msg in messages:
                # Map sender_type to LLM role format
                role = "user" if msg.sender_type == "user" else "assistant"
                if msg.sender_type == "system":
                    role = "system"
                
                formatted_messages.append({
                    "role": role,
                    "content": msg.content
                })
            
            state["messages"] = formatted_messages
            
            logger.info(
                f"Loaded {len(formatted_messages)} messages for chat {chat_id}"
            )
            
        except Exception as e:
            logger.error(
                f"Error loading chat history for {chat_id}: {e}",
                exc_info=True
            )
            # Continue with empty messages list - don't fail the flow
            state["messages"] = []
    else:
        logger.warning(
            f"MessageService not provided to load_chat node, "
            f"skipping message history load"
        )
    
    # Log current flow state for debugging
    flow_state = state.get("flow_state", {})
    current_step = flow_state.get("step", "none")
    current_intent = flow_state.get("intent", "none")
    
    logger.debug(
        f"Chat {chat_id} state loaded - "
        f"step={current_step}, intent={current_intent}, "
        f"messages_count={len(state['messages'])}"
    )
    
    return state


async def append_user_message(
    state: ConversationState,
    chat_service: ChatService = None,
    message_service: MessageService = None
) -> ConversationState:
    """
    Add the user's message to the conversation history in bot_memory.
    
    This node appends the current user message to the conversation_history
    stored in bot_memory. This maintains a persistent record of the conversation
    that can be used for context across sessions and for conversation analysis.
    
    The node also adds the message to the ephemeral messages list for
    immediate LLM context during this processing cycle.
    
    Implements Requirements:
    - 6.1: LangGraph high-level graph with Append_User_Message node
    - 6.5: Update bot_memory as needed when a node completes
    - 20.1-20.8: Flow state management and bot_memory updates
    
    Args:
        state: ConversationState with user_message and bot_memory
        chat_service: Optional ChatService for dependency injection (unused in this node)
        message_service: Optional MessageService for dependency injection (unused in this node)
        
    Returns:
        ConversationState: State with updated bot_memory containing the new message
        
    Example:
        state = {
            "user_message": "I want to book a tennis court",
            "bot_memory": {
                "conversation_history": [
                    {"role": "user", "content": "Hello", "timestamp": "..."},
                    {"role": "assistant", "content": "Hi! How can I help?", "timestamp": "..."}
                ]
            },
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I help?"}
            ],
            ...
        }
        
        result = await append_user_message(state)
        # result["bot_memory"]["conversation_history"] now includes the new message
        # result["messages"] also includes the new message for immediate context
    """
    user_message = state["user_message"]
    bot_memory = state.get("bot_memory", {})
    
    logger.debug(
        f"Appending user message to bot_memory for chat {state['chat_id']}"
    )
    
    # Initialize conversation_history in bot_memory if not present
    if "conversation_history" not in bot_memory:
        bot_memory["conversation_history"] = []
        logger.debug("Initialized conversation_history in bot_memory")
    
    # Create message entry with timestamp
    message_entry = {
        "role": "user",
        "content": user_message,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Append to conversation history in bot_memory
    bot_memory["conversation_history"].append(message_entry)
    
    # Update bot_memory in state
    state["bot_memory"] = bot_memory
    
    # Also append to ephemeral messages list for immediate LLM context
    if "messages" not in state:
        state["messages"] = []
    
    state["messages"].append({
        "role": "user",
        "content": user_message
    })
    
    logger.info(
        f"Appended user message to bot_memory for chat {state['chat_id']} - "
        f"conversation_history_length={len(bot_memory['conversation_history'])}, "
        f"messages_length={len(state['messages'])}"
    )
    
    return state

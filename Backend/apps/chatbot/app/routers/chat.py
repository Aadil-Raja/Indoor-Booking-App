"""
Chat API router for message handling and chat management.

Endpoints:
- POST /api/chat/message - Process user messages
- GET /api/chat/history/{chat_id} - Get conversation history
- POST /api/chat/new - Create new chat session
- GET /api/chat/list - List user's chats
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from app.deps.db import get_async_db
from app.repositories.chat_repository import ChatRepository
from app.repositories.message_repository import MessageRepository
from app.services.chat_service import ChatService
from app.services.message_service import MessageService
from app.services.agent_service import AgentService
from app.agent.runtime.graph_runtime import GraphRuntime
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse, ChatHistoryResponse, ChatCreate, ChatResponse, ChatListResponse, ChatSummary
from app.core.config import settings
from app.services.llm import get_llm_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# Dependency to get ChatService
# Dependencies
async def get_chat_service(db: AsyncSession = Depends(get_async_db)) -> ChatService:
    """Get ChatService instance."""
    chat_repo = ChatRepository(db)
    message_repo = MessageRepository(db)
    return ChatService(db, chat_repo, message_repo)


async def get_message_service(db: AsyncSession = Depends(get_async_db)) -> MessageService:
    """Get MessageService instance."""
    message_repo = MessageRepository(db)
    return MessageService(db, message_repo)


async def get_agent_service(
    db: AsyncSession = Depends(get_async_db),
    chat_service: ChatService = Depends(get_chat_service),
    message_service: MessageService = Depends(get_message_service)
) -> AgentService:
    """Get AgentService instance with LLM and graph runtime."""
    llm_provider = get_llm_provider()
    graph_runtime = GraphRuntime(
        llm_provider=llm_provider,
        chat_service=chat_service,
        message_service=message_service
    )
    return AgentService(db, chat_service, message_service, graph_runtime)


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    chat_service: ChatService = Depends(get_chat_service),
    agent_service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Process user message and return bot response.
    
    Flow: Get/create session → Process message → Return response
    """
    logger.info(f"Message from user={request.user_id}, owner={request.owner_profile_id}")
    
    try:
        # Get or create chat session
        chat, is_new = await chat_service.determine_session(
            user_id=request.user_id,
            owner_profile_id=request.owner_profile_id
        )
        
        logger.info(f"Using chat_id={chat.id}, is_new={is_new}")
        
        # Process message through agent
        response = await agent_service.process_message(
            chat=chat,
            user_message=request.content
        )
        
        await db.commit()
        
        logger.info(f"Message processed successfully, chat_id={chat.id}")
        
        # Return response
        return ChatMessageResponse(
            chat_id=chat.id,
            message_id=response["message_id"],
            content=response["content"],
            message_type=response["message_type"],
            message_metadata=response["metadata"]
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing your message. Please try again."
        )


@router.get("/history/{chat_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    chat_id: UUID,
    message_service: MessageService = Depends(get_message_service),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get all messages in a chat session.
    
    Returns messages in chronological order.
    """
    logger.info(f"Getting history for chat={chat_id}")
    
    try:
        # Get chat
        chat_repo = ChatRepository(db)
        chat = await chat_repo.get_by_id(chat_id)
        
        if not chat:
            logger.warning(f"Chat not found: {chat_id}")
            raise HTTPException(status_code=404, detail="Chat not found")
        
        # Get messages
        messages = await message_service.get_chat_history(chat_id)
        logger.info(f"Retrieved {len(messages)} messages")
        
        return ChatHistoryResponse(chat_id=chat_id, messages=messages)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving chat history")


@router.post("/new", response_model=ChatResponse)
async def create_new_chat(
    request: ChatCreate,
    chat_service: ChatService = Depends(get_chat_service),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Create a new chat session explicitly.
    
    Use this endpoint when user wants to start a fresh conversation.
    
    Args:
        request: ChatCreate with user_id and owner_profile_id
        
    Returns:
        ChatResponse with new chat_id and initial state
    """
    logger.info(f"Creating new chat for user={request.user_id}, owner_profile={request.owner_profile_id}")
    
    try:
        chat = await chat_service.create_chat(
            user_id=request.user_id,
            owner_profile_id=request.owner_profile_id
        )
        
        await db.commit()
        
        logger.info(f"New chat created: {chat.id}")
        
        return ChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            owner_profile_id=chat.owner_profile_id,
            status=chat.status,
            last_message_at=chat.last_message_at,
            flow_state=chat.flow_state,
            created_at=chat.created_at,
            updated_at=chat.updated_at
        )
        
    except Exception as e:
        logger.error(f"Error creating new chat: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating new chat. Please try again."
        )



@router.get("/list", response_model=ChatListResponse)
async def list_user_chats(
    user_id: UUID,
    message_service: MessageService = Depends(get_message_service),
    db: AsyncSession = Depends(get_async_db)
):
    """
    List all chats for a user.
    
    Returns chats ordered by most recent activity with message preview.
    """
    logger.info(f"Listing chats for user={user_id}")
    
    try:
        # Get all chats
        chat_repo = ChatRepository(db)
        chats = await chat_repo.get_user_chats(user_id)
        logger.info(f"Found {len(chats)} chats")
        
        # Build summaries with last message preview
        chat_summaries = []
        message_repo = MessageRepository(db)
        
        for chat in chats:
            last_message = await message_repo.get_last_message(chat.id)
            
            # Truncate preview to 100 chars
            preview = None
            sender = None
            if last_message:
                preview = (
                    last_message.content[:100] + "..."
                    if len(last_message.content) > 100
                    else last_message.content
                )
                sender = last_message.sender_type
            
            chat_summaries.append(ChatSummary(
                chat_id=chat.id,
                owner_profile_id=chat.owner_profile_id,
                status=chat.status,
                last_message_at=chat.last_message_at,
                last_message_preview=preview,
                last_message_sender=sender
            ))
        
        return ChatListResponse(chats=chat_summaries)
        
    except Exception as e:
        logger.error(f"Error listing chats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error listing chats")

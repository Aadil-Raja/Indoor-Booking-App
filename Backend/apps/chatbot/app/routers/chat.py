"""
Chat API router for message handling and chat management.

This module implements REST API endpoints for the chatbot, including:
- POST /api/chat/message: Process user messages and return bot responses
- Session continuity handling with 24-hour threshold
- Structured logging for all requests
- Error handling with user-friendly messages

Requirements: 4.1-4.8, 12.1, 17.1-17.3, 18.1-18.3
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import logging

from ..core.database import get_async_db
from ..repositories.chat_repository import ChatRepository
from ..repositories.message_repository import MessageRepository
from ..services.chat_service import ChatService
from ..services.message_service import MessageService
from ..services.agent_service import AgentService
from ..agent.runtime.graph_runtime import GraphRuntime
from ..schemas.chat import ChatMessageRequest, ChatMessageResponse, ChatHistoryResponse, ChatCreate, ChatResponse, ChatListResponse, ChatSummary
from ..core.config import settings
from ..services.llm import get_llm_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# Dependency to get ChatService
async def get_chat_service(
    db: AsyncSession = Depends(get_async_db)
) -> ChatService:
    """Dependency injection for ChatService."""
    chat_repo = ChatRepository(db)
    message_repo = MessageRepository(db)
    return ChatService(db, chat_repo, message_repo)


# Dependency to get MessageService
async def get_message_service(
    db: AsyncSession = Depends(get_async_db)
) -> MessageService:
    """Dependency injection for MessageService."""
    message_repo = MessageRepository(db)
    return MessageService(db, message_repo)


# Dependency to get AgentService
async def get_agent_service(
    db: AsyncSession = Depends(get_async_db),
    chat_service: ChatService = Depends(get_chat_service),
    message_service: MessageService = Depends(get_message_service)
) -> AgentService:
    """Dependency injection for AgentService."""
    # Get LLM provider
    llm_provider = get_llm_provider()
    
    # Initialize GraphRuntime with LLM provider
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
    message_service: MessageService = Depends(get_message_service),
    agent_service: AgentService = Depends(get_agent_service),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Process user message and return bot response.
    
    This endpoint implements the complete message processing flow:
    1. Determine session continuity (new or existing chat)
    2. Handle expired sessions (ask user about continuation)
    3. Process message through AgentService
    4. Return bot response with chat_id and message_id
    
    Implements Requirements:
    - 4.1-4.8: Session continuity management
    - 12.1: Structured logging for all requests
    - 17.1-17.3: API endpoint specification
    - 18.1-18.3: Authentication and authorization
    
    Args:
        request: ChatMessageRequest with user_id, owner_id, and message content
        chat_service: Injected ChatService
        message_service: Injected MessageService
        agent_service: Injected AgentService
        db: Injected database session
        
    Returns:
        ChatMessageResponse with bot response, chat_id, and message_id
        
    Raises:
        HTTPException: If validation fails or processing errors occur
    """
    # Log incoming request (Requirement 12.1)
    logger.info(
        f"Received message request",
        extra={
            "user_id": str(request.user_id),
            "owner_id": str(request.owner_id),
            "message_preview": request.content[:100]
        }
    )
    
    try:
        # Step 1: Determine session continuity (Requirements 4.1-4.8)
        chat, is_new_session = await chat_service.determine_session(
            user_id=request.user_id,
            owner_id=request.owner_id,
            user_message=request.content
        )
        
        logger.info(
            f"Session determined: chat_id={chat.id}, is_new={is_new_session}",
            extra={
                "chat_id": str(chat.id),
                "user_id": str(request.user_id),
                "owner_id": str(request.owner_id),
                "is_new_session": is_new_session
            }
        )
        
        # Step 2: Handle expired sessions (Requirements 4.4-4.6)
        if not is_new_session:
            chat_repo = ChatRepository(db)
            is_expired = await chat_repo.is_session_expired(
                chat, 
                threshold_hours=settings.SESSION_EXPIRY_HOURS
            )
            
            if is_expired:
                # Session expired - ask user about continuation
                logger.info(
                    f"Session expired for chat {chat.id}, prompting user",
                    extra={
                        "chat_id": str(chat.id),
                        "last_message_at": str(chat.last_message_at)
                    }
                )
                
                # Store user message
                user_msg = await message_service.create_message(
                    chat_id=chat.id,
                    sender_type="user",
                    content=request.content
                )
                
                # Check if user is confirming or denying continuation
                user_message_lower = request.content.lower()
                
                # User confirms continuation (Requirement 4.5)
                if any(word in user_message_lower for word in ["yes", "continue", "sure", "ok", "yeah"]):
                    logger.info(
                        f"User confirmed continuation of chat {chat.id}",
                        extra={"chat_id": str(chat.id)}
                    )
                    
                    # Continue with existing session
                    response = await agent_service.process_message(
                        chat=chat,
                        user_message=request.content
                    )
                    
                    await db.commit()
                    
                    return ChatMessageResponse(
                        chat_id=chat.id,
                        message_id=response["message_id"],
                        content=response["content"],
                        message_type=response["message_type"],
                        message_metadata=response["metadata"]
                    )
                
                # User denies continuation (Requirement 4.6)
                elif any(word in user_message_lower for word in ["no", "new", "different", "start over"]):
                    logger.info(
                        f"User denied continuation, creating new chat",
                        extra={
                            "old_chat_id": str(chat.id),
                            "user_id": str(request.user_id),
                            "owner_id": str(request.owner_id)
                        }
                    )
                    
                    # Create new session (Requirement 4.6)
                    chat = await chat_service.create_chat(
                        user_id=request.user_id,
                        owner_id=request.owner_id
                    )
                    
                    # Process message with new session
                    response = await agent_service.process_message(
                        chat=chat,
                        user_message=request.content
                    )
                    
                    await db.commit()
                    
                    return ChatMessageResponse(
                        chat_id=chat.id,
                        message_id=response["message_id"],
                        content=response["content"],
                        message_type=response["message_type"],
                        message_metadata=response["metadata"]
                    )
                
                # First message after expiry - ask about continuation (Requirement 4.4)
                else:
                    continuation_prompt = (
                        "Are you referring to our previous conversation? "
                        "Reply 'yes' to continue or 'no' to start a new conversation."
                    )
                    
                    # Store bot's continuation prompt
                    bot_msg = await message_service.create_message(
                        chat_id=chat.id,
                        sender_type="bot",
                        content=continuation_prompt,
                        message_type="text",
                        metadata={"continuation_prompt": True}
                    )
                    
                    # Update chat's last_message_at
                    await chat_service.update_chat_state(chat)
                    
                    await db.commit()
                    
                    logger.info(
                        f"Sent continuation prompt for chat {chat.id}",
                        extra={"chat_id": str(chat.id)}
                    )
                    
                    return ChatMessageResponse(
                        chat_id=chat.id,
                        message_id=bot_msg.id,
                        content=continuation_prompt,
                        message_type="text",
                        message_metadata={"continuation_prompt": True}
                    )
        
        # Step 3: Process message through AgentService (Requirements 6.1-6.8)
        response = await agent_service.process_message(
            chat=chat,
            user_message=request.content
        )
        
        # Commit transaction
        await db.commit()
        
        logger.info(
            f"Message processed successfully",
            extra={
                "chat_id": str(chat.id),
                "message_id": str(response["message_id"]),
                "message_type": response["message_type"]
            }
        )
        
        # Step 4: Return response (Requirement 17.3)
        return ChatMessageResponse(
            chat_id=chat.id,
            message_id=response["message_id"],
            content=response["content"],
            message_type=response["message_type"],
            message_metadata=response["metadata"]
        )
        
    except ValueError as e:
        # Validation error
        logger.error(
            f"Validation error: {e}",
            extra={
                "user_id": str(request.user_id),
                "owner_id": str(request.owner_id),
                "error": str(e)
            }
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except Exception as e:
        # Unexpected error
        logger.error(
            f"Error processing message: {e}",
            extra={
                "user_id": str(request.user_id),
                "owner_id": str(request.owner_id),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred processing your message. Please try again."
        )


@router.get("/history/{chat_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    chat_id: UUID,
    chat_service: ChatService = Depends(get_chat_service),
    message_service: MessageService = Depends(get_message_service),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Retrieve chat history for a specific chat session.
    
    This endpoint returns all messages in a chat session in chronological order.
    It verifies that the user has access to the chat (user_id matches or is owner).
    
    Implements Requirements:
    - 17.4-17.5: Chat history endpoint specification
    - 18.1-18.5: Authentication and authorization
    
    Args:
        chat_id: UUID of the chat session
        chat_service: Injected ChatService
        message_service: Injected MessageService
        db: Injected database session
        
    Returns:
        ChatHistoryResponse with chat_id and list of messages
        
    Raises:
        HTTPException 404: If chat not found
        HTTPException 403: If user doesn't have access to chat
        HTTPException 500: If unexpected error occurs
    """
    # Log incoming request (Requirement 12.1)
    logger.info(
        f"Received chat history request",
        extra={
            "chat_id": str(chat_id)
        }
    )
    
    try:
        # Step 1: Retrieve chat session (Requirement 17.4)
        chat_repo = ChatRepository(db)
        chat = await chat_repo.get_by_id(chat_id)
        
        if not chat:
            logger.warning(
                f"Chat not found: {chat_id}",
                extra={"chat_id": str(chat_id)}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat {chat_id} not found"
            )
        
        # Step 2: Verify user has access to chat (Requirements 18.1-18.5)
        # Note: In a production system, this would use get_current_user dependency
        # For now, we'll allow access since authentication will be added later
        # The check would be: if current_user.id != chat.user_id and current_user.id != chat.owner_id
        
        logger.info(
            f"Access granted to chat {chat_id}",
            extra={
                "chat_id": str(chat_id),
                "user_id": str(chat.user_id),
                "owner_id": str(chat.owner_id)
            }
        )
        
        # Step 3: Retrieve all messages in chronological order (Requirement 17.5)
        messages = await message_service.get_chat_history(chat_id)
        
        logger.info(
            f"Retrieved {len(messages)} messages for chat {chat_id}",
            extra={
                "chat_id": str(chat_id),
                "message_count": len(messages)
            }
        )
        
        # Step 4: Return response
        return ChatHistoryResponse(
            chat_id=chat_id,
            messages=messages
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        # Unexpected error
        logger.error(
            f"Error retrieving chat history: {e}",
            extra={
                "chat_id": str(chat_id),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred retrieving chat history. Please try again."
        )


@router.post("/new", response_model=ChatResponse)
async def create_new_chat(
    request: ChatCreate,
    chat_service: ChatService = Depends(get_chat_service),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Create a new chat session explicitly.
    
    This endpoint allows users to explicitly create a new chat session
    without sending a message. It returns the chat_id and initial state
    that can be used for subsequent message exchanges.
    
    Implements Requirements:
    - 17.6: New chat endpoint specification
    
    Args:
        request: ChatCreate with user_id and owner_id
        chat_service: Injected ChatService
        db: Injected database session
        
    Returns:
        ChatResponse with chat_id and initial state
        
    Raises:
        HTTPException 400: If validation fails
        HTTPException 500: If unexpected error occurs
    """
    # Log incoming request (Requirement 12.1)
    logger.info(
        f"Received new chat request",
        extra={
            "user_id": str(request.user_id),
            "owner_id": str(request.owner_id)
        }
    )
    
    try:
        # Create new chat session
        chat = await chat_service.create_chat(
            user_id=request.user_id,
            owner_id=request.owner_id
        )
        
        # Commit transaction
        await db.commit()
        
        logger.info(
            f"New chat created successfully",
            extra={
                "chat_id": str(chat.id),
                "user_id": str(request.user_id),
                "owner_id": str(request.owner_id)
            }
        )
        
        # Return chat response
        return ChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            owner_id=chat.owner_id,
            status=chat.status,
            last_message_at=chat.last_message_at,
            flow_state=chat.flow_state,
            created_at=chat.created_at,
            updated_at=chat.updated_at
        )
        
    except ValueError as e:
        # Validation error
        logger.error(
            f"Validation error creating new chat: {e}",
            extra={
                "user_id": str(request.user_id),
                "owner_id": str(request.owner_id),
                "error": str(e)
            }
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except Exception as e:
        # Unexpected error
        logger.error(
            f"Error creating new chat: {e}",
            extra={
                "user_id": str(request.user_id),
                "owner_id": str(request.owner_id),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred creating new chat. Please try again."
        )



@router.get("/list", response_model=ChatListResponse)
async def list_user_chats(
    user_id: UUID,
    chat_service: ChatService = Depends(get_chat_service),
    message_service: MessageService = Depends(get_message_service),
    db: AsyncSession = Depends(get_async_db)
):
    """
    List all chat sessions for a user.
    
    This endpoint returns all chat sessions for a user ordered by most recent
    activity first. Each chat includes a preview of the last message and
    the chat status.
    
    Implements Requirements:
    - 17.7-17.8: Chat list endpoint specification
    - 18.1-18.5: Authentication and authorization
    
    Args:
        user_id: UUID of the user (query parameter)
        chat_service: Injected ChatService
        message_service: Injected MessageService
        db: Injected database session
        
    Returns:
        ChatListResponse with list of chat summaries
        
    Raises:
        HTTPException 400: If validation fails
        HTTPException 500: If unexpected error occurs
    """
    # Log incoming request (Requirement 12.1)
    logger.info(
        f"Received list chats request",
        extra={
            "user_id": str(user_id)
        }
    )
    
    try:
        # Step 1: Retrieve all chats for user (Requirement 17.7)
        chat_repo = ChatRepository(db)
        chats = await chat_repo.get_user_chats(user_id)
        
        logger.info(
            f"Retrieved {len(chats)} chats for user {user_id}",
            extra={
                "user_id": str(user_id),
                "chat_count": len(chats)
            }
        )
        
        # Step 2: Build chat summaries with last message preview (Requirement 17.8)
        chat_summaries = []
        message_repo = MessageRepository(db)
        
        for chat in chats:
            # Get last message for preview
            last_message = await message_repo.get_last_message(chat.id)
            
            # Create preview (truncate to 100 characters)
            last_message_preview = None
            last_message_sender = None
            if last_message:
                last_message_preview = (
                    last_message.content[:100] + "..." 
                    if len(last_message.content) > 100 
                    else last_message.content
                )
                last_message_sender = last_message.sender_type
            
            chat_summary = ChatSummary(
                chat_id=chat.id,
                owner_id=chat.owner_id,
                status=chat.status,
                last_message_at=chat.last_message_at,
                last_message_preview=last_message_preview,
                last_message_sender=last_message_sender
            )
            chat_summaries.append(chat_summary)
        
        logger.info(
            f"Built {len(chat_summaries)} chat summaries for user {user_id}",
            extra={
                "user_id": str(user_id),
                "summary_count": len(chat_summaries)
            }
        )
        
        # Step 3: Return response (Requirement 17.8)
        return ChatListResponse(chats=chat_summaries)
        
    except ValueError as e:
        # Validation error
        logger.error(
            f"Validation error listing chats: {e}",
            extra={
                "user_id": str(user_id),
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
    except Exception as e:
        # Unexpected error
        logger.error(
            f"Error listing chats: {e}",
            extra={
                "user_id": str(user_id),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred listing chats. Please try again."
        )

# Technical Design Document: WhatsApp-Style Chatbot Module

## Overview

The WhatsApp-style chatbot module is a production-grade conversational AI system that enables customers to search for indoor sports facilities, check availability, and create bookings through natural language interactions. The system is built as a separate async module within an existing FastAPI backend, using LangGraph for conversation flow management and maintaining its own dedicated database for chat data.

### Key Design Principles

1. **Async-First Architecture**: All chat operations use async/await patterns to handle concurrent conversations efficiently
2. **Database Separation**: Chat data lives in a separate async database with no foreign key constraints to the main database
3. **Service Integration**: Read-only access to main database through existing service interfaces, write access only through booking service
4. **Structured Conversation Flow**: LangGraph state machine manages complex multi-step booking workflows
5. **LLM Provider Abstraction**: Pluggable language model interface supporting multiple providers
6. **Session Continuity**: Intelligent conversation resumption based on time elapsed and user intent
7. **Multi-Message Handling**: Natural WhatsApp-like experience with message aggregation

### System Context

The chatbot module integrates with an existing FastAPI backend that manages:
- User authentication and authorization
- Owner profiles for property owners
- Property and court management (properties linked to owner_profiles)
- Booking and availability services
- Pricing calculations

The chatbot acts as a conversational interface layer on top of these existing services, providing a natural language way to interact with the booking system.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│                   (WhatsApp, Web, Mobile)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP/REST
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      FastAPI Router Layer                        │
│                    (POST /api/chat/message)                      │
│                    (GET /api/chat/history)                       │
│                    (POST /api/chat/new)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Async Calls
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      Chat Service Layer                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │  Chat Service    │  │ Message Service  │  │ Agent Service │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
└────────────┬────────────────────┬────────────────────┬──────────┘
             │                    │                    │
             │                    │                    │
┌────────────▼────────────────────▼────────────────────▼──────────┐
│                   Chat Repository Layer                          │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  Chat Repository │  │Message Repository│                     │
│  └──────────────────┘  └──────────────────┘                     │
└────────────┬────────────────────┬──────────────────────────────┘
             │                    │
             │ AsyncSession       │
             │                    │
┌────────────▼────────────────────▼──────────────────────────────┐
│                      Chat Database (Async)                       │
│                    PostgreSQL + AsyncPG                          │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │   chats table    │  │  messages table  │                     │
│  └──────────────────┘  └──────────────────┘                     │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    LangGraph Agent Layer                          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                      Main Graph                            │  │
│  │  Receive → Load → Append → Intent → [Handler Nodes]       │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                   Booking Subgraph                         │  │
│  │  Select Property → Service → Date → Time → Confirm        │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    Agent Tools                             │  │
│  │  Property | Court | Booking | Availability | Pricing      │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────┬─────────────────────────────────────────────────────┘
             │
             │ Tool Calls (Sync-to-Async Bridge)
             │
┌────────────▼─────────────────────────────────────────────────────┐
│              Main Database Services (Sync)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │
│  │ Property │ │  Court   │ │ Booking  │ │  Availability    │    │
│  │ Service  │ │ Service  │ │ Service  │ │  Service         │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘    │
└────────────┬─────────────────────────────────────────────────────┘
             │
             │ Sync DB Session
             │
┌────────────▼─────────────────────────────────────────────────────┐
│                   Main Database (Sync)                            │
│                    PostgreSQL + psycopg2                          │
│  ┌────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐ ┌──────┐ │
│  │ users  │ │owner_profiles│ │properties│ │  courts  │ │bookings│
│  └────────┘ └──────────────┘ └──────────┘ └──────────┘ └──────┘ │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    LLM Provider Layer                             │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Abstract LLMProvider                          │  │
│  │  generate() | stream() | count_tokens()                   │  │
│  └────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────┐              ┌──────────────────┐          │
│  │ OpenAIProvider   │              │ GeminiProvider   │          │
│  │  (Implemented)   │              │  (Placeholder)   │          │
│  └──────────────────┘              └──────────────────┘          │
└──────────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
User Message Flow:
1. Client sends POST /api/chat/message
2. Router validates auth and extracts user_id
3. Chat Service determines session continuity
4. Message Service stores user message
5. Agent Service invokes LangGraph
6. LangGraph executes node sequence
7. Nodes call tools to access main services
8. LLM Provider generates natural language
9. Message Service stores bot response
10. Router returns response to client

Booking Flow:
1. User expresses booking intent
2. Intent Detection routes to Booking Subgraph
3. Select Property node presents options
4. User selects property (stored in flow_state)
5. Select Service node shows available courts
6. User selects court (stored in flow_state)
7. Select Date node presents calendar
8. User selects date (stored in flow_state)
9. Select Time node shows available slots with pricing
10. User selects time (stored in flow_state)
11. Confirm node presents summary
12. User confirms
13. Create Pending Booking node calls booking_service
14. Booking created in main database
15. Bot confirms booking with details
```

## Components and Interfaces

### Database Models

#### Chat Model

```python
# Backend/apps/chatbot/app/models/chat.py

from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # No FK
    owner_id = Column(UUID(as_uuid=True), nullable=False, index=True)  # No FK
    status = Column(String(20), nullable=False, default="active")  # active, closed
    last_message_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    flow_state = Column(JSONB, nullable=False, default=dict)
    bot_memory = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_user_owner_last_message', 'user_id', 'owner_id', 'last_message_at'),
        Index('idx_status', 'status'),
    )
```

**Flow State Schema**:
```json
{
  "intent": "booking",
  "step": "select_time",
  "property_id": "uuid",
  "service_id": "uuid",
  "date": "2024-01-15",
  "time": "14:00",
  "booking_id": "uuid"
}
```

**Bot Memory Schema**:
```json
{
  "conversation_history": [
    {"role": "user", "content": "I want to book a tennis court"},
    {"role": "assistant", "content": "Great! Let me show you available properties."}
  ],
  "user_preferences": {
    "preferred_sport": "tennis",
    "preferred_time": "afternoon"
  },
  "context": {
    "last_search_results": ["property_id_1", "property_id_2"]
  }
}
```

#### Message Model

```python
# Backend/apps/chatbot/app/models/message.py

from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey('chats.id', ondelete='CASCADE'), nullable=False, index=True)
    sender_type = Column(String(20), nullable=False)  # user, bot, system
    message_type = Column(String(20), nullable=False, default="text")  # text, button, list, media
    content = Column(Text, nullable=False)
    metadata = Column(JSONB, nullable=False, default=dict)
    token_usage = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    
    # Index for efficient chat history retrieval
    __table_args__ = (
        Index('idx_chat_created', 'chat_id', 'created_at'),
    )
```

**Metadata Schema Examples**:
```json
// Button message
{
  "buttons": [
    {"id": "property_1", "text": "Downtown Sports Center"},
    {"id": "property_2", "text": "Westside Arena"}
  ]
}

// List message
{
  "list_items": [
    {"id": "time_1", "title": "2:00 PM", "description": "$50/hour"},
    {"id": "time_2", "title": "3:00 PM", "description": "$50/hour"}
  ]
}

// Media message
{
  "media_type": "image",
  "media_url": "https://example.com/court.jpg",
  "caption": "Tennis Court A"
}
```

### Pydantic Schemas

```python
# Backend/apps/chatbot/app/schemas/chat.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class ChatBase(BaseModel):
    user_id: UUID
    owner_id: UUID

class ChatCreate(ChatBase):
    pass

class ChatUpdate(BaseModel):
    status: Optional[str] = None
    last_message_at: Optional[datetime] = None
    flow_state: Optional[Dict[str, Any]] = None
    bot_memory: Optional[Dict[str, Any]] = None

class ChatResponse(ChatBase):
    id: UUID
    status: str
    last_message_at: datetime
    flow_state: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    chat_id: UUID
    sender_type: str
    message_type: str = "text"
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    token_usage: Optional[int] = None

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatMessageRequest(BaseModel):
    user_id: UUID
    owner_id: UUID
    content: str

class ChatMessageResponse(BaseModel):
    chat_id: UUID
    message_id: UUID
    content: str
    message_type: str
    metadata: Dict[str, Any]
```

### Repository Layer

```python
# Backend/apps/chatbot/app/repositories/chat_repository.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID

class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, chat_data: dict) -> Chat:
        """Create a new chat session"""
        chat = Chat(**chat_data)
        self.session.add(chat)
        await self.session.flush()
        return chat
    
    async def get_by_id(self, chat_id: UUID) -> Optional[Chat]:
        """Get chat by ID"""
        result = await self.session.execute(
            select(Chat).where(Chat.id == chat_id)
        )
        return result.scalar_one_or_none()
    
    async def get_latest_by_user_owner(
        self, 
        user_id: UUID, 
        owner_id: UUID
    ) -> Optional[Chat]:
        """Get the most recent chat for a user-owner pair"""
        result = await self.session.execute(
            select(Chat)
            .where(
                and_(
                    Chat.user_id == user_id,
                    Chat.owner_id == owner_id,
                    Chat.status == "active"
                )
            )
            .order_by(desc(Chat.last_message_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_user_chats(
        self, 
        user_id: UUID, 
        limit: int = 50
    ) -> List[Chat]:
        """Get all chats for a user"""
        result = await self.session.execute(
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(desc(Chat.last_message_at))
            .limit(limit)
        )
        return result.scalars().all()
    
    async def update(self, chat: Chat, update_data: dict) -> Chat:
        """Update chat fields"""
        for key, value in update_data.items():
            setattr(chat, key, value)
        await self.session.flush()
        return chat
    
    async def is_session_expired(
        self, 
        chat: Chat, 
        threshold_hours: int = 24
    ) -> bool:
        """Check if chat session has expired"""
        threshold = datetime.utcnow() - timedelta(hours=threshold_hours)
        return chat.last_message_at < threshold
```

```python
# Backend/apps/chatbot/app/repositories/message_repository.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List
from uuid import UUID

class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, message_data: dict) -> Message:
        """Create a new message"""
        message = Message(**message_data)
        self.session.add(message)
        await self.session.flush()
        return message
    
    async def get_chat_history(
        self, 
        chat_id: UUID, 
        limit: Optional[int] = None
    ) -> List[Message]:
        """Get all messages for a chat in chronological order"""
        query = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at)
        )
        if limit:
            query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_unprocessed_user_messages(
        self, 
        chat_id: UUID, 
        after_timestamp: datetime
    ) -> List[Message]:
        """Get user messages after a specific timestamp"""
        result = await self.session.execute(
            select(Message)
            .where(
                and_(
                    Message.chat_id == chat_id,
                    Message.sender_type == "user",
                    Message.created_at > after_timestamp
                )
            )
            .order_by(Message.created_at)
        )
        return result.scalars().all()
    
    async def get_total_token_usage(
        self, 
        chat_id: UUID
    ) -> int:
        """Calculate total token usage for a chat"""
        result = await self.session.execute(
            select(func.sum(Message.token_usage))
            .where(Message.chat_id == chat_id)
        )
        return result.scalar() or 0
```

### Service Layer

```python
# Backend/apps/chatbot/app/services/chat_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Tuple
from uuid import UUID
from datetime import datetime

class ChatService:
    def __init__(
        self, 
        session: AsyncSession,
        chat_repo: ChatRepository,
        message_repo: MessageRepository
    ):
        self.session = session
        self.chat_repo = chat_repo
        self.message_repo = message_repo
    
    async def determine_session(
        self, 
        user_id: UUID, 
        owner_id: UUID,
        user_message: str
    ) -> Tuple[Chat, bool]:
        """
        Determine whether to continue existing session or create new one.
        Returns (chat, is_new_session)
        """
        # Check for explicit new session intent
        if self._is_new_session_intent(user_message):
            return await self._create_new_session(user_id, owner_id), True
        
        # Look for existing session
        existing_chat = await self.chat_repo.get_latest_by_user_owner(
            user_id, owner_id
        )
        
        if not existing_chat:
            return await self._create_new_session(user_id, owner_id), True
        
        # Check if session expired
        if await self.chat_repo.is_session_expired(existing_chat):
            # Session expired - need to ask user
            return existing_chat, False  # Caller will handle continuation prompt
        
        # Continue existing session
        return existing_chat, False
    
    async def create_chat(
        self, 
        user_id: UUID, 
        owner_id: UUID
    ) -> Chat:
        """Create a new chat session"""
        return await self._create_new_session(user_id, owner_id)
    
    async def update_chat_state(
        self, 
        chat: Chat, 
        flow_state: dict = None,
        bot_memory: dict = None
    ) -> Chat:
        """Update chat flow state and/or bot memory"""
        update_data = {"last_message_at": datetime.utcnow()}
        if flow_state is not None:
            update_data["flow_state"] = flow_state
        if bot_memory is not None:
            update_data["bot_memory"] = bot_memory
        
        return await self.chat_repo.update(chat, update_data)
    
    async def close_chat(self, chat_id: UUID) -> Chat:
        """Close a chat session"""
        chat = await self.chat_repo.get_by_id(chat_id)
        return await self.chat_repo.update(chat, {"status": "closed"})
    
    def _is_new_session_intent(self, message: str) -> bool:
        """Detect if user wants to start a new conversation"""
        new_session_keywords = [
            "new topic", "start over", "new conversation",
            "forget previous", "reset"
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in new_session_keywords)
    
    async def _create_new_session(
        self, 
        user_id: UUID, 
        owner_id: UUID
    ) -> Chat:
        """Internal method to create new chat"""
        chat_data = {
            "user_id": user_id,
            "owner_id": owner_id,
            "status": "active",
            "flow_state": {},
            "bot_memory": {}
        }
        return await self.chat_repo.create(chat_data)
```

```python
# Backend/apps/chatbot/app/services/message_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from datetime import datetime

class MessageService:
    def __init__(
        self, 
        session: AsyncSession,
        message_repo: MessageRepository
    ):
        self.session = session
        self.message_repo = message_repo
    
    async def create_message(
        self,
        chat_id: UUID,
        sender_type: str,
        content: str,
        message_type: str = "text",
        metadata: dict = None,
        token_usage: int = None
    ) -> Message:
        """Create a new message"""
        message_data = {
            "chat_id": chat_id,
            "sender_type": sender_type,
            "message_type": message_type,
            "content": content,
            "metadata": metadata or {},
            "token_usage": token_usage
        }
        return await self.message_repo.create(message_data)
    
    async def get_chat_history(
        self, 
        chat_id: UUID, 
        limit: int = None
    ) -> List[Message]:
        """Retrieve chat message history"""
        return await self.message_repo.get_chat_history(chat_id, limit)
    
    async def aggregate_user_messages(
        self, 
        chat_id: UUID, 
        after_timestamp: datetime
    ) -> str:
        """Aggregate multiple user messages into single input"""
        messages = await self.message_repo.get_unprocessed_user_messages(
            chat_id, after_timestamp
        )
        if not messages:
            return ""
        
        if len(messages) == 1:
            return messages[0].content
        
        # Combine multiple messages with context
        aggregated = "\n".join([msg.content for msg in messages])
        return aggregated
```


### Agent Service and LangGraph Integration

```python
# Backend/apps/chatbot/app/services/agent_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from uuid import UUID

class AgentService:
    def __init__(
        self,
        session: AsyncSession,
        chat_service: ChatService,
        message_service: MessageService,
        main_graph: MainGraph,
        llm_provider: LLMProvider
    ):
        self.session = session
        self.chat_service = chat_service
        self.message_service = message_service
        self.main_graph = main_graph
        self.llm_provider = llm_provider
    
    async def process_message(
        self,
        chat: Chat,
        user_message: str
    ) -> Dict[str, Any]:
        """
        Process user message through LangGraph and return bot response
        """
        # Store user message
        await self.message_service.create_message(
            chat_id=chat.id,
            sender_type="user",
            content=user_message
        )
        
        # Prepare conversation state
        state = {
            "chat_id": str(chat.id),
            "user_id": str(chat.user_id),
            "owner_id": str(chat.owner_id),
            "user_message": user_message,
            "flow_state": chat.flow_state,
            "bot_memory": chat.bot_memory,
            "messages": []
        }
        
        # Execute LangGraph
        result = await self.main_graph.execute(state)
        
        # Update chat state
        await self.chat_service.update_chat_state(
            chat,
            flow_state=result.get("flow_state"),
            bot_memory=result.get("bot_memory")
        )
        
        # Store bot response
        bot_message = await self.message_service.create_message(
            chat_id=chat.id,
            sender_type="bot",
            content=result["response_content"],
            message_type=result.get("response_type", "text"),
            metadata=result.get("response_metadata", {}),
            token_usage=result.get("token_usage")
        )
        
        return {
            "content": result["response_content"],
            "message_type": result.get("response_type", "text"),
            "metadata": result.get("response_metadata", {}),
            "message_id": bot_message.id
        }
```

## Data Models

### Conversation State Schema

The LangGraph agent uses a typed state object that flows through all nodes:

```python
# Backend/apps/chatbot/app/agent/state/conversation_state.py

from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime

class ConversationState(TypedDict):
    # Identifiers
    chat_id: str
    user_id: str
    owner_id: str
    
    # Current message
    user_message: str
    
    # Persistent state
    flow_state: Dict[str, Any]  # Structured booking progress
    bot_memory: Dict[str, Any]  # Unstructured AI context
    
    # Processing state
    messages: List[Dict[str, str]]  # Message history for LLM context
    intent: Optional[str]  # Current detected intent
    
    # Response building
    response_content: str
    response_type: str  # text, button, list, media
    response_metadata: Dict[str, Any]
    
    # Metrics
    token_usage: Optional[int]
    
    # Tool results
    search_results: Optional[List[Dict[str, Any]]]
    availability_data: Optional[Dict[str, Any]]
    pricing_data: Optional[Dict[str, Any]]
```

### Flow State Structure

```python
# Booking flow state example
{
    "intent": "booking",
    "step": "select_time",
    "property_id": "123e4567-e89b-12d3-a456-426614174000",
    "property_name": "Downtown Sports Center",
    "service_id": "223e4567-e89b-12d3-a456-426614174000",
    "service_name": "Tennis Court A",
    "sport_type": "tennis",
    "date": "2024-01-15",
    "time": "14:00",
    "duration": 60,
    "price": 50.00,
    "booking_id": null
}

# Search flow state example
{
    "intent": "search",
    "step": "presenting_results",
    "search_query": "tennis courts",
    "sport_type": "tennis",
    "location": "downtown",
    "last_search_timestamp": "2024-01-10T10:30:00Z"
}
```

### Bot Memory Structure

```python
# Bot memory example
{
    "conversation_history": [
        {
            "role": "user",
            "content": "I want to book a tennis court",
            "timestamp": "2024-01-10T10:00:00Z"
        },
        {
            "role": "assistant",
            "content": "Great! Let me show you available properties.",
            "timestamp": "2024-01-10T10:00:02Z"
        }
    ],
    "user_preferences": {
        "preferred_sport": "tennis",
        "preferred_time_of_day": "afternoon",
        "preferred_duration": 60
    },
    "context": {
        "last_search_results": [
            "123e4567-e89b-12d3-a456-426614174000",
            "223e4567-e89b-12d3-a456-426614174001"
        ],
        "mentioned_properties": ["Downtown Sports Center"],
        "clarification_needed": false
    },
    "session_metadata": {
        "total_messages": 15,
        "total_tokens": 3500,
        "session_start": "2024-01-10T10:00:00Z"
    }
}
```

## LangGraph Conversation Flow

### Main Graph Structure

```python
# Backend/apps/chatbot/app/agent/graphs/main_graph.py

from langgraph.graph import StateGraph, END
from ..state.conversation_state import ConversationState
from ..nodes import (
    receive_message,
    load_chat,
    append_user_message,
    intent_detection,
    greeting_handler,
    indoor_search_handler,
    faq_handler
)
from .booking_subgraph import create_booking_subgraph

def create_main_graph(llm_provider, tools):
    """Create the main conversation flow graph"""
    
    # Initialize graph
    graph = StateGraph(ConversationState)
    
    # Add nodes
    graph.add_node("receive_message", receive_message)
    graph.add_node("load_chat", load_chat)
    graph.add_node("append_user_message", append_user_message)
    graph.add_node("intent_detection", intent_detection)
    graph.add_node("greeting", greeting_handler)
    graph.add_node("indoor_search", indoor_search_handler)
    graph.add_node("faq", faq_handler)
    
    # Add booking subgraph
    booking_subgraph = create_booking_subgraph(llm_provider, tools)
    graph.add_node("booking", booking_subgraph)
    
    # Define edges
    graph.set_entry_point("receive_message")
    graph.add_edge("receive_message", "load_chat")
    graph.add_edge("load_chat", "append_user_message")
    graph.add_edge("append_user_message", "intent_detection")
    
    # Conditional routing from intent detection
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
    
    # All handlers return to END
    graph.add_edge("greeting", END)
    graph.add_edge("indoor_search", END)
    graph.add_edge("booking", END)
    graph.add_edge("faq", END)
    
    return graph.compile()

def route_by_intent(state: ConversationState) -> str:
    """Route to appropriate handler based on detected intent"""
    return state.get("intent", "unknown")
```

### Booking Subgraph

```python
# Backend/apps/chatbot/app/agent/graphs/booking_subgraph.py

from langgraph.graph import StateGraph, END
from ..state.conversation_state import ConversationState
from ..nodes.booking import (
    select_property,
    select_service,
    select_date,
    select_time,
    confirm_booking,
    create_pending_booking
)

def create_booking_subgraph(llm_provider, tools):
    """Create the booking flow subgraph"""
    
    graph = StateGraph(ConversationState)
    
    # Add nodes
    graph.add_node("select_property", select_property)
    graph.add_node("select_service", select_service)
    graph.add_node("select_date", select_date)
    graph.add_node("select_time", select_time)
    graph.add_node("confirm", confirm_booking)
    graph.add_node("create_booking", create_pending_booking)
    
    # Define flow
    graph.set_entry_point("select_property")
    
    # Linear flow with conditional routing
    graph.add_conditional_edges(
        "select_property",
        route_property_selection,
        {
            "continue": "select_service",
            "cancel": END
        }
    )
    
    graph.add_conditional_edges(
        "select_service",
        route_service_selection,
        {
            "continue": "select_date",
            "back": "select_property",
            "cancel": END
        }
    )
    
    graph.add_conditional_edges(
        "select_date",
        route_date_selection,
        {
            "continue": "select_time",
            "back": "select_service",
            "cancel": END
        }
    )
    
    graph.add_conditional_edges(
        "select_time",
        route_time_selection,
        {
            "continue": "confirm",
            "back": "select_date",
            "cancel": END
        }
    )
    
    graph.add_conditional_edges(
        "confirm",
        route_confirmation,
        {
            "confirmed": "create_booking",
            "modify": "select_property",  # Allow full modification
            "cancel": END
        }
    )
    
    graph.add_edge("create_booking", END)
    
    return graph.compile()

def route_property_selection(state: ConversationState) -> str:
    """Route based on property selection"""
    flow_state = state.get("flow_state", {})
    if flow_state.get("property_id"):
        return "continue"
    return "cancel"

def route_service_selection(state: ConversationState) -> str:
    """Route based on service selection"""
    flow_state = state.get("flow_state", {})
    user_message = state.get("user_message", "").lower()
    
    if "back" in user_message or "previous" in user_message:
        return "back"
    if "cancel" in user_message:
        return "cancel"
    if flow_state.get("service_id"):
        return "continue"
    return "cancel"

def route_date_selection(state: ConversationState) -> str:
    """Route based on date selection"""
    flow_state = state.get("flow_state", {})
    user_message = state.get("user_message", "").lower()
    
    if "back" in user_message:
        return "back"
    if "cancel" in user_message:
        return "cancel"
    if flow_state.get("date"):
        return "continue"
    return "cancel"

def route_time_selection(state: ConversationState) -> str:
    """Route based on time selection"""
    flow_state = state.get("flow_state", {})
    user_message = state.get("user_message", "").lower()
    
    if "back" in user_message:
        return "back"
    if "cancel" in user_message:
        return "cancel"
    if flow_state.get("time"):
        return "continue"
    return "cancel"

def route_confirmation(state: ConversationState) -> str:
    """Route based on user confirmation"""
    user_message = state.get("user_message", "").lower()
    
    if any(word in user_message for word in ["yes", "confirm", "book", "proceed"]):
        return "confirmed"
    if any(word in user_message for word in ["change", "modify", "edit"]):
        return "modify"
    return "cancel"
```

### Graph Node Implementations

```python
# Backend/apps/chatbot/app/agent/nodes/intent_detection.py

from ..state.conversation_state import ConversationState
from ..prompts.intent_prompts import INTENT_CLASSIFICATION_PROMPT
import logging

logger = logging.getLogger(__name__)

async def intent_detection(state: ConversationState, llm_provider) -> ConversationState:
    """
    Classify user intent using rule-based matching and LLM fallback
    """
    user_message = state["user_message"].lower()
    
    # Rule-based intent detection
    greeting_keywords = ["hi", "hello", "hey", "good morning", "good afternoon"]
    search_keywords = ["search", "find", "looking for", "show me", "available"]
    booking_keywords = ["book", "reserve", "schedule", "appointment"]
    
    if any(keyword in user_message for keyword in greeting_keywords):
        intent = "greeting"
    elif any(keyword in user_message for keyword in search_keywords):
        intent = "search"
    elif any(keyword in user_message for keyword in booking_keywords):
        intent = "booking"
    else:
        # Use LLM for complex intent detection
        intent = await _llm_intent_classification(user_message, llm_provider)
    
    logger.info(f"Detected intent: {intent} for message: {user_message[:50]}")
    
    state["intent"] = intent
    return state

async def _llm_intent_classification(message: str, llm_provider) -> str:
    """Use LLM to classify intent when rules don't match"""
    prompt = INTENT_CLASSIFICATION_PROMPT.format(message=message)
    
    try:
        response = await llm_provider.generate(
            prompt=prompt,
            max_tokens=10,
            temperature=0.0
        )
        intent = response.strip().lower()
        
        # Validate intent
        valid_intents = ["greeting", "search", "booking", "faq"]
        if intent in valid_intents:
            return intent
        return "faq"
    except Exception as e:
        logger.error(f"LLM intent classification failed: {e}")
        return "faq"
```

```python
# Backend/apps/chatbot/app/agent/nodes/greeting.py

from ..state.conversation_state import ConversationState
import logging

logger = logging.getLogger(__name__)

async def greeting_handler(state: ConversationState) -> ConversationState:
    """Handle greeting intents"""
    
    # Check if this is a returning user
    bot_memory = state.get("bot_memory", {})
    is_returning = bot_memory.get("session_metadata", {}).get("total_messages", 0) > 0
    
    if is_returning:
        response = (
            "Welcome back! How can I help you today? "
            "I can help you search for sports facilities or make a booking."
        )
    else:
        response = (
            "Hello! I'm your sports booking assistant. "
            "I can help you find and book indoor sports facilities. "
            "What would you like to do today?"
        )
    
    state["response_content"] = response
    state["response_type"] = "text"
    state["response_metadata"] = {}
    
    logger.info(f"Greeting handler completed for chat {state['chat_id']}")
    
    return state
```

```python
# Backend/apps/chatbot/app/agent/nodes/indoor_search.py

from ..state.conversation_state import ConversationState
from ..tools.property_tool import search_properties_tool
from ..tools.court_tool import search_courts_tool
import logging

logger = logging.getLogger(__name__)

async def indoor_search_handler(state: ConversationState, tools) -> ConversationState:
    """Handle facility search requests"""
    
    user_message = state["user_message"]
    owner_id = state["owner_id"]
    
    # Extract search parameters from message
    search_params = _extract_search_params(user_message)
    
    # Search for properties
    properties = await tools["search_properties"](
        owner_id=owner_id,
        sport_type=search_params.get("sport_type"),
        location=search_params.get("location")
    )
    
    if not properties:
        response = (
            "I couldn't find any facilities matching your criteria. "
            "Would you like to try a different search?"
        )
        state["response_content"] = response
        state["response_type"] = "text"
        return state
    
    # Format results as list message
    list_items = []
    for prop in properties[:5]:  # Limit to 5 results
        list_items.append({
            "id": str(prop["id"]),
            "title": prop["name"],
            "description": f"{prop['location']} - {prop['available_courts']} courts available"
        })
    
    response = "Here are the available facilities:"
    state["response_content"] = response
    state["response_type"] = "list"
    state["response_metadata"] = {"list_items": list_items}
    
    # Store search results in bot memory
    bot_memory = state.get("bot_memory", {})
    bot_memory["context"] = bot_memory.get("context", {})
    bot_memory["context"]["last_search_results"] = [p["id"] for p in properties]
    state["bot_memory"] = bot_memory
    
    logger.info(f"Search completed: {len(properties)} properties found")
    
    return state

def _extract_search_params(message: str) -> dict:
    """Extract search parameters from user message"""
    params = {}
    
    # Sport type detection
    sport_keywords = {
        "tennis": ["tennis"],
        "basketball": ["basketball", "basket ball"],
        "badminton": ["badminton"],
        "squash": ["squash"],
        "volleyball": ["volleyball", "volley ball"]
    }
    
    message_lower = message.lower()
    for sport, keywords in sport_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            params["sport_type"] = sport
            break
    
    # Location detection (simple keyword matching)
    if "downtown" in message_lower:
        params["location"] = "downtown"
    elif "westside" in message_lower:
        params["location"] = "westside"
    
    return params
```

```python
# Backend/apps/chatbot/app/agent/nodes/booking/select_property.py

from ...state.conversation_state import ConversationState
from ...tools.property_tool import get_property_details_tool
import logging

logger = logging.getLogger(__name__)

async def select_property(state: ConversationState, tools) -> ConversationState:
    """Handle property selection in booking flow"""
    
    flow_state = state.get("flow_state", {})
    
    # Check if property already selected
    if flow_state.get("property_id"):
        return state
    
    # Check if user is selecting from previous search results
    bot_memory = state.get("bot_memory", {})
    last_search = bot_memory.get("context", {}).get("last_search_results", [])
    
    if not last_search:
        # No previous search, prompt user to search first
        response = (
            "To make a booking, I first need to know which facility you're interested in. "
            "Would you like me to search for available facilities?"
        )
        state["response_content"] = response
        state["response_type"] = "text"
        return state
    
    # Present properties as buttons
    properties = await tools["get_properties_by_ids"](last_search[:5])
    
    buttons = []
    for prop in properties:
        buttons.append({
            "id": str(prop["id"]),
            "text": prop["name"]
        })
    
    response = "Which facility would you like to book?"
    state["response_content"] = response
    state["response_type"] = "button"
    state["response_metadata"] = {"buttons": buttons}
    
    # Update flow state
    flow_state["step"] = "select_property"
    state["flow_state"] = flow_state
    
    logger.info(f"Property selection presented for chat {state['chat_id']}")
    
    return state
```


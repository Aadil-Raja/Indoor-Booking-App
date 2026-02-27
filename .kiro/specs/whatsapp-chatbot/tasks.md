# Implementation Plan: WhatsApp-Style Chatbot Module

## Overview

This implementation plan breaks down the WhatsApp-style chatbot feature into discrete, actionable coding tasks. The chatbot module will be built as a separate async FastAPI application within the existing Backend/apps/chatbot directory, with its own async PostgreSQL database for chat data. The implementation follows a bottom-up approach: database layer → repository layer → service layer → LLM providers → LangGraph agent → API endpoints.

The chatbot integrates with existing sync services (booking, property, court, availability) through a sync-to-async bridge pattern, enabling natural language interactions for facility search and booking.

**Important Notes:**
- Properties are linked to OwnerProfile (not directly to User)
- The chatbot uses a separate async database (CHAT_DATABASE_URL) for chat/message data
- Integration with main database services uses MAIN_DATABASE_URL (sync)
- Configuration is in Backend/apps/chatbot/.env with both database URLs

## Tasks

- [x] 1. Set up async database infrastructure and core models
  - [x] 1.1 Create async database configuration and engine
    - Implement `Backend/apps/chatbot/app/core/config.py` with CHAT_DATABASE_URL (async) and MAIN_DATABASE_URL (sync) settings
    - Implement `Backend/apps/chatbot/app/core/database.py` with `create_async_engine`, `AsyncSessionLocal`, and `get_async_db` dependency
    - Configure connection pooling for async operations
    - Add JWT_SECRET, LLM provider settings, and session configuration
    - _Requirements: 1.1, 1.3, 16.1_
  
  - [x] 1.2 Implement Chat and Message database models
    - Replace existing `chat_message.py` with proper `chat.py` model (UUID primary key, user_id, owner_id, status, last_message_at, flow_state JSONB, bot_memory JSONB, timestamps)
    - Create `message.py` model (UUID primary key, chat_id FK, sender_type, message_type, content, metadata JSONB, token_usage, created_at)
    - Add proper indexes for efficient queries (user_owner_last_message, chat_created)
    - Update `__init__.py` to export both models
    - _Requirements: 2.1-2.9, 3.1-3.8, 16.1_
  
  - [x] 1.3 Create Alembic migration for Chat and Message tables
    - Generate migration script for new async database schema
    - Include all indexes and constraints
    - Test migration up and down
    - _Requirements: 1.1, 2.1, 3.1_

- [x] 2. Implement Pydantic schemas for request/response validation
  - [x] 2.1 Create chat schemas
    - Implement `Backend/apps/chatbot/app/schemas/chat.py` with ChatBase, ChatCreate, ChatUpdate, ChatResponse
    - Implement MessageBase, MessageCreate, MessageResponse
    - Implement ChatMessageRequest, ChatMessageResponse for API endpoints
    - _Requirements: 16.2, 17.2-17.3_
  
  - [x] 2.2 Create agent state schemas
    - Implement `Backend/apps/chatbot/app/agent/state/conversation_state.py` with ConversationState TypedDict
    - Include all required fields: chat_id, user_id, owner_id, user_message, flow_state, bot_memory, messages, intent, response fields, token_usage, tool results
    - _Requirements: 6.4-6.5, 20.1-20.8_

- [x] 3. Build repository layer for data access
  - [x] 3.1 Implement ChatRepository
    - Create `Backend/apps/chatbot/app/repositories/chat_repository.py`
    - Implement async methods: create, get_by_id, get_latest_by_user_owner, get_user_chats, update, is_session_expired
    - Use AsyncSession for all database operations
    - _Requirements: 1.3, 4.1-4.8, 11.2-11.3, 16.3_
  
  - [x] 3.2 Implement MessageRepository
    - Create `Backend/apps/chatbot/app/repositories/message_repository.py`
    - Implement async methods: create, get_chat_history, get_unprocessed_user_messages, get_total_token_usage
    - Use AsyncSession for all database operations
    - _Requirements: 1.3, 5.1-5.3, 11.2-11.3, 13.4, 16.3_

- [x] 4. Implement core service layer
  - [x] 4.1 Implement ChatService
    - Create `Backend/apps/chatbot/app/services/chat_service.py`
    - Implement async methods: determine_session, create_chat, update_chat_state, close_chat
    - Implement session continuity logic (24-hour threshold, new topic detection)
    - Use transaction management for state updates
    - _Requirements: 4.1-4.8, 11.1-11.5, 15.1-15.5, 16.4, 20.1-20.8_
  
  - [x] 4.2 Implement MessageService
    - Create `Backend/apps/chatbot/app/services/message_service.py`
    - Implement async methods: create_message, get_chat_history, aggregate_user_messages
    - Handle multi-message aggregation for sequential user inputs
    - _Requirements: 5.1-5.6, 11.1-11.5, 16.4_

- [x] 5. Implement LLM provider abstraction layer
  - [x] 5.1 Create abstract LLMProvider base class
    - Create `Backend/apps/chatbot/app/services/llm/base.py`
    - Define abstract methods: generate, stream, count_tokens
    - Define standardized exception classes for provider errors
    - _Requirements: 7.1-7.4, 7.8, 14.1-14.2_
  
  - [x] 5.2 Implement OpenAIProvider
    - Create `Backend/apps/chatbot/app/services/llm/openai_provider.py`
    - Implement all abstract methods using OpenAI SDK
    - Add retry logic with exponential backoff (3 retries)
    - Include token counting and usage tracking
    - _Requirements: 7.5, 12.2, 13.1-13.2, 14.1-14.2_
  
  - [x] 5.3 Create GeminiProvider placeholder
    - Create `Backend/apps/chatbot/app/services/llm/gemini_provider.py`
    - Implement stub methods that raise NotImplementedError
    - Add documentation for future implementation
    - _Requirements: 7.6_
  
  - [x] 5.4 Create LLM provider factory and configuration
    - Create `Backend/apps/chatbot/app/services/llm/__init__.py` with factory function
    - Add LLM provider configuration to core config
    - Implement provider selection based on environment variables
    - _Requirements: 7.1-7.2, 16.1_

- [x] 6. Checkpoint - Verify core infrastructure
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Implement agent tools for service integration
  - [x] 7.1 Create sync-to-async bridge utility
    - Create `Backend/apps/chatbot/app/agent/tools/sync_bridge.py`
    - Implement `run_sync_in_executor` function to wrap sync service calls
    - Handle session management for sync database operations
    - _Requirements: 8.1, 9.1-9.3, 10.1-10.2, 11.4, 19.1-19.5_
  
  - [x] 7.2 Implement property search tool
    - Create `Backend/apps/chatbot/app/agent/tools/property_tool.py`
    - Implement `search_properties_tool` wrapping property_service.search_properties
    - Implement `get_property_details_tool` for property information
    - Note: Properties are linked to OwnerProfile, access via owner_profile.properties
    - Use sync bridge for database access
    - _Requirements: 9.1-9.2, 19.1-19.5_
  
  - [x] 7.3 Implement court search tool
    - Create `Backend/apps/chatbot/app/agent/tools/court_tool.py`
    - Implement `search_courts_tool` wrapping court_service.search_courts_by_sport_type
    - Implement `get_court_details_tool` for court information
    - Use sync bridge for database access
    - _Requirements: 9.3-9.4, 19.1-19.5_
  
  - [x] 7.4 Implement availability tool
    - Create `Backend/apps/chatbot/app/agent/tools/availability_tool.py`
    - Implement `check_availability_tool` wrapping availability_service.check_blocked_slots
    - Implement `get_available_slots_tool` for time slot retrieval
    - Use sync bridge for database access
    - _Requirements: 10.1-10.3, 19.1-19.5_
  
  - [x] 7.5 Implement pricing tool
    - Create `Backend/apps/chatbot/app/agent/tools/pricing_tool.py`
    - Implement `get_pricing_tool` wrapping pricing_service.get_pricing_for_time_slot
    - Calculate total price for selected duration
    - Use sync bridge for database access
    - _Requirements: 10.4-10.5, 19.1-19.5_
  
  - [x] 7.6 Implement booking tool
    - Create `Backend/apps/chatbot/app/agent/tools/booking_tool.py`
    - Implement `create_booking_tool` wrapping booking_service.create_booking
    - Handle booking creation with pending status
    - Use sync bridge for database access
    - _Requirements: 8.1-8.6, 19.1-19.5_
  
  - [x] 7.7 Create tool registry and initialization
    - Create `Backend/apps/chatbot/app/agent/tools/__init__.py`
    - Implement tool registry dictionary with all tools
    - Add tool initialization function with dependency injection
    - _Requirements: 6.6, 16.8_

- [x] 8. Implement LangGraph nodes for conversation flow
  - [x] 8.1 Create basic flow nodes
    - Create `Backend/apps/chatbot/app/agent/nodes/basic_nodes.py`
    - Implement receive_message, load_chat, append_user_message nodes
    - Handle message history management in bot_memory
    - _Requirements: 6.1, 6.4-6.5, 20.1-20.8_
  
  - [x] 8.2 Implement intent detection node
    - Create `Backend/apps/chatbot/app/agent/nodes/intent_detection.py`
    - Implement rule-based intent classification (greeting, search, booking, faq)
    - Add LLM fallback for complex intent detection
    - Update flow_state with detected intent
    - _Requirements: 6.2, 21.1-21.6_
  
  - [x] 8.3 Implement greeting handler node
    - Create `Backend/apps/chatbot/app/agent/nodes/greeting.py`
    - Generate contextual greeting based on session history
    - Differentiate between new and returning users
    - _Requirements: 6.1, 21.1_
  
  - [x] 8.4 Implement indoor search handler node
    - Create `Backend/apps/chatbot/app/agent/nodes/indoor_search.py`
    - Extract search parameters from user message (sport type, location)
    - Call property and court search tools
    - Format results as list message type
    - Store search results in bot_memory
    - _Requirements: 9.1-9.7, 21.2, 23.1-23.6_
  
  - [x] 8.5 Implement FAQ handler node
    - Create `Backend/apps/chatbot/app/agent/nodes/faq.py`
    - Use LLM to generate responses for general questions
    - Handle unknown intents gracefully
    - _Requirements: 6.1, 21.4_

- [x] 9. Implement booking subgraph nodes
  - [x] 9.1 Implement select property node
    - Create `Backend/apps/chatbot/app/agent/nodes/booking/select_property.py`
    - Present properties from search results as buttons
    - Store selected property_id in flow_state
    - Update flow_state step to "select_property"
    - _Requirements: 6.3, 20.2, 22.1-22.6, 23.2_
  
  - [x] 9.2 Implement select service node
    - Create `Backend/apps/chatbot/app/agent/nodes/booking/select_service.py`
    - Retrieve courts for selected property using court tool
    - Present courts as list with sport type information
    - Store selected service_id in flow_state
    - Update flow_state step to "select_service"
    - _Requirements: 6.3, 20.3, 22.1-22.6, 23.3_
  
  - [x] 9.3 Implement select date node
    - Create `Backend/apps/chatbot/app/agent/nodes/booking/select_date.py`
    - Parse date from user message or present calendar options
    - Validate date is in the future
    - Store selected date in flow_state
    - Update flow_state step to "select_date"
    - _Requirements: 6.3, 20.4, 22.1-22.6_
  
  - [x] 9.4 Implement select time node
    - Create `Backend/apps/chatbot/app/agent/nodes/booking/select_time.py`
    - Call availability tool to get available slots for selected date
    - Call pricing tool to get prices for each slot
    - Present slots with pricing as list message
    - Exclude blocked slots from options
    - Store selected time in flow_state
    - Update flow_state step to "select_time"
    - _Requirements: 6.3, 10.1-10.6, 20.5, 22.1-22.6, 23.3_
  
  - [x] 9.5 Implement confirm booking node
    - Create `Backend/apps/chatbot/app/agent/nodes/booking/confirm.py`
    - Generate booking summary with all details (property, court, date, time, price)
    - Ask for explicit user confirmation
    - Handle confirmation, cancellation, or modification requests
    - Update flow_state step to "confirm"
    - _Requirements: 6.3, 22.1-22.6_
  
  - [x] 9.6 Implement create pending booking node
    - Create `Backend/apps/chatbot/app/agent/nodes/booking/create_booking.py`
    - Call booking tool to create booking with pending status
    - Store booking_id in flow_state on success
    - Handle booking creation errors with retry information
    - Clear booking fields from flow_state on completion
    - Generate confirmation message with booking details
    - _Requirements: 6.3, 8.1-8.6, 20.8, 22.1-22.6_

- [x] 10. Implement LangGraph graph structures
  - [x] 10.1 Create booking subgraph
    - Create `Backend/apps/chatbot/app/agent/graphs/booking_subgraph.py`
    - Define StateGraph with booking nodes
    - Implement conditional routing functions (route_property_selection, route_service_selection, etc.)
    - Support back navigation and cancellation at each step
    - Wire nodes: select_property → select_service → select_date → select_time → confirm → create_booking
    - _Requirements: 6.3, 6.8, 22.1-22.6_
  
  - [x] 10.2 Create main conversation graph
    - Create `Backend/apps/chatbot/app/agent/graphs/main_graph.py`
    - Define StateGraph with all top-level nodes
    - Implement route_by_intent function for conditional routing
    - Integrate booking subgraph as a node
    - Wire flow: receive_message → load_chat → append_user_message → intent_detection → [handler nodes] → END
    - _Requirements: 6.1-6.8_
  
  - [x] 10.3 Create graph runtime and initialization
    - Create `Backend/apps/chatbot/app/agent/runtime/graph_runtime.py`
    - Implement graph compilation and execution wrapper
    - Add structured logging for node transitions
    - Handle graph execution errors gracefully
    - _Requirements: 6.8, 12.3, 14.3-14.5, 16.11_

- [x] 11. Implement AgentService for orchestration
  - [x] 11.1 Create AgentService
    - Create `Backend/apps/chatbot/app/services/agent_service.py`
    - Implement process_message method to orchestrate LangGraph execution
    - Store user message before processing
    - Prepare conversation state from chat data
    - Execute main graph and handle results
    - Update chat state with new flow_state and bot_memory
    - Store bot response with token usage
    - _Requirements: 6.1-6.8, 11.1-11.5, 12.1-12.3, 13.1-13.3, 15.1-15.5_

- [x] 12. Checkpoint - Verify agent and graph implementation
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Implement prompt templates
  - [x] 13.1 Create intent classification prompts
    - Create `Backend/apps/chatbot/app/agent/prompts/intent_prompts.py`
    - Define INTENT_CLASSIFICATION_PROMPT template
    - Include examples for each intent type
    - _Requirements: 21.5_
  
  - [x] 13.2 Create conversation prompts
    - Create `Backend/apps/chatbot/app/agent/prompts/conversation_prompts.py`
    - Define prompts for natural language generation in various contexts
    - Include system prompts for bot personality and behavior
    - _Requirements: 21.1-21.6_

- [x] 14. Implement API endpoints and routers
  - [x] 14.1 Create chat message endpoint
    - Create `Backend/apps/chatbot/app/routers/chat.py`
    - Implement POST /api/chat/message endpoint
    - Handle session continuity (check for expired sessions, ask user about continuation)
    - Call AgentService to process message
    - Return bot response with chat_id and message_id
    - Add structured logging for all requests
    - _Requirements: 4.1-4.8, 12.1, 17.1-17.3, 18.1-18.3_
  
  - [x] 14.2 Create chat history endpoint
    - Add GET /api/chat/history/{chat_id} endpoint to chat router
    - Verify user has access to chat (user_id matches or is owner)
    - Return all messages in chronological order
    - _Requirements: 17.4-17.5, 18.1-18.5_
  
  - [x] 14.3 Create new chat endpoint
    - Add POST /api/chat/new endpoint to chat router
    - Create new chat session explicitly
    - Return chat_id for new session
    - _Requirements: 17.6_
  
  - [x] 14.4 Create list chats endpoint
    - Add GET /api/chat/list endpoint to chat router
    - Return user's chat sessions ordered by last_message_at descending
    - Include last message preview and unread count
    - _Requirements: 17.7-17.8, 18.1-18.5_
  
  - [x] 14.5 Update health check endpoint
    - Update `Backend/apps/chatbot/app/routers/health.py`
    - Add Chat_Database connectivity check
    - Add LLM_Provider availability check
    - Return detailed health status
    - _Requirements: 26.1-26.3_

- [x] 15. Implement authentication and dependency injection
  - [x] 15.1 Create authentication dependencies
    - Create `Backend/apps/chatbot/app/deps/auth.py`
    - Implement get_current_user dependency (reuse from management app pattern)
    - Add authorization helpers for chat access verification
    - _Requirements: 17.9, 18.1-18.5_
  
  - [x] 15.2 Create service dependencies
    - Create `Backend/apps/chatbot/app/deps/services.py`
    - Implement dependency injection for ChatService, MessageService, AgentService
    - Implement dependency injection for LLMProvider
    - Implement dependency injection for tool registry
    - _Requirements: 16.14_

- [x] 16. Implement structured logging and error handling
  - [x] 16.1 Create logging configuration
    - Create `Backend/apps/chatbot/app/core/logging_config.py`
    - Configure structured JSON logging
    - Set up log levels and formatters
    - _Requirements: 12.1-12.6_
  
  - [x] 16.2 Add logging to all service methods
    - Add structured logging to ChatService, MessageService, AgentService
    - Log all incoming messages with context (chat_id, user_id, owner_id)
    - Log all LLM calls with token usage
    - Log all tool invocations with parameters and results
    - Log all errors with full context
    - _Requirements: 12.1-12.6_
  
  - [x] 16.3 Implement error handling middleware
    - Create `Backend/apps/chatbot/app/core/error_handlers.py`
    - Add global exception handlers for common errors
    - Return user-friendly error messages
    - Log all errors with correlation IDs
    - _Requirements: 14.1-14.5, 24.1-24.5_

- [x] 17. Implement transaction management and retry logic
  - [x] 17.1 Add transaction wrappers to repositories
    - Ensure all repository methods properly use async transactions
    - Add rollback handling for failed operations
    - _Requirements: 15.1-15.5_
  
  - [x] 17.2 Implement retry logic for LLM calls
    - Add exponential backoff retry decorator
    - Configure retry limits (3 attempts)
    - Add fallback responses for retry exhaustion
    - _Requirements: 14.1-14.2, 24.1-24.5_
  
  - [x] 17.3 Add graceful degradation for service failures
    - Implement fallback responses when LLM is unavailable
    - Handle main database service unavailability
    - Provide helpful error messages to users
    - _Requirements: 24.1-24.5_

- [x] 18. Update main application and wire everything together
  - [x] 18.1 Update main.py with all routers
    - Import and include chat router
    - Configure CORS and middleware
    - Add startup and shutdown event handlers
    - Initialize database on startup
    - _Requirements: 16.5, 17.1-17.10_
  
  - [x] 18.2 Create application factory
    - Create `Backend/apps/chatbot/app/core/app_factory.py`
    - Implement create_app function with all configuration
    - Initialize all dependencies and services
    - _Requirements: 16.1-16.14_
  
  - [x] 18.3 Update requirements.txt
    - Add langgraph, openai, asyncpg, and other required dependencies
    - Pin versions for production stability
    - _Requirements: 1.1, 6.1, 7.5_

- [x] 19. Create utility functions and helpers
  - [x] 19.1 Create response utility
    - Create `Backend/apps/chatbot/app/utils/response_utils.py`
    - Implement make_response function for consistent API responses (reuse pattern from management app)
    - _Requirements: 17.10_
  
  - [x] 19.2 Create date/time utilities
    - Create `Backend/apps/chatbot/app/utils/datetime_utils.py`
    - Implement date parsing and validation helpers
    - Implement time slot calculation utilities
    - _Requirements: 20.4-20.5_
  
  - [x] 19.3 Create message formatting utilities
    - Create `Backend/apps/chatbot/app/utils/message_utils.py`
    - Implement formatters for different message types (text, button, list)
    - Implement message aggregation helpers
    - _Requirements: 5.1-5.6, 23.1-23.6_

- [x] 20. Final checkpoint and integration verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks reference specific requirements for traceability
- The implementation follows a bottom-up approach: database → repositories → services → agent → API
- Each checkpoint ensures incremental validation before proceeding
- The chatbot module is completely separate from the management app but integrates through service interfaces
- Async/await patterns are used throughout for efficient concurrent conversation handling
- The sync-to-async bridge enables integration with existing sync services without modification
- LangGraph provides structured, maintainable conversation flow management
- All database operations use transactions to ensure data consistency
- Structured logging and error handling provide production-grade observability

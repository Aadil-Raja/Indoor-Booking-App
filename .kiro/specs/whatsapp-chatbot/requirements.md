# Requirements Document: WhatsApp-Style Chatbot Module

## Introduction

This document specifies requirements for a production-grade WhatsApp-style chatbot module integrated into an existing FastAPI backend. The chatbot enables customers to search for indoor sports facilities, check availability, and create bookings through conversational interactions. The system uses LangGraph for conversation flow management, maintains separate async chat storage, and integrates with existing booking services.

## Glossary

- **Chat_System**: The complete chatbot module including API, services, repositories, and agent components
- **Chat_Database**: Separate async PostgreSQL database containing only chat and message data
- **Main_Database**: Existing sync PostgreSQL database containing users, owner_profiles, properties, courts, bookings, and related data
- **Chat_Session**: A conversation thread between a user and the bot associated with a specific owner
- **Flow_State**: Structured JSONB field tracking current booking progress (property_id, service_id, date, time, intent, step)
- **Bot_Memory**: Unstructured JSONB field for AI context and conversation history
- **LangGraph_Agent**: State machine managing conversation flow through structured nodes
- **Intent_Node**: Graph node that classifies user intent (greeting, search, booking, FAQ)
- **Booking_Subgraph**: Nested graph handling multi-step booking flow
- **LLM_Provider**: Abstract interface for language model interactions
- **Message_Aggregator**: Component that combines multiple sequential user messages
- **Tool**: Function callable by the agent to interact with existing services
- **Pending_Booking**: Booking record created by bot awaiting confirmation or payment
- **Session_Continuity**: Logic determining whether to continue or create new chat based on time elapsed
- **Token_Usage**: Count of LLM tokens consumed per message for cost tracking
- **Owner**: Property owner (via OwnerProfile) whose facilities are being booked
- **Customer**: User interacting with the chatbot to make bookings

## Requirements

### Requirement 1: Separate Async Chat Database

**User Story:** As a system architect, I want chat data stored in a separate async database, so that chat operations don't block the main application and can scale independently.

#### Acceptance Criteria

1. THE Chat_System SHALL create an async database engine using create_async_engine for the Chat_Database
2. THE Chat_Database SHALL contain only the chats table and messages table
3. THE Chat_System SHALL use AsyncSession for all Chat_Database operations
4. THE Chat_System SHALL NOT create foreign key constraints between Chat_Database and Main_Database
5. WHEN storing user_id or owner_id in Chat_Database, THE Chat_System SHALL store them as reference-only fields without FK constraints

### Requirement 2: Chat Model Schema

**User Story:** As a developer, I want a well-defined chat model, so that conversation sessions are properly tracked and managed.

#### Acceptance Criteria

1. THE Chat model SHALL include id field as UUID primary key
2. THE Chat model SHALL include user_id field referencing Main_Database User table without FK constraint
3. THE Chat model SHALL include owner_id field referencing Main_Database User table without FK constraint
4. THE Chat model SHALL include status field with values (active, closed)
5. THE Chat model SHALL include last_message_at field as datetime
6. THE Chat model SHALL include flow_state field as JSONB storing structured booking state
7. THE Chat model SHALL include bot_memory field as JSONB storing free-form AI context
8. THE Chat model SHALL include created_at and updated_at timestamp fields
9. THE Flow_State JSONB SHALL support keys: property_id, service_id, date, time, intent, step

### Requirement 3: Message Model Schema

**User Story:** As a developer, I want a structured message model, so that all conversation messages are properly stored and retrievable.

#### Acceptance Criteria

1. THE Message model SHALL include id field as UUID primary key
2. THE Message model SHALL include chat_id field as foreign key to chats table
3. THE Message model SHALL include sender_type field with values (user, bot, system)
4. THE Message model SHALL include message_type field with values (text, button, list, media)
5. THE Message model SHALL include content field as text
6. THE Message model SHALL include metadata field as JSONB
7. THE Message model SHALL include token_usage field as nullable integer
8. THE Message model SHALL include created_at timestamp field

### Requirement 4: Session Continuity Management

**User Story:** As a customer, I want the bot to remember recent conversations, so that I can continue where I left off without repeating information.

#### Acceptance Criteria

1. WHEN a message is received, THE Chat_System SHALL query for the latest Chat_Session by user_id and owner_id
2. IF no Chat_Session exists, THEN THE Chat_System SHALL create a new Chat_Session
3. IF a Chat_Session exists AND last_message_at is within 24 hours, THEN THE Chat_System SHALL continue the existing Chat_Session
4. IF a Chat_Session exists AND last_message_at exceeds 24 hours, THEN THE Chat_System SHALL ask the user "Are you referring to our previous conversation?"
5. WHEN user confirms previous conversation reference, THE Chat_System SHALL continue the existing Chat_Session
6. WHEN user denies previous conversation reference, THE Chat_System SHALL create a new Chat_Session
7. WHEN user message contains "new topic" or equivalent intent, THE Chat_System SHALL create a new Chat_Session
8. WHEN continuing a Chat_Session, THE Chat_System SHALL load flow_state and bot_memory from the existing session

### Requirement 5: Multi-Message Handling

**User Story:** As a customer, I want to send multiple messages in quick succession, so that I can communicate naturally like in WhatsApp.

#### Acceptance Criteria

1. WHEN multiple user messages arrive sequentially, THE Message_Aggregator SHALL store each message separately in the messages table
2. WHEN processing user input, THE Message_Aggregator SHALL retrieve all unprocessed user messages in chronological order
3. THE Message_Aggregator SHALL aggregate retrieved messages into a single input for the LangGraph_Agent
4. THE Chat_System SHALL preserve all intermediate messages in the database
5. THE Chat_System SHALL support both combined replies and sequential replies based on message content
6. WHEN generating responses, THE Chat_System SHALL maintain conversational tone across aggregated messages

### Requirement 6: LangGraph Architecture

**User Story:** As a developer, I want a structured conversation flow using LangGraph, so that the bot handles complex booking workflows reliably.

#### Acceptance Criteria

1. THE LangGraph_Agent SHALL implement a high-level graph with nodes: Receive_Message, Load_Chat, Append_User_Message, Intent_Detection, Greeting, Indoor_Search, Booking_Subgraph, FAQ
2. THE Intent_Detection node SHALL classify user intent and route to appropriate handler node
3. THE Booking_Subgraph SHALL implement nested nodes: Select_Property, Select_Service, Select_Date, Select_Time, Confirm, Create_Pending_Booking, End
4. WHEN executing a node, THE LangGraph_Agent SHALL read current flow_state and bot_memory
5. WHEN a node completes, THE LangGraph_Agent SHALL update flow_state and bot_memory as needed
6. THE LangGraph_Agent SHALL call tools to interact with existing services
7. THE LangGraph_Agent SHALL invoke LLM_Provider only when natural language generation is required
8. THE LangGraph_Agent SHALL maintain state persistence between node transitions

### Requirement 7: LLM Provider Abstraction

**User Story:** As a developer, I want an abstract LLM provider interface, so that we can switch between different language models without changing business logic.

#### Acceptance Criteria

1. THE Chat_System SHALL define an abstract LLM_Provider base class
2. THE LLM_Provider interface SHALL include generate() method for text completion
3. THE LLM_Provider interface SHALL include stream() method for streaming responses
4. THE LLM_Provider interface SHALL include count_tokens() method for token calculation
5. THE Chat_System SHALL implement OpenAIProvider class conforming to LLM_Provider interface
6. THE Chat_System SHALL provide placeholder GeminiProvider class for future implementation
7. THE Chat_System SHALL NOT use OpenAI SDK directly in business logic outside provider implementations
8. WHEN a provider method fails, THE LLM_Provider SHALL raise a standardized exception

### Requirement 8: Booking Integration

**User Story:** As a customer, I want bookings created through the bot to appear in the main system, so that my reservations are properly recorded.

#### Acceptance Criteria

1. WHEN booking is confirmed in Booking_Subgraph, THE Chat_System SHALL call booking_service.create_booking() from Main_Database
2. THE Chat_System SHALL create the booking with pending status
3. WHEN booking is created successfully, THE Chat_System SHALL store booking_id in flow_state
4. WHEN booking creation fails, THE Chat_System SHALL inform the user and retain booking details in flow_state for retry
5. WHEN booking is completed, THE Chat_System SHALL clear booking-specific fields from flow_state
6. THE Chat_System SHALL preserve bot_memory for conversation context after booking completion

### Requirement 9: Property and Court Search Integration

**User Story:** As a customer, I want to search for sports facilities through the bot, so that I can find available courts matching my needs.

#### Acceptance Criteria

1. THE Chat_System SHALL integrate property_service.search_properties() as a tool
2. THE Chat_System SHALL integrate court_service.search_courts_by_sport_type() as a tool
3. THE Chat_System SHALL integrate court_service.get_availability() as a tool
4. WHEN user requests facility search, THE Indoor_Search node SHALL call property search tools
5. WHEN user specifies sport type, THE Indoor_Search node SHALL filter courts by sport type
6. THE Chat_System SHALL present search results in conversational format
7. WHEN presenting multiple options, THE Chat_System SHALL use list or button message types

### Requirement 10: Availability and Pricing Integration

**User Story:** As a customer, I want to see available time slots and pricing, so that I can choose a suitable booking time.

#### Acceptance Criteria

1. THE Chat_System SHALL integrate availability_service.check_blocked_slots() as a tool
2. THE Chat_System SHALL integrate pricing_service.get_pricing_for_time_slot() as a tool
3. WHEN user selects a date, THE Select_Time node SHALL retrieve available time slots
4. WHEN displaying time slots, THE Chat_System SHALL include pricing information
5. THE Chat_System SHALL exclude blocked time slots from available options
6. WHEN no slots are available, THE Chat_System SHALL suggest alternative dates

### Requirement 11: Async Service Layer

**User Story:** As a system architect, I want all chat services to be async, so that the system handles concurrent conversations efficiently.

#### Acceptance Criteria

1. THE Chat_System SHALL implement all service methods as async functions
2. THE Chat_System SHALL implement all repository methods as async functions
3. THE Chat_System SHALL use async database sessions for all Chat_Database operations
4. THE Chat_System SHALL use await for all I/O operations including LLM calls
5. THE Chat_System SHALL handle concurrent chat sessions without blocking

### Requirement 12: Structured Logging

**User Story:** As a developer, I want comprehensive structured logging, so that I can debug issues and monitor system behavior.

#### Acceptance Criteria

1. THE Chat_System SHALL log all incoming messages with chat_id, user_id, and owner_id
2. THE Chat_System SHALL log all LLM_Provider calls with token_usage
3. THE Chat_System SHALL log all node transitions in LangGraph_Agent with current state
4. THE Chat_System SHALL log all tool invocations with parameters and results
5. THE Chat_System SHALL log all errors with full context including chat_id and flow_state
6. THE Chat_System SHALL use structured logging format (JSON) for all log entries

### Requirement 13: Token Usage Tracking

**User Story:** As a product manager, I want to track LLM token usage, so that I can monitor costs and optimize prompts.

#### Acceptance Criteria

1. WHEN LLM_Provider generates a response, THE Chat_System SHALL calculate token_usage
2. THE Chat_System SHALL store token_usage in the message record
3. THE Chat_System SHALL log token_usage for each LLM call
4. THE Chat_System SHALL support querying total token usage by chat_id
5. THE Chat_System SHALL support querying total token usage by time period

### Requirement 14: Error Handling and Retry Safety

**User Story:** As a developer, I want robust error handling, so that temporary failures don't break conversations.

#### Acceptance Criteria

1. WHEN LLM_Provider call fails, THE Chat_System SHALL retry up to 3 times with exponential backoff
2. WHEN retry limit is exceeded, THE Chat_System SHALL return a fallback message to the user
3. WHEN database operation fails, THE Chat_System SHALL rollback the transaction
4. WHEN tool invocation fails, THE Chat_System SHALL log the error and inform the user
5. THE Chat_System SHALL preserve flow_state and bot_memory across failures
6. WHEN recovering from failure, THE Chat_System SHALL resume from last known good state

### Requirement 15: Transaction Management

**User Story:** As a developer, I want proper transaction handling, so that data remains consistent across failures.

#### Acceptance Criteria

1. THE Chat_System SHALL wrap each message processing operation in a database transaction
2. WHEN creating a Chat_Session and first message, THE Chat_System SHALL use a single transaction
3. WHEN updating flow_state and creating a message, THE Chat_System SHALL use a single transaction
4. WHEN a transaction fails, THE Chat_System SHALL rollback all changes
5. THE Chat_System SHALL commit transactions only after successful completion of all operations

### Requirement 16: Architecture and Code Organization

**User Story:** As a developer, I want clear code organization, so that the codebase is maintainable and follows existing patterns.

#### Acceptance Criteria

1. THE Chat_System SHALL place database models in app/models directory
2. THE Chat_System SHALL place Pydantic schemas in app/schemas directory
3. THE Chat_System SHALL place repository classes in app/repositories directory
4. THE Chat_System SHALL place service classes in app/services directory
5. THE Chat_System SHALL place API routers in app/routers directory
6. THE Chat_System SHALL place LangGraph graphs in app/agent/graphs directory
7. THE Chat_System SHALL place LangGraph nodes in app/agent/nodes directory
8. THE Chat_System SHALL place tool definitions in app/agent/tools directory
9. THE Chat_System SHALL place state definitions in app/agent/state directory
10. THE Chat_System SHALL place prompt templates in app/agent/prompts directory
11. THE Chat_System SHALL place runtime utilities in app/agent/runtime directory
12. THE Chat_System SHALL follow repository pattern for all data access
13. THE Chat_System SHALL follow service layer pattern for all business logic
14. THE Chat_System SHALL use FastAPI Depends for dependency injection

### Requirement 17: API Endpoints

**User Story:** As a frontend developer, I want RESTful API endpoints, so that I can integrate the chatbot into the application.

#### Acceptance Criteria

1. THE Chat_System SHALL expose POST /api/chat/message endpoint to receive user messages
2. THE POST /api/chat/message endpoint SHALL accept user_id, owner_id, and message content
3. THE POST /api/chat/message endpoint SHALL return bot response and chat_id
4. THE Chat_System SHALL expose GET /api/chat/history/{chat_id} endpoint to retrieve chat history
5. THE GET /api/chat/history endpoint SHALL return all messages in chronological order
6. THE Chat_System SHALL expose POST /api/chat/new endpoint to start a new chat session
7. THE Chat_System SHALL expose GET /api/chat/list endpoint to list user's chat sessions
8. THE GET /api/chat/list endpoint SHALL return chats ordered by last_message_at descending
9. THE Chat_System SHALL require authentication for all chat endpoints
10. THE Chat_System SHALL use make_response() utility for consistent API responses

### Requirement 18: Authentication and Authorization

**User Story:** As a security engineer, I want proper authentication and authorization, so that users can only access their own chats.

#### Acceptance Criteria

1. THE Chat_System SHALL use get_current_user dependency for authentication
2. THE Chat_System SHALL verify user_id matches authenticated user for all operations
3. THE Chat_System SHALL prevent users from accessing other users' chat sessions
4. THE Chat_System SHALL allow owners to view chats related to their properties
5. THE Chat_System SHALL allow admins to view all chats

### Requirement 19: Read-Only Access to Main Database

**User Story:** As a system architect, I want the bot to have read-only access to main database, so that it cannot corrupt existing data.

#### Acceptance Criteria

1. THE Chat_System SHALL access Main_Database only through existing service interfaces
2. THE Chat_System SHALL NOT directly modify Main_Database tables except through booking_service
3. THE Chat_System SHALL use existing repositories for read operations on properties, courts, and availability
4. WHEN creating bookings, THE Chat_System SHALL use booking_service.create_booking() method
5. THE Chat_System SHALL NOT implement custom SQL queries against Main_Database

### Requirement 20: Conversation Flow State Management

**User Story:** As a developer, I want explicit state management, so that conversation flows are predictable and debuggable.

#### Acceptance Criteria

1. THE Flow_State SHALL track current step in booking process
2. THE Flow_State SHALL store selected property_id when user chooses a property
3. THE Flow_State SHALL store selected service_id when user chooses a court
4. THE Flow_State SHALL store selected date when user chooses a date
5. THE Flow_State SHALL store selected time when user chooses a time slot
6. THE Flow_State SHALL store current intent (greeting, search, booking, faq)
7. WHEN transitioning between nodes, THE LangGraph_Agent SHALL update step field in Flow_State
8. WHEN booking is completed or cancelled, THE LangGraph_Agent SHALL clear booking-related fields from Flow_State

### Requirement 21: Natural Language Understanding

**User Story:** As a customer, I want the bot to understand my natural language requests, so that I don't need to use specific commands.

#### Acceptance Criteria

1. WHEN user sends a greeting, THE Intent_Detection node SHALL route to Greeting node
2. WHEN user asks about facilities or sports, THE Intent_Detection node SHALL route to Indoor_Search node
3. WHEN user expresses booking intent, THE Intent_Detection node SHALL route to Booking_Subgraph
4. WHEN user asks general questions, THE Intent_Detection node SHALL route to FAQ node
5. THE Intent_Detection node SHALL use LLM_Provider for intent classification when rule-based matching fails
6. THE Chat_System SHALL handle typos and informal language in user messages

### Requirement 22: Booking Confirmation Flow

**User Story:** As a customer, I want to review booking details before confirmation, so that I can verify everything is correct.

#### Acceptance Criteria

1. WHEN all booking details are collected, THE Confirm node SHALL present a summary to the user
2. THE booking summary SHALL include property name, court type, date, time, and price
3. THE Confirm node SHALL ask for explicit user confirmation
4. WHEN user confirms, THE Create_Pending_Booking node SHALL create the booking
5. WHEN user cancels, THE Booking_Subgraph SHALL clear flow_state and return to main menu
6. WHEN user requests changes, THE Booking_Subgraph SHALL return to the appropriate selection step

### Requirement 23: Message Type Support

**User Story:** As a customer, I want rich message types, so that I can interact with the bot using buttons and lists.

#### Acceptance Criteria

1. THE Chat_System SHALL support text message type for plain text responses
2. THE Chat_System SHALL support button message type for quick reply options
3. THE Chat_System SHALL support list message type for multiple choice selections
4. THE Chat_System SHALL support media message type for images and documents
5. WHEN presenting options, THE Chat_System SHALL use button or list message types
6. THE Chat_System SHALL store message_type in message metadata

### Requirement 24: Graceful Degradation

**User Story:** As a customer, I want the bot to remain functional during partial outages, so that I can still get basic assistance.

#### Acceptance Criteria

1. WHEN LLM_Provider is unavailable, THE Chat_System SHALL use rule-based fallback responses
2. WHEN Main_Database services are unavailable, THE Chat_System SHALL inform the user and suggest trying later
3. WHEN Chat_Database is unavailable, THE Chat_System SHALL return an error but not crash
4. THE Chat_System SHALL provide helpful error messages to users during degraded operation
5. THE Chat_System SHALL log all degraded operation events for monitoring

### Requirement 25: Performance Requirements

**User Story:** As a customer, I want fast bot responses, so that conversations feel natural and responsive.

#### Acceptance Criteria

1. WHEN user sends a message, THE Chat_System SHALL respond within 3 seconds for 95% of requests
2. THE Chat_System SHALL use database connection pooling for efficient resource usage
3. THE Chat_System SHALL cache frequently accessed data such as property lists
4. THE Chat_System SHALL limit LLM_Provider calls to necessary interactions only
5. THE Chat_System SHALL use streaming responses for long-form content when supported

### Requirement 26: Testing and Observability

**User Story:** As a developer, I want comprehensive observability, so that I can monitor system health and debug issues quickly.

#### Acceptance Criteria

1. THE Chat_System SHALL expose health check endpoint at /api/chat/health
2. THE health check SHALL verify Chat_Database connectivity
3. THE health check SHALL verify LLM_Provider availability
4. THE Chat_System SHALL track metrics: messages per minute, average response time, error rate
5. THE Chat_System SHALL support distributed tracing with correlation IDs across service calls

---

## Notes

This requirements document follows EARS patterns and INCOSE quality rules to ensure clarity, testability, and completeness. Each requirement is structured to be verifiable and implementation-independent, focusing on what the system shall do rather than how it will be implemented.

The architecture maintains clean separation between the async Chat_Database and sync Main_Database while enabling seamless integration through service interfaces. The LangGraph-based conversation flow provides structured, maintainable dialog management with explicit state tracking.

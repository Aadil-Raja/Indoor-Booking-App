# Requirements Document

## Introduction

This document specifies the requirements for refactoring the chatbot agent to use LLM-driven conversation flow with intelligent node routing and context-aware conversations. The refactoring eliminates rule-based transitions, removes FAQ ambiguities, and enables the LLM to make explicit routing decisions while maintaining conversation state through flow_state and bot_memory.

## Glossary

- **Chatbot_Agent**: The conversational AI system that handles user interactions for property bookings and information queries
- **LLM**: Large Language Model that processes user messages and makes routing decisions
- **Node**: A distinct conversation handler in the chatbot flow (greeting, information, booking)
- **Flow_State**: Temporary conversation state containing current intent, booking progress, and cached data
- **Bot_Memory**: Persistent storage for user preferences and inferred information across conversations
- **Node_Routing**: The process of determining which conversation handler should process the next user message
- **Booking_Flow**: Sequential process for creating a booking (property → court → date → time → confirm)
- **Information_Handler**: Node that processes non-booking informational queries
- **Greeting_Handler**: Node that initializes conversations and sets up context
- **Owner_Properties**: List of properties owned by the authenticated user
- **Context_Awareness**: Ability to skip redundant questions by checking existing flow_state data

## Requirements

### Requirement 1: Remove FAQ Node

**User Story:** As a system architect, I want to remove the FAQ node, so that the LLM can handle information queries without ambiguity between FAQ and information nodes.

#### Acceptance Criteria

1. THE Chatbot_Agent SHALL NOT include an FAQ node in the conversation flow
2. WHEN a user asks a frequently asked question, THE Information_Handler SHALL process the query
3. THE Chatbot_Agent SHALL route all informational queries to the Information_Handler regardless of whether they are FAQ-like

### Requirement 2: LLM-Driven Node Routing

**User Story:** As a developer, I want the LLM to explicitly decide the next node, so that conversation flow is intelligent and eliminates rule-based transitions.

#### Acceptance Criteria

1. THE LLM SHALL return a next_node field in its response containing one of: "greeting", "information", "booking_flow"
2. THE Chatbot_Agent SHALL NOT use rule-based logic to determine node transitions
3. WHEN the LLM processes a user message, THE LLM SHALL analyze the intent and explicitly select the appropriate next_node
4. THE Chatbot_Agent SHALL route the conversation to the node specified by the LLM's next_node decision
5. IF the LLM does not return a next_node value, THEN THE Chatbot_Agent SHALL default to the current node

### Requirement 3: Flow State Structure

**User Story:** As a developer, I want a structured flow_state to maintain conversation context, so that the chatbot can track booking progress and cached data across messages.

#### Acceptance Criteria

1. THE Flow_State SHALL contain a current_intent field with values: "booking", "information", or "greeting"
2. THE Flow_State SHALL contain optional property_id and property_name fields for the selected property
3. THE Flow_State SHALL contain optional court_id and court_name fields for the selected court
4. THE Flow_State SHALL contain an optional date field in YYYY-MM-DD format
5. THE Flow_State SHALL contain an optional time_slot field in HH:MM-HH:MM format
6. THE Flow_State SHALL contain a booking_step field with values: "property_selected", "court_selected", "date_selected", "time_selected", or "confirming"
7. THE Flow_State SHALL contain an owner_properties field for caching the list of owner's properties
8. THE Flow_State SHALL contain a context field for additional contextual information
9. THE Chatbot_Agent SHALL preserve Flow_State across messages within a conversation

### Requirement 4: Bot Memory Management

**User Story:** As a user, I want the chatbot to remember my preferences and inferred information, so that I don't have to repeat myself across conversations.

#### Acceptance Criteria

1. THE LLM SHALL store user preferences in Bot_Memory when they are expressed or inferred
2. THE LLM SHALL store inferred information in Bot_Memory for use in future messages
3. WHEN a user expresses a preference for morning time slots, THE LLM SHALL store this preference in Bot_Memory
4. WHEN the LLM infers user interest in a specific sport, THE LLM SHALL store this inference in Bot_Memory
5. THE LLM SHALL check Bot_Memory before asking questions that may have been answered previously
6. THE Chatbot_Agent SHALL persist Bot_Memory across conversation sessions

### Requirement 5: On-Demand Property Fetching

**User Story:** As a system architect, I want properties fetched only when needed, so that the chatbot doesn't perform unnecessary operations at conversation start.

#### Acceptance Criteria

1. THE Chatbot_Agent SHALL NOT fetch Owner_Properties at conversation initialization
2. WHEN the LLM determines a booking intent, THE Chatbot_Agent SHALL fetch Owner_Properties
3. WHEN Owner_Properties are fetched, THE Chatbot_Agent SHALL cache them in Flow_State
4. IF Owner_Properties exist in Flow_State, THEN THE Chatbot_Agent SHALL use the cached data instead of fetching again

### Requirement 6: Single Property Auto-Selection

**User Story:** As a user with one property, I want the chatbot to skip property selection, so that I can book faster without redundant questions.

#### Acceptance Criteria

1. WHEN Owner_Properties contains exactly one property, THE LLM SHALL automatically select it and store it in Flow_State
2. WHEN a property is auto-selected, THE LLM SHALL NOT ask the user to select a property
3. WHEN a user says "book it" and exactly one property exists in Owner_Properties, THE Booking_Flow SHALL skip property selection
4. THE LLM SHALL check Flow_State for existing property_id before asking property selection questions

### Requirement 7: Context-Aware Booking Step Skipping

**User Story:** As a user, I want the chatbot to skip steps where information already exists, so that I can complete bookings efficiently without answering redundant questions.

#### Acceptance Criteria

1. WHEN Flow_State contains a property_id, THE Booking_Flow SHALL skip the property selection step
2. WHEN Flow_State contains a court_id, THE Booking_Flow SHALL skip the court selection step
3. WHEN Flow_State contains a date, THE Booking_Flow SHALL skip the date selection step
4. WHEN Flow_State contains a time_slot, THE Booking_Flow SHALL skip the time slot selection step
5. THE LLM SHALL check Flow_State before asking any booking-related question
6. THE LLM SHALL proceed directly to the next incomplete booking step

### Requirement 8: Sequential Booking Flow

**User Story:** As a user, I want to follow a clear booking process, so that I can complete my reservation step by step.

#### Acceptance Criteria

1. THE Booking_Flow SHALL follow the sequence: property selection → court selection → date selection → time selection → confirmation
2. WHEN a booking step is completed, THE Booking_Flow SHALL update the booking_step field in Flow_State
3. THE Booking_Flow SHALL NOT allow skipping to confirmation without completing all required steps
4. WHEN all booking information is collected, THE Booking_Flow SHALL present a confirmation to the user
5. THE Booking_Flow SHALL validate each step's data before proceeding to the next step

### Requirement 9: Information Handler Rename and Functionality

**User Story:** As a developer, I want the indoor_search node renamed to information_handler, so that its purpose is clear and it handles all informational queries.

#### Acceptance Criteria

1. THE Chatbot_Agent SHALL rename the indoor_search node to Information_Handler
2. THE Information_Handler SHALL process all non-booking informational queries
3. THE Information_Handler SHALL use existing search tools to retrieve information
4. THE LLM SHALL decide when to use search tools versus answering from existing context
5. WHEN a user asks about property details, THE Information_Handler SHALL process the query
6. WHEN a user asks about court availability, THE Information_Handler SHALL process the query

### Requirement 10: Greeting Handler Initialization

**User Story:** As a system architect, I want the greeting handler to initialize conversation state, so that subsequent nodes have proper context.

#### Acceptance Criteria

1. THE Greeting_Handler SHALL initialize Flow_State when a conversation begins
2. THE Greeting_Handler SHALL initialize Bot_Memory when a conversation begins
3. THE Greeting_Handler SHALL set up conversation context for subsequent nodes
4. WHEN a user starts a conversation, THE Greeting_Handler SHALL be the first node to process the message
5. THE Greeting_Handler SHALL remain as a separate node in the conversation flow

### Requirement 11: LangGraph Architecture Compatibility

**User Story:** As a developer, I want the refactored system to work with existing LangGraph architecture, so that we don't need to rebuild the entire framework.

#### Acceptance Criteria

1. THE Chatbot_Agent SHALL maintain compatibility with the existing LangGraph state management
2. THE Chatbot_Agent SHALL maintain compatibility with existing tool integrations
3. THE Chatbot_Agent SHALL preserve conversation state across messages using LangGraph mechanisms
4. THE Chatbot_Agent SHALL use LangGraph's node routing capabilities for next_node transitions
5. THE refactored system SHALL NOT require changes to the LangGraph framework itself

### Requirement 12: Tool Compatibility

**User Story:** As a developer, I want to maintain compatibility with existing tools, so that we don't need to refactor tool implementations.

#### Acceptance Criteria

1. THE Chatbot_Agent SHALL use existing search tools without modification
2. THE Chatbot_Agent SHALL use existing booking tools without modification
3. THE Chatbot_Agent SHALL use existing property and court retrieval tools without modification
4. THE LLM SHALL continue to decide which tools to invoke based on user intent
5. THE tool invocation mechanism SHALL remain unchanged from the current implementation

### Requirement 13: LLM Response Structure

**User Story:** As a developer, I want a consistent LLM response structure, so that the system can reliably parse routing decisions and conversation state updates.

#### Acceptance Criteria

1. THE LLM SHALL return a structured response containing next_node, message, and state_updates fields
2. THE next_node field SHALL contain exactly one of: "greeting", "information", "booking_flow"
3. THE message field SHALL contain the text response to present to the user
4. THE state_updates field SHALL contain any updates to Flow_State or Bot_Memory
5. THE Chatbot_Agent SHALL parse the LLM response and apply state updates before routing to the next node

### Requirement 14: Single Court Auto-Selection

**User Story:** As a user with a property that has one court, I want the chatbot to skip court selection, so that I can book faster.

#### Acceptance Criteria

1. WHEN a property has exactly one court, THE LLM SHALL automatically select it and store it in Flow_State
2. WHEN a court is auto-selected, THE LLM SHALL NOT ask the user to select a court
3. THE LLM SHALL check the number of available courts before asking court selection questions
4. THE Booking_Flow SHALL proceed directly to date selection when a court is auto-selected

### Requirement 15: Conversation State Persistence

**User Story:** As a user, I want my conversation context preserved across messages, so that the chatbot maintains continuity throughout our interaction.

#### Acceptance Criteria

1. THE Chatbot_Agent SHALL preserve Flow_State across all messages in a conversation session
2. THE Chatbot_Agent SHALL preserve Bot_Memory across all conversation sessions for a user
3. WHEN a user sends a new message, THE Chatbot_Agent SHALL load the existing Flow_State
4. WHEN a conversation ends, THE Chatbot_Agent SHALL persist Bot_Memory for future sessions
5. THE Chatbot_Agent SHALL clear Flow_State when a booking is completed or cancelled

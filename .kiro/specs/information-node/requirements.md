# Requirements Document

## Introduction

The Information Node is a core component of the chatbot system that handles all information-related queries from users. It enables users to search for properties, view detailed information about properties and courts, check availability, view pricing, and access media content. The system uses LangGraph to manage conversation flow and routing between nodes, while each node (including the Information Node) uses LangChain agents with automatic tool calling to intelligently respond to user queries. All LLM interactions go through LangChain wrappers (ChatOpenAI from langchain-openai), not direct OpenAI API calls.

## Glossary

- **Chatbot System**: The conversational AI system built with LangGraph and LangChain that assists users with property and court information and bookings
- **LangGraph**: The framework that controls conversation flow and routing between nodes based on detected intent
- **LangChain**: The framework that handles all LLM interactions and automatic tool calling within each node
- **Information Node**: A LangGraph node that processes information-related queries using LangChain AgentExecutor
- **LangChain Agent**: An AI agent that automatically selects and executes tools based on user input without manual tool extraction
- **ChatOpenAI**: The LangChain wrapper for OpenAI LLM (from langchain-openai package) used instead of direct OpenAI API calls
- **Property**: A sports facility location that contains one or more courts
- **Court**: A specific playing area within a property (e.g., tennis court, basketball court)
- **Tool**: A LangChain StructuredTool that performs a specific operation (e.g., search properties, get court details)
- **flow_state**: A structured data store in the database that tracks multi-step processes and user selections
- **bot_memory**: A flexible data store in the database that maintains conversation context and user preferences
- **owner_profile_id**: The unique identifier for the property owner whose properties are being queried

## Requirements

### Requirement 1

**User Story:** As a customer, I want to search for properties by sport type and location, so that I can find suitable facilities for my needs

#### Acceptance Criteria

1. WHEN a user provides a search query with sport type or location, THE Information Node SHALL invoke the property search tool with the extracted parameters
2. WHEN the property search tool returns results, THE Information Node SHALL store the property IDs in bot_memory under context.last_search_results
3. WHEN multiple properties match the search criteria, THE Information Node SHALL present all matching properties with their basic information
4. WHEN no properties match the search criteria, THE Information Node SHALL inform the user that no results were found
5. WHEN the search is successful, THE Information Node SHALL update bot_memory with the search parameters under context.last_search_query

### Requirement 2

**User Story:** As a customer, I want to view detailed information about a specific property, so that I can learn about its amenities, location, and contact details

#### Acceptance Criteria

1. WHEN a user requests details for a specific property, THE Information Node SHALL invoke the get property details tool with the property identifier
2. WHEN property details are retrieved, THE Information Node SHALL present the property name, description, address, amenities, and contact information
3. WHEN a user references a property from previous search results, THE Information Node SHALL retrieve the property ID from bot_memory.context.last_search_results
4. WHEN property details include available courts, THE Information Node SHALL present the court information as part of the response
5. IF the property identifier is invalid or not found, THEN THE Information Node SHALL inform the user that the property does not exist

### Requirement 3

**User Story:** As a customer, I want to view information about specific courts within a property, so that I can understand the court specifications and features

#### Acceptance Criteria

1. WHEN a user requests court details for a specific property, THE Information Node SHALL invoke the get court details tool with the property identifier
2. WHEN court details are retrieved, THE Information Node SHALL present court names, types, surface materials, and specifications
3. WHEN multiple courts exist for a property, THE Information Node SHALL present information for all courts
4. WHEN a user asks about a specific court by name or type, THE Information Node SHALL filter and present only the relevant court information
5. IF no courts exist for the specified property, THEN THE Information Node SHALL inform the user that no courts are available

### Requirement 4

**User Story:** As a customer, I want to check court availability for specific dates and times, so that I can plan my booking

#### Acceptance Criteria

1. WHEN a user requests availability for a court and date, THE Information Node SHALL invoke the check availability tool with court ID and date parameters
2. WHEN availability data is retrieved, THE Information Node SHALL present available time slots for the specified date
3. WHEN a user requests availability without specifying a date, THE Information Node SHALL use the current date as the default
4. WHEN no availability exists for the requested date, THE Information Node SHALL inform the user and suggest alternative dates if available
5. WHEN availability is checked, THE Information Node SHALL store the court ID and date in bot_memory.context.last_availability_check

### Requirement 5

**User Story:** As a customer, I want to view pricing information for courts, so that I can understand the cost before making a booking

#### Acceptance Criteria

1. WHEN a user requests pricing for a court, THE Information Node SHALL invoke the get pricing tool with the court identifier
2. WHEN pricing data is retrieved, THE Information Node SHALL present hourly rates, peak and off-peak pricing, and any special rates
3. WHEN pricing varies by time of day or day of week, THE Information Node SHALL clearly indicate the different pricing tiers
4. WHEN a user asks about pricing for a specific time slot, THE Information Node SHALL provide the applicable rate for that time
5. IF no pricing is configured for a court, THEN THE Information Node SHALL inform the user to contact the property directly

### Requirement 6

**User Story:** As a customer, I want to view photos and media of properties and courts, so that I can see the facilities before booking

#### Acceptance Criteria

1. WHEN a user requests photos or media for a property or court, THE Information Node SHALL invoke the get media tool with the appropriate identifier
2. WHEN media is retrieved, THE Information Node SHALL present image URLs and descriptions in the response
3. WHEN multiple media items exist, THE Information Node SHALL present up to five media items with the option to view more
4. WHEN no media is available, THE Information Node SHALL inform the user that no photos are currently available
5. WHEN media is viewed, THE Information Node SHALL store the media request in bot_memory.context.last_media_viewed

### Requirement 7

**User Story:** As a customer, I want the chatbot to handle complex queries that require multiple pieces of information, so that I can get comprehensive answers in one interaction

#### Acceptance Criteria

1. WHEN a user asks a query requiring multiple tools, THE Information Node SHALL automatically invoke all necessary tools in sequence
2. WHEN multiple tools are executed, THE Information Node SHALL compose a coherent response combining all retrieved information
3. WHEN a user asks for property details and availability together, THE Information Node SHALL invoke both get property details and check availability tools
4. WHEN tool execution fails for one of multiple tools, THE Information Node SHALL provide partial information and indicate which data could not be retrieved
5. WHEN complex queries are processed, THE Information Node SHALL update bot_memory with all relevant context from the interaction

### Requirement 8

**User Story:** As a customer, I want the chatbot to remember my previous searches and preferences, so that I can have contextual follow-up conversations

#### Acceptance Criteria

1. WHEN a user refers to "that property" or "the last one", THE Information Node SHALL retrieve the reference from bot_memory.context.last_search_results
2. WHEN a user shows preference for a sport type, THE Information Node SHALL store it in bot_memory.user_preferences.preferred_sport
3. WHEN a user asks follow-up questions, THE Information Node SHALL use bot_memory context to understand the reference
4. WHEN bot_memory contains relevant context, THE Information Node SHALL include it in the agent prompt for better responses
5. WHEN a new search is performed, THE Information Node SHALL update bot_memory.context.last_search_results with new property IDs

### Requirement 9

**User Story:** As a system administrator, I want the Information Node to use LangChain agents exclusively with ChatOpenAI wrapper, so that tool calling is automatic and consistent with the architecture

#### Acceptance Criteria

1. THE Information Node SHALL use ChatOpenAI from langchain-openai as the LLM provider
2. THE Information Node SHALL NOT make direct OpenAI API calls
3. THE Information Node SHALL create a LangChain AgentExecutor with all information-related tools
4. THE Information Node SHALL NOT perform manual tool extraction or calling
5. THE Information Node SHALL allow the LangChain agent to automatically select which tools to invoke based on user input
6. THE Information Node SHALL wrap all custom tools as LangChain StructuredTool instances with proper schemas

### Requirement 10

**User Story:** As a system administrator, I want LangGraph to handle conversation flow routing, so that user messages are directed to the appropriate node based on intent

#### Acceptance Criteria

1. WHEN a user message is received, THE Chatbot System SHALL use LangGraph intent detection to classify the message
2. WHEN the intent is classified as information-related, THE LangGraph SHALL route the message to the Information Node
3. THE LangGraph SHALL manage the overall conversation state and flow between nodes
4. THE Information Node SHALL receive state from LangGraph containing user message, chat context, and bot memory
5. THE Information Node SHALL return updated state to LangGraph after processing

### Requirement 11

**User Story:** As a system administrator, I want the Information Node to properly manage state, so that conversation context is maintained correctly

#### Acceptance Criteria

1. THE Information Node SHALL read flow_state and bot_memory from the incoming state
2. THE Information Node SHALL update bot_memory.context with search results, tool usage, and relevant query information
3. THE Information Node SHALL update bot_memory.user_preferences when user preferences are identified
4. THE Information Node SHALL NOT store full conversation history in bot_memory
5. THE Information Node SHALL return updated state with response_content and response_type fields

### Requirement 12

**User Story:** As a developer, I want service functions to return appropriate data for chatbot tools, so that the Information Node can provide comprehensive responses

#### Acceptance Criteria

1. WHEN service functions need extension for chatbot use, THE System SHALL extend existing services in Backend/shared/services
2. WHEN service functions return data, THE System SHALL include all fields needed by the Information Node tools
3. THE System SHALL follow the existing pattern of using Backend/shared/services for core business logic
4. THE System SHALL use Backend/apps/management/app/services only when management-specific logic is required or being used in current files
5. THE System SHALL maintain consistency with existing service response formats using make_response utility

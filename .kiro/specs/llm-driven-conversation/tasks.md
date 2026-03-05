# Implementation Plan: LLM-Driven Conversation Flow

## Overview

This implementation refactors the chatbot from rule-based routing to LLM-driven conversation flow. The LLM makes explicit routing decisions at three levels (main graph, subgraph, and node), eliminating conditional logic. The system maintains state through flow_state (temporary) and bot_memory (persistent), enables context-aware conversations that skip redundant questions, and supports on-demand property fetching with auto-selection.

## Tasks

- [ ] 1. Update state models and LLM response structure
  - [ ] 1.1 Update ConversationState TypedDict with new fields
    - Add flow_state field with proper structure (current_intent, property_id, property_name, court_id, court_name, date, time_slot, booking_step, owner_properties, context)
    - Add bot_memory field with user_preferences and inferred_information structure
    - Add response_metadata field for structured data
    - Update existing fields to match design specification
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 4.1, 4.2_
  
  - [ ] 1.2 Create LLM response parser utility
    - Write parse_llm_response() function to extract next_node, message, and state_updates
    - Add validation for required fields (next_node, message, state_updates)
    - Add default handling for missing next_node (default to current node)
    - Add validation for next_node values ("greeting", "information", "booking")
    - _Requirements: 2.1, 2.5, 13.1, 13.2, 13.3, 13.4, 13.5_
  
  - [ ]* 1.3 Write property test for LLM response structure
    - **Property 1: LLM Response Structure Completeness**
    - **Validates: Requirements 2.1, 13.1, 13.3, 13.4**

- [ ] 2. Implement state management utilities
  - [ ] 2.1 Create flow_state management functions
    - Write initialize_flow_state() to create empty flow_state
    - Write validate_flow_state() to check structure validity
    - Write update_flow_state() to merge state updates
    - Write clear_flow_state() to reset after booking completion
    - _Requirements: 3.1, 3.9, 15.1, 15.5_
  
  - [ ] 2.2 Create bot_memory persistence functions
    - Write load_bot_memory() to retrieve from database
    - Write save_bot_memory() to persist to database
    - Write update_bot_memory() to merge memory updates
    - Add error handling for persistence failures
    - _Requirements: 4.1, 4.2, 4.6, 15.2, 15.4_
  
  - [ ]* 2.3 Write property test for flow_state persistence
    - **Property 4: Flow State Persistence Within Session**
    - **Validates: Requirements 3.9**
  
  - [ ]* 2.4 Write unit tests for state management
    - Test flow_state initialization and validation
    - Test bot_memory persistence and loading
    - Test state update merging logic
    - Test error handling for corrupted state

- [ ] 3. Refactor greeting handler with LLM-driven routing
  - [ ] 3.1 Update greeting_handler to return structured LLM response
    - Modify greeting prompt to request next_node decision
    - Parse LLM response to extract next_node, message, state_updates
    - Initialize flow_state with current_intent
    - Initialize bot_memory if not exists
    - Return structured response with routing decision
    - _Requirements: 2.1, 2.3, 2.4, 10.1, 10.2, 10.3, 10.4_
  
  - [ ] 3.2 Update greeting handler to use business_name personalization
    - Fetch owner_profile attributes from owner_profile_id
    - Extract business_name from owner_profile
    - Update greeting prompt to include: "Hello, I am {business_name}'s assistant. I can show you indoors and courts where you can play futsal, cricket, etc."
    - _Requirements: 10.1, 10.3_
  
  - [ ]* 3.3 Write unit test for greeting handler
    - Test greeting handler is first node (Requirement 10.4)
    - Test flow_state and bot_memory initialization
    - Test personalized greeting with business_name

- [ ] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Refactor information handler with LangChain agent
  - [ ] 5.1 Rename indoor_search node to information_handler
    - Update node name in main_graph.py
    - Update all references to indoor_search
    - Update routing logic to use "information" consistently
    - _Requirements: 9.1, 9.2_
  
  - [ ] 5.2 Update information_handler to use LangChain ReAct agent
    - Configure create_react_agent with all information tools (search_properties, get_property_details, search_courts, get_court_details, get_availability, get_pricing)
    - Update information prompt to guide LLM on tool usage
    - Add fuzzy search logic for court names and sports (e.g., "football" → "futsal" with confirmation)
    - Return structured response with next_node decision
    - _Requirements: 9.2, 9.3, 9.4, 9.5, 9.6_
  
  - [ ] 5.3 Update information handler prompts for personalization
    - Update prompts to reference business_name from owner_profile
    - Add context that bot only shows owner's properties
    - Add fuzzy match confirmation prompts
    - _Requirements: 9.2, 9.5, 9.6_
  
  - [ ]* 5.4 Write unit tests for information handler
    - Test property details query handled by information handler (Requirement 9.5)
    - Test court availability query handled by information handler (Requirement 9.6)
    - Test fuzzy search matching and confirmation
    - Test personalized responses with business_name

- [ ] 6. Remove FAQ node from main graph
  - [ ] 6.1 Remove faq_handler node from main_graph.py
    - Remove faq node from graph
    - Remove faq routing from conditional edges
    - Update unknown intent to route to information handler
    - _Requirements: 1.1, 1.2, 1.3_
  
  - [ ]* 6.2 Write unit test for FAQ removal
    - Test that FAQ-like queries route to information handler
    - Test that unknown intents route to information handler

- [ ] 7. Implement on-demand property fetching
  - [ ] 7.1 Remove property fetching from conversation initialization
    - Remove get_owner_properties call from receive_message or load_chat
    - Verify owner_properties is not in initial flow_state
    - _Requirements: 5.1_
  
  - [ ] 7.2 Add property fetching to booking subgraph entry
    - Check if owner_properties exists in flow_state
    - If not, fetch using get_owner_properties_tool
    - Cache fetched properties in flow_state.owner_properties
    - _Requirements: 5.2, 5.3, 5.4_
  
  - [ ]* 7.3 Write property test for on-demand fetching
    - **Property 8: On-Demand Property Fetching**
    - **Validates: Requirements 5.1, 5.2**
  
  - [ ]* 7.4 Write property test for property caching
    - **Property 9: Property Caching in Flow State**
    - **Validates: Requirements 5.3, 5.4**
  
  - [ ]* 7.5 Write unit test for property fetching
    - Test properties not fetched at initialization (Requirement 5.1)
    - Test properties fetched when booking starts
    - Test cached properties reused

- [ ] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Implement property selection with auto-selection
  - [ ] 9.1 Create select_property_node in booking subgraph
    - Check if property_id exists in flow_state (skip if exists)
    - Fetch owner_properties if not cached
    - Handle 0 properties: return error message
    - Handle 1 property: auto-select and store in flow_state (property_id, property_name)
    - Handle multiple properties: present list and wait for selection
    - Update booking_step to "property_selected" when complete
    - Return next_node decision
    - _Requirements: 5.2, 5.3, 6.1, 6.2, 6.4, 7.1, 8.2_
  
  - [ ]* 9.2 Write property test for single property auto-selection
    - **Property 10: Single Property Auto-Selection**
    - **Validates: Requirements 6.1, 6.2, 6.4**
  
  - [ ]* 9.3 Write unit test for property selection
    - Test "book it" with single property skips selection (Requirement 6.3)
    - Test multiple properties show selection list
    - Test zero properties show error

- [ ] 10. Implement court selection with auto-selection
  - [ ] 10.1 Create select_court_node in booking subgraph
    - Check if court_id exists in flow_state (skip if exists)
    - Fetch courts for selected property using get_property_courts_tool
    - Handle 0 courts: return error message
    - Handle 1 court: auto-select and store in flow_state (court_id, court_name)
    - Handle multiple courts: present list and wait for selection
    - Update booking_step to "court_selected" when complete
    - Return next_node decision
    - _Requirements: 7.2, 8.2, 14.1, 14.2, 14.3_
  
  - [ ]* 10.2 Write property test for single court auto-selection
    - **Property 11: Single Court Auto-Selection**
    - **Validates: Requirements 14.1, 14.2, 14.3**
  
  - [ ]* 10.3 Write unit tests for court selection
    - Test single court auto-selection
    - Test multiple courts show selection list
    - Test zero courts show error

- [ ] 11. Implement date selection with LLM parsing
  - [ ] 11.1 Create select_date_node in booking subgraph
    - Check if date exists in flow_state (skip if exists)
    - Use LLM to parse date from user message (natural language → YYYY-MM-DD)
    - Validate date format and future date
    - If date parsed: store in flow_state and update booking_step to "date_selected"
    - If date not parsed: ask user for date
    - Return next_node decision
    - _Requirements: 7.3, 8.2, 8.5_
  
  - [ ]* 11.2 Write unit tests for date selection
    - Test date parsing from natural language
    - Test date validation (format, future date)
    - Test date skipping when exists in flow_state

- [ ] 12. Implement time selection with availability checking
  - [ ] 12.1 Create select_time_node in booking subgraph
    - Check if time_slot exists in flow_state (skip if exists)
    - Fetch available slots using get_availability_tool (court_id, date)
    - Use LLM to parse time from user message or present available slots
    - If slot is booked, show available slots for that day
    - If full day is booked, show nearest available date
    - Validate time_slot format (HH:MM-HH:MM)
    - If time parsed: store in flow_state and update booking_step to "time_selected"
    - If time not parsed: present available slots
    - Return next_node decision
    - _Requirements: 7.4, 8.2, 8.5_
  
  - [ ]* 12.2 Write unit tests for time selection
    - Test time parsing from natural language
    - Test available slots presentation
    - Test booked slot handling (show alternatives)
    - Test full day handling (show nearest date)
    - Test time skipping when exists in flow_state

- [ ] 13. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Implement booking confirmation and creation
  - [ ] 14.1 Create confirm_booking_node in booking subgraph
    - Build booking summary (property, court, date, time)
    - Fetch pricing using get_pricing_tool
    - Use LLM to check for user confirmation
    - If confirmed: update booking_step to "confirming" and route to create_booking
    - If user wants to modify: route back to appropriate selection node
    - If cancelled: clear flow_state and end
    - Return next_node decision
    - _Requirements: 8.1, 8.3, 8.4_
  
  - [ ] 14.2 Create create_booking_node in booking subgraph
    - Parse time_slot into start_time and end_time
    - Call create_booking_tool with all booking data
    - If success: clear flow_state and return confirmation message
    - If failure: return error and route back to time_selection
    - _Requirements: 8.5, 15.5_
  
  - [ ]* 14.3 Write unit tests for confirmation and creation
    - Test booking confirmation flow
    - Test booking modification flow
    - Test booking cancellation
    - Test successful booking creation
    - Test failed booking creation
    - Test flow_state cleared after completion

- [ ] 15. Implement context-aware step skipping
  - [ ] 15.1 Add flow_state checking to all booking nodes
    - Update each node to check flow_state before asking questions
    - Skip to next incomplete step if data exists
    - Ensure sequential ordering (property → court → date → time → confirm)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_
  
  - [ ]* 15.2 Write property test for booking step skipping
    - **Property 12: Booking Step Skipping with Existing Data**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
  
  - [ ]* 15.3 Write property test for sequential ordering
    - **Property 14: Booking Flow Sequential Ordering**
    - **Validates: Requirements 8.1, 8.3, 8.4**
  
  - [ ]* 15.4 Write property test for booking step state updates
    - **Property 15: Booking Step State Updates**
    - **Validates: Requirements 8.2**

- [ ] 16. Implement reversibility in information subgraph
  - [ ] 16.1 Update information handler to support attribute changes
    - Add logic to detect when user wants to change property/court/date/slot
    - Update only the changed attribute in flow_state
    - Continue from where left off (don't restart entire flow)
    - Maintain other attributes unchanged
    - _Requirements: 7.5, 7.6_
  
  - [ ]* 16.2 Write unit tests for reversibility
    - Test changing property keeps court/date/slot
    - Test changing court keeps property/date/slot
    - Test changing date keeps property/court/slot
    - Test changing slot keeps property/court/date

- [ ] 17. Update main graph routing to use LLM decisions
  - [ ] 17.1 Remove rule-based routing from main_graph.py
    - Remove route_by_intent function
    - Remove conditional_edges based on intent
    - Update intent_detection to return next_node from LLM
    - Add routing based on LLM's next_node decision
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [ ] 17.2 Update all nodes to apply state_updates before routing
    - Extract state_updates from LLM response
    - Apply updates to flow_state and bot_memory
    - Route to next_node after updates applied
    - _Requirements: 13.5_
  
  - [ ]* 17.3 Write property test for routing follows LLM decision
    - **Property 2: Routing Follows LLM Decision**
    - **Validates: Requirements 1.2, 2.4**
  
  - [ ]* 17.4 Write property test for state updates applied before routing
    - **Property 17: State Updates Applied Before Routing**
    - **Validates: Requirements 13.5**

- [ ] 18. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 19. Implement bot_memory preference management
  - [ ] 19.1 Add preference extraction to LLM prompts
    - Update all node prompts to identify and extract user preferences
    - Store preferences in bot_memory.user_preferences (preferred_time, preferred_sport, preferred_property, preferred_court)
    - Store inferred information in bot_memory.inferred_information
    - _Requirements: 4.1, 4.2, 4.3, 4.4_
  
  - [ ] 19.2 Add bot_memory checking to prevent redundant questions
    - Update all node prompts to check bot_memory before asking questions
    - Skip questions if bot_memory contains answers
    - Use preferences to pre-fill or suggest options
    - _Requirements: 4.5_
  
  - [ ]* 19.3 Write property test for bot_memory preference storage
    - **Property 5: Bot Memory Preference Storage**
    - **Validates: Requirements 4.1, 4.2**
  
  - [ ]* 19.4 Write property test for bot_memory prevents redundant questions
    - **Property 6: Bot Memory Prevents Redundant Questions**
    - **Validates: Requirements 4.5**
  
  - [ ]* 19.5 Write property test for bot_memory persistence across sessions
    - **Property 7: Bot Memory Persistence Across Sessions**
    - **Validates: Requirements 4.6**
  
  - [ ]* 19.6 Write unit test for preference storage
    - Test morning preference stored in bot_memory (Requirement 4.3)
    - Test sport preference storage
    - Test property preference storage

- [ ] 20. Add comprehensive error handling
  - [ ] 20.1 Add LLM response error handling
    - Handle missing next_node (default to current node)
    - Handle invalid next_node (default to greeting)
    - Handle LLM API failures (return error message)
    - Handle malformed response structure
    - Add logging for all error cases
    - _Requirements: 2.5_
  
  - [ ] 20.2 Add state management error handling
    - Handle flow_state corruption (reinitialize)
    - Handle bot_memory persistence failures (log and continue)
    - Handle state deserialization errors
    - Add validation and recovery logic
  
  - [ ] 20.3 Add tool invocation error handling
    - Handle property fetch failures
    - Handle court fetch failures
    - Handle availability check failures
    - Handle booking creation failures
    - Return user-friendly error messages
  
  - [ ] 20.4 Add validation error handling
    - Handle invalid date format
    - Handle invalid time slot format
    - Handle missing required booking data
    - Handle conflicting booking data
  
  - [ ]* 20.5 Write unit tests for error handling
    - Test missing next_node defaults to current node (Requirement 2.5)
    - Test invalid next_node defaults to greeting
    - Test LLM API failure handling
    - Test flow_state corruption recovery
    - Test tool failure handling
    - Test validation error messages

- [ ] 21. Implement remaining correctness properties as tests
  - [ ]* 21.1 Write property test for flow_state structure validity
    - **Property 3: Flow State Structure Validity**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8**
  
  - [ ]* 21.2 Write property test for booking flow proceeds to next incomplete step
    - **Property 13: Booking Flow Proceeds to Next Incomplete Step**
    - **Validates: Requirements 7.6**
  
  - [ ]* 21.3 Write property test for booking step validation
    - **Property 16: Booking Step Validation**
    - **Validates: Requirements 8.5**
  
  - [ ]* 21.4 Write property test for flow_state cleared after completion
    - **Property 18: Flow State Cleared After Booking Completion**
    - **Validates: Requirements 15.5**

- [ ] 22. Final checkpoint and integration verification
  - [ ] 22.1 Run all property tests (minimum 100 iterations each)
    - Verify all 18 correctness properties pass
    - Check test coverage for all requirements
  
  - [ ] 22.2 Run all unit tests
    - Verify 90%+ code coverage
    - Check all edge cases covered
  
  - [ ] 22.3 Verify LangGraph compatibility
    - Test state flows correctly through nodes
    - Test all tools work without modification
    - Test flow_state and bot_memory persistence
    - Test LLM provider integration
  
  - [ ] 22.4 Final checkpoint - Ensure all tests pass
    - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties using hypothesis library (100+ iterations)
- Unit tests validate specific examples and edge cases
- Checkpoints ensure incremental validation at reasonable breaks
- All code examples use Python (as specified in design document)
- The implementation maintains compatibility with existing LangGraph architecture and tools
- Bot personality is personalized using business_name from owner_profile
- Fuzzy search enables flexible user queries with confirmation
- Reversibility allows users to change any attribute without restarting the flow

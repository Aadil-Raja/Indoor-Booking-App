# Implementation Plan

- [x] 1. Create LangChain LLM wrapper utility









  - Create `Backend/apps/chatbot/app/services/llm/langchain_wrapper.py`
  - Implement create_langchain_llm() function that creates ChatOpenAI instance
  - Accept llm_provider parameter and extract api_key, model, temperature
  - Import ChatOpenAI from langchain_openai package
  - Return configured ChatOpenAI instance
  - This will be used by ALL nodes instead of direct OpenAI calls
  - _Requirements: 9.1, 9.2_
-

- [x] 2. Convert greeting node to use LangChain










  - Update `Backend/apps/chatbot/app/agent/nodes/greeting.py`
  - Remove direct LLM calls if any
  - For new user greeting with properties, keep current implementation (no LLM needed)
  - For returning user greeting, keep current implementation (no LLM needed)
  - Greeting node doesn't need tools, so tools parameter should be None
  - Ensure node follows standard pattern: extract state, process, return state
  - _Requirements: 9.2, 9.3_

- [x] 3. Convert intent_detection node to use LangChain











  - Update `Backend/apps/chatbot/app/agent/nodes/intent_detection.py`
  - Keep rule-based classification as primary method
  - For LLM fallback, use ChatOpenAI from create_langchain_llm()
  - Replace llm_provider.generate() with ChatOpenAI.ainvoke()
  - Create simple prompt for intent classification
  - No tools needed for intent detection (tools=None)
  - _Requirements: 9.1, 9.2, 9.3_

- [x] 4. Replace indoor_search node with information node





  - The indoor_search node will be replaced by the new information_node
  - Information node handles all search functionality PLUS availability, pricing, media
  - Keep indoor_search.py file for reference but it will not be used in the graph
  - The new information_node (task 9) will handle all these queries using LangChain agent
  - _Requirements: 9.1, 9.2, 9.4_

- [x] 5. Create information tools module





  - Create `Backend/apps/chatbot/app/agent/tools/information_tools.py`
  - Implement search_properties_tool that calls public_service.search_properties()
  - Implement get_property_details_tool that calls public_service.get_property_details()
  - Implement get_court_details_tool that calls public_service.get_court_details()
  - Implement get_court_availability_tool that calls public_service.get_available_slots()
  - Implement get_court_pricing_tool that calls public_service.get_court_pricing_for_date()
  - Implement get_property_media_tool that extracts media from property details
  - Implement get_court_media_tool that extracts media from court details
  - All tools should use async/await and call_sync_service bridge
  - All tools should handle errors gracefully and return empty results on failure
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 9.6_

- [x] 6. Create LangChain tool converter





  - Create `Backend/apps/chatbot/app/agent/tools/langchain_converter.py`
  - Define Pydantic schemas for each tool (SearchPropertiesInput, GetPropertyDetailsInput, etc.)
  - Implement create_langchain_tools() function that converts tool registry to LangChain StructuredTools
  - Each tool should have proper name, description, and args_schema
  - Use StructuredTool.from_function() with coroutine parameter for async tools
  - _Requirements: 9.1, 9.6_

- [x] 7. Create information prompt templates









  - Create `Backend/apps/chatbot/app/agent/prompts/information_prompts.py`
  - Define SYSTEM_TEMPLATE with instructions for information assistant
  - Implement create_information_prompt() that builds ChatPromptTemplate
  - Extract context from bot_memory (last_search_results, user_preferences)
  - Include MessagesPlaceholder for chat_history and agent_scratchpad
  - Use prompt.partial() to inject owner_profile_id and context
  - _Requirements: 8.4, 10.1_

- [x] 8. Create bot memory manager





  - Create `Backend/apps/chatbot/app/agent/state/memory_manager.py`
  - Implement update_bot_memory() function
  - Extract intermediate_steps from agent result to see which tools were called
  - Store last_search_results (property IDs) when search_properties is called
  - Store last_search_params when search is performed
  - Update user_preferences.preferred_sport when sport_type is searched
  - Store last_viewed_property and last_viewed_court
  - Store last_availability_check with court_id and date
  - _Requirements: 1.2, 1.5, 5.5, 8.1, 8.2, 8.3, 11.2, 11.3_

- [x] 9. Implement information node handler





  - Create `Backend/apps/chatbot/app/agent/nodes/information.py`
  - Implement information_node() async function
  - Extract state: user_message, owner_profile_id, bot_memory, flow_state
  - Get information tools from TOOL_REGISTRY
  - Convert tools to LangChain format using create_langchain_tools()
  - Create ChatOpenAI LLM using create_langchain_llm()
  - Create prompt using create_information_prompt()
  - Create agent using create_openai_functions_agent()
  - Create AgentExecutor with agent and tools
  - Execute agent with ainvoke() passing user_message
  - Update state with response_content from agent result
  - Update bot_memory using update_bot_memory()
  - Handle exceptions and return error message on failure
  - _Requirements: 1.1-1.5, 2.1-2.5, 3.1-3.5, 4.1-4.5, 5.1-5.5, 6.1-6.5, 7.1-7.5, 8.1-8.5, 9.1-9.6, 10.1-10.5, 11.1-11.5_

- [x] 10. Register information tools in tool registry



















  - Update `Backend/apps/chatbot/app/agent/tools/__init__.py`
  - Import information tools from information_tools module
  - Add all information tools to TOOL_REGISTRY dictionary
  - Ensure tool names match what's used in create_langchain_tools()
  - _Requirements: 9.6_

- [x] 11. Register information node in LangGraph




  - Update `Backend/apps/chatbot/app/agent/graph.py` (or main graph file)
  - Import information_node from nodes.information
  - Add information_node to the graph
  - REPLACE indoor_search_handler with information_node in routing
  - Add routing from intent_detection to information_node when intent is "information" or "search"
  - Add routing from information_node to END
  - Remove indoor_search_handler from graph (replaced by information_node)
  - _Requirements: 10.1, 10.2, 10.3_

- [x] 12. Update intent detection patterns





  - Update `Backend/apps/chatbot/app/agent/nodes/intent_detection.py`
  - Ensure SEARCH_PATTERNS include information-related queries
  - Add patterns for availability queries ("when is available", "check availability")
  - Add patterns for pricing queries ("how much", "what's the price")
  - Add patterns for media queries ("show me photos", "pictures of")
  - Ensure "information" or "search" intent routes to information_node
  - _Requirements: 10.2_

- [x] 13. Add langchain dependencies





  - Update `Backend/requirements.txt`
  - Add langchain>=0.1.0
  - Add langchain-openai>=0.0.5
  - Run pip install -r requirements.txt to install dependencies
  - _Requirements: 9.1_

- [x] 14. Convert booking nodes to use LangChain agents





  - Update booking nodes to use LangChain agents instead of manual flow control
  - Each booking step node should use LangChain agent with appropriate tools
  - Create booking-specific prompt templates for each step
  - Use create_langchain_llm() for LLM instances
  - Maintain flow_state management for booking progress
  - _Requirements: 9.1, 9.2_


- [x] 14.1 Convert select_property booking node

  - Update `Backend/apps/chatbot/app/agent/nodes/booking/select_property.py`
  - Create LangChain agent with get_owner_properties tool
  - Create prompt template for property selection assistant
  - Agent should present properties and extract user selection
  - Update flow_state with selected property_id and property_name
  - _Requirements: 9.1, 9.2_


- [x] 14.2 Convert select_service booking node

  - Update `Backend/apps/chatbot/app/agent/nodes/booking/select_service.py`
  - Create LangChain agent with get_property_courts tool
  - Create prompt template for service/court selection assistant
  - Agent should present courts for selected property and extract user selection
  - Update flow_state with selected service_id and service_name
  - _Requirements: 9.1, 9.2_


- [x] 14.3 Convert select_date booking node

  - Update `Backend/apps/chatbot/app/agent/nodes/booking/select_date.py`
  - Create LangChain agent (no tools needed, just date parsing)
  - Create prompt template for date selection assistant
  - Agent should help user select a date and validate it
  - Update flow_state with selected date
  - _Requirements: 9.1, 9.2, 9.3_


- [x] 14.4 Convert select_time booking node

  - Update `Backend/apps/chatbot/app/agent/nodes/booking/select_time.py`
  - Create LangChain agent with get_available_slots tool
  - Create prompt template for time selection assistant
  - Agent should present available time slots and extract user selection
  - Update flow_state with selected start_time, end_time, price
  - _Requirements: 9.1, 9.2_


- [x] 14.5 Convert confirm_booking node

  - Update `Backend/apps/chatbot/app/agent/nodes/booking/confirm_booking.py`
  - Create LangChain agent (no tools needed, just confirmation)
  - Create prompt template for booking confirmation assistant
  - Agent should present booking summary and get user confirmation
  - Update flow_state step based on user response (confirmed/cancelled/modify)
  - _Requirements: 9.1, 9.2, 9.3_


- [x] 14.6 Keep create_pending_booking node as-is

  - The create_pending_booking node doesn't need LangChain agent
  - It just calls the create_booking tool and formats response
  - Keep current implementation
  - _Requirements: 9.1_

- [x] 15. Write unit tests for information tools






  - Create `Backend/apps/chatbot/tests/test_information_tools.py`
  - Test search_properties_tool with valid inputs
  - Test get_property_details_tool with valid property_id
  - Test get_court_details_tool with valid court_id
  - Test get_court_availability_tool with valid court_id and date
  - Test get_court_pricing_tool with valid court_id and date
  - Test error handling for invalid IDs
  - Mock service calls using pytest fixtures
  - _Requirements: 1.1-1.5, 2.1-2.5, 3.1-3.5, 4.1-4.5, 5.1-5.5, 6.1-6.5_

- [x] 16. Write unit tests for memory manager






  - Create `Backend/apps/chatbot/tests/test_memory_manager.py`
  - Test update_bot_memory() with search_properties result
  - Test preference extraction from search parameters
  - Test last_viewed_property storage
  - Test last_availability_check storage
  - Verify bot_memory structure is correct
  - _Requirements: 8.1-8.5, 11.2, 11.3_

- [x] 17. Write integration tests for information node





  - Create `Backend/apps/chatbot/tests/integration/test_information_node.py`
  - Test simple search query flow
  - Test property details query flow
  - Test court availability query flow
  - Test complex multi-tool query
  - Test context reference using bot_memory
  - Mock LLM responses for predictable testing
  - _Requirements: 1.1-1.5, 7.1-7.5, 8.1-8.5_

- [x] 18. Write integration tests for booking nodes






  - Create `Backend/apps/chatbot/tests/integration/test_booking_nodes.py`
  - Test complete booking flow from property selection to creation
  - Test back navigation between steps
  - Test cancellation at different steps
  - Test modification requests
  - Mock LLM responses and tool calls
  - _Requirements: Booking requirements_

- [ ] 19. Manual testing with ChatbotTest UI
  - Start chatbot service: `cd Backend/apps/chatbot && python -m app.main`
  - Open ChatbotTest UI in browser
  - Test Information Node queries:
    - "Show me tennis courts"
    - "Tell me about property 6"
    - "What courts are available at property 6?"
    - "Check availability for court 23 on March 10"
    - "What's the pricing for court 23?"
    - "Show me photos of property 6"
    - "Show me tennis courts" then "Tell me more about the first one"
  - Test Booking flow:
    - "I want to book a tennis court"
    - Follow through complete booking flow
    - Test "back" navigation
    - Test "cancel" at different steps
    - Test "change property" during confirmation
  - Verify responses are accurate and contextual
  - Verify bot_memory and flow_state are updated correctly
  - _Requirements: All_

# Information Node Design Document

## Overview

The Information Node is a LangGraph node that handles all information-related queries in the chatbot system. It uses LangChain AgentExecutor with automatic tool calling to intelligently respond to user queries about properties, courts, availability, pricing, and media. The node integrates with existing Backend/shared/services through custom tools wrapped as LangChain StructuredTools.

## Architecture

### High-Level Flow

```
User Message
    ↓
LangGraph: intent_detection (classifies as "information")
    ↓
LangGraph: Routes to information_node
    ↓
Information Node:
  1. Extract state (user_message, bot_memory, flow_state)
  2. Create LangChain tools from TOOL_REGISTRY
  3. Build context-aware prompt with bot_memory
  4. Create ChatOpenAI LLM (langchain-openai)
  5. Create LangChain agent with tools
  6. Execute AgentExecutor (automatic tool calling)
  7. Update bot_memory with results
  8. Return updated state
    ↓
LangGraph: Continue flow or END
```

### Node Pattern

The Information Node follows the standard LangGraph + LangChain node pattern:

```python
async def information_node(
    state: ConversationState,
    llm_provider: LLMProvider
) -> ConversationState:
    """
    Handle information queries using LangChain agent with automatic tool calling.
    """
    # 1. Extract state
    user_message = state["user_message"]
    owner_profile_id = state["owner_profile_id"]
    bot_memory = state.get("bot_memory", {})
    flow_state = state.get("flow_state", {})
    
    # 2. Convert tools to LangChain format
    langchain_tools = create_langchain_tools(TOOL_REGISTRY)
    
    # 3. Create LangChain LLM (ChatOpenAI wrapper)
    llm = ChatOpenAI(
        model="gpt-4",
        api_key=llm_provider.api_key,
        temperature=0.7
    )
    
    # 4. Build context-aware prompt
    prompt = create_information_prompt(
        owner_profile_id=owner_profile_id,
        bot_memory=bot_memory
    )
    
    # 5. Create agent
    agent = create_openai_functions_agent(llm, langchain_tools, prompt)
    
    # 6. Execute agent (automatic tool calling)
    agent_executor = AgentExecutor(
        agent=agent,
        tools=langchain_tools,
        verbose=True
    )
    result = await agent_executor.ainvoke({"input": user_message})
    
    # 7. Update state
    state["response_content"] = result["output"]
    state["response_type"] = "text"
    state["response_metadata"] = {}
    
    # 8. Update bot_memory
    bot_memory = update_bot_memory(bot_memory, result)
    state["bot_memory"] = bot_memory
    
    return state
```

## Components and Interfaces

### 1. Information Node Handler

**File**: `Backend/apps/chatbot/app/agent/nodes/information.py`

**Purpose**: Main node handler that processes information queries

**Interface**:
```python
async def information_node(
    state: ConversationState,
    llm_provider: LLMProvider
) -> ConversationState
```

**Responsibilities**:
- Extract state and context
- Create LangChain tools
- Build context-aware prompts
- Execute LangChain agent
- Update bot_memory with results
- Return updated state

### 2. Information Tools

**File**: `Backend/apps/chatbot/app/agent/tools/information_tools.py`

**Purpose**: Wrap service functions as LangChain StructuredTools

**Tools**:

#### search_properties_tool
```python
async def search_properties_tool(
    owner_profile_id: int,
    city: Optional[str] = None,
    sport_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = 10
) -> List[Dict[str, Any]]
```
- Calls `public_service.search_properties()`
- Returns list of properties with basic info

#### get_property_details_tool
```python
async def get_property_details_tool(
    property_id: int
) -> Optional[Dict[str, Any]]
```
- Calls `public_service.get_property_details()`
- Returns comprehensive property info with courts and media

#### get_court_details_tool
```python
async def get_court_details_tool(
    court_id: int
) -> Optional[Dict[str, Any]]
```
- Calls `public_service.get_court_details()`
- Returns court details with pricing and media

#### get_court_availability_tool
```python
async def get_court_availability_tool(
    court_id: int,
    date: str  # ISO format YYYY-MM-DD
) -> Dict[str, Any]
```
- Calls `public_service.get_available_slots()`
- Returns available time slots for the date

#### get_court_pricing_tool
```python
async def get_court_pricing_tool(
    court_id: int,
    date: str  # ISO format YYYY-MM-DD
) -> Dict[str, Any]
```
- Calls `public_service.get_court_pricing_for_date()`
- Returns pricing rules for the date

#### get_property_media_tool
```python
async def get_property_media_tool(
    property_id: int,
    limit: int = 5
) -> List[Dict[str, Any]]
```
- Extracts media from `get_property_details_tool` response
- Returns property media (photos/videos)

#### get_court_media_tool
```python
async def get_court_media_tool(
    court_id: int,
    limit: int = 5
) -> List[Dict[str, Any]]
```
- Extracts media from `get_court_details_tool` response
- Returns court media (photos/videos)

### 3. Tool Converter

**File**: `Backend/apps/chatbot/app/agent/tools/langchain_converter.py`

**Purpose**: Convert custom async tools to LangChain StructuredTool format

**Interface**:
```python
def create_langchain_tools(
    tool_registry: Dict[str, Callable]
) -> List[StructuredTool]
```

**Implementation**:
```python
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field

# Define schemas for each tool
class SearchPropertiesInput(BaseModel):
    owner_profile_id: int = Field(description="Owner profile ID")
    city: Optional[str] = Field(None, description="City name to filter by")
    sport_type: Optional[str] = Field(None, description="Sport type (tennis, basketball, etc.)")
    min_price: Optional[float] = Field(None, description="Minimum price per hour")
    max_price: Optional[float] = Field(None, description="Maximum price per hour")
    limit: int = Field(10, description="Maximum results to return")

def create_langchain_tools(tool_registry):
    tools = []
    
    # Search properties tool
    tools.append(StructuredTool.from_function(
        func=tool_registry["search_properties"],
        name="search_properties",
        description="Search for sports properties/facilities by location and sport type",
        args_schema=SearchPropertiesInput,
        coroutine=tool_registry["search_properties"]
    ))
    
    # ... similar for other tools
    
    return tools
```

### 4. Prompt Templates

**File**: `Backend/apps/chatbot/app/agent/prompts/information_prompts.py`

**Purpose**: Create context-aware prompts for the information agent

**Interface**:
```python
def create_information_prompt(
    owner_profile_id: int,
    bot_memory: Dict[str, Any]
) -> ChatPromptTemplate
```

**Prompt Structure**:
```python
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

SYSTEM_TEMPLATE = """You are a helpful sports facility booking assistant.

You help users find and learn about sports facilities, courts, availability, and pricing.

Owner Profile ID: {owner_profile_id}

Context from previous conversation:
{context}

Available tools:
- search_properties: Search for facilities by location and sport type
- get_property_details: Get detailed information about a specific property
- get_court_details: Get details about a specific court
- get_court_availability: Check available time slots for a court
- get_court_pricing: Get pricing information for a court
- get_property_media: Get photos/videos of a property
- get_court_media: Get photos/videos of a court

Guidelines:
- Use tools to get accurate, up-to-date information
- You can call multiple tools if needed to answer the user's question
- Reference previous search results from context when user says "that property" or "the last one"
- Store important information in memory for future reference
- Be conversational and helpful
- If you don't have enough information, ask clarifying questions
"""

def create_information_prompt(owner_profile_id, bot_memory):
    # Extract context from bot_memory
    context_parts = []
    
    if bot_memory.get("context", {}).get("last_search_results"):
        results = bot_memory["context"]["last_search_results"]
        context_parts.append(f"Last search returned property IDs: {results}")
    
    if bot_memory.get("user_preferences", {}).get("preferred_sport"):
        sport = bot_memory["user_preferences"]["preferred_sport"]
        context_parts.append(f"User prefers: {sport}")
    
    context = "\n".join(context_parts) if context_parts else "No previous context"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_TEMPLATE),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    
    return prompt.partial(
        owner_profile_id=owner_profile_id,
        context=context
    )
```

### 5. Bot Memory Manager

**File**: `Backend/apps/chatbot/app/agent/state/memory_manager.py`

**Purpose**: Update bot_memory with information from agent execution

**Interface**:
```python
def update_bot_memory(
    bot_memory: Dict[str, Any],
    agent_result: Dict[str, Any]
) -> Dict[str, Any]
```

**Implementation**:
```python
def update_bot_memory(bot_memory, agent_result):
    """
    Update bot_memory with information from agent execution.
    
    Stores:
    - Last search results (property IDs)
    - Last tools used
    - User preferences (sport type)
    - Last query context
    """
    if "context" not in bot_memory:
        bot_memory["context"] = {}
    
    # Extract intermediate steps to see which tools were called
    intermediate_steps = agent_result.get("intermediate_steps", [])
    
    for action, observation in intermediate_steps:
        tool_name = action.tool
        tool_input = action.tool_input
        
        # Store last tools used
        if "last_tools_used" not in bot_memory["context"]:
            bot_memory["context"]["last_tools_used"] = []
        bot_memory["context"]["last_tools_used"].append(tool_name)
        
        # Store search results
        if tool_name == "search_properties" and observation:
            property_ids = [str(p["id"]) for p in observation if "id" in p]
            bot_memory["context"]["last_search_results"] = property_ids
            
            # Store search parameters
            bot_memory["context"]["last_search_params"] = tool_input
            
            # Update user preferences if sport type was searched
            if tool_input.get("sport_type"):
                if "user_preferences" not in bot_memory:
                    bot_memory["user_preferences"] = {}
                bot_memory["user_preferences"]["preferred_sport"] = tool_input["sport_type"]
        
        # Store last viewed property/court
        if tool_name == "get_property_details":
            bot_memory["context"]["last_viewed_property"] = tool_input.get("property_id")
        
        if tool_name == "get_court_details":
            bot_memory["context"]["last_viewed_court"] = tool_input.get("court_id")
        
        # Store last availability check
        if tool_name == "get_court_availability":
            bot_memory["context"]["last_availability_check"] = {
                "court_id": tool_input.get("court_id"),
                "date": tool_input.get("date")
            }
    
    return bot_memory
```

## Data Models

### ConversationState

```python
class ConversationState(TypedDict):
    """State passed between LangGraph nodes"""
    chat_id: str
    user_id: str
    owner_profile_id: str
    user_message: str
    intent: str
    response_content: str
    response_type: str  # "text", "list", "buttons"
    response_metadata: Dict[str, Any]
    flow_state: Dict[str, Any]
    bot_memory: Dict[str, Any]
```

### bot_memory Structure

```python
{
    "context": {
        "last_search_results": ["6", "12", "15"],  # Property IDs
        "last_search_params": {
            "sport_type": "tennis",
            "city": "New York"
        },
        "last_tools_used": ["search_properties", "get_property_details"],
        "last_viewed_property": 6,
        "last_viewed_court": 23,
        "last_availability_check": {
            "court_id": 23,
            "date": "2026-03-10"
        }
    },
    "user_preferences": {
        "preferred_sport": "tennis",
        "preferred_location": "downtown"
    }
}
```

### flow_state Structure

For information queries, flow_state is minimal:

```python
{
    "intent": "information",
    "last_node": "information"
}
```

## Service Extensions

### Existing Services (No Changes Needed)

The following services in `Backend/shared/services/public_service.py` already provide the data needed:

- `search_properties()` - Returns properties with filtering
- `get_property_details()` - Returns property with courts and media
- `get_court_details()` - Returns court with pricing and media
- `get_court_pricing_for_date()` - Returns pricing for specific date
- `get_available_slots()` - Returns available time slots

### Service Response Format

All services use the standard `make_response()` format:

```python
{
    "success": True,
    "message": "...",
    "data": {...}  # Actual data
}
```

Tools extract the `data` field from responses.

## Error Handling

### Tool-Level Error Handling

Each tool handles errors gracefully:

```python
async def search_properties_tool(...):
    try:
        result = await call_sync_service(
            public_service.search_properties,
            ...
        )
        
        if hasattr(result, 'body'):
            response_data = json.loads(result.body.decode('utf-8'))
            if response_data.get('success'):
                return response_data.get('data', {}).get('items', [])
            else:
                logger.warning(f"Search failed: {response_data.get('message')}")
                return []
        else:
            logger.error(f"Unexpected response type: {type(result)}")
            return []
            
    except Exception as e:
        logger.error(f"Error searching properties: {e}", exc_info=True)
        return []
```

### Agent-Level Error Handling

The information node catches agent execution errors:

```python
async def information_node(state, llm_provider):
    try:
        # ... agent execution
        result = await agent_executor.ainvoke({"input": user_message})
        state["response_content"] = result["output"]
        
    except Exception as e:
        logger.error(f"Error in information node: {e}", exc_info=True)
        state["response_content"] = (
            "I'm sorry, I encountered an error while processing your request. "
            "Please try again or rephrase your question."
        )
        state["response_type"] = "text"
    
    return state
```

### LangChain Agent Error Handling

LangChain agents have built-in error handling:
- Tool execution failures are caught and reported to the agent
- Agent can retry with different tools or ask for clarification
- Max iterations prevent infinite loops

## Testing Strategy

### Unit Tests

**File**: `Backend/apps/chatbot/tests/test_information_node.py`

Test individual components:

1. **Tool Tests**
   - Test each tool with valid inputs
   - Test error handling (invalid IDs, missing data)
   - Test service integration

2. **Prompt Tests**
   - Test prompt generation with different bot_memory states
   - Test context extraction

3. **Memory Manager Tests**
   - Test bot_memory updates with different tool results
   - Test preference extraction

### Integration Tests

**File**: `Backend/apps/chatbot/tests/integration/test_information_flow.py`

Test end-to-end flows:

1. **Simple Search Flow**
   - User: "Show me tennis courts"
   - Expected: search_properties called, results returned

2. **Property Details Flow**
   - User: "Tell me about property 6"
   - Expected: get_property_details called, details returned

3. **Complex Query Flow**
   - User: "Show me tennis courts in NYC with pricing"
   - Expected: Multiple tools called (search + pricing)

4. **Context Reference Flow**
   - User: "Show me tennis courts" → "Tell me more about the first one"
   - Expected: Uses bot_memory to resolve reference

### Manual Testing

Use the ChatbotTest UI (`Frontend/src/pages/customer/ChatbotTest.jsx`) to test:

1. Property search queries
2. Court details requests
3. Availability checks
4. Pricing inquiries
5. Media requests
6. Complex multi-tool queries
7. Context-based follow-ups

## Performance Considerations

### Tool Execution

- Tools execute asynchronously
- LangChain agent can call multiple tools in parallel when possible
- Service calls use connection pooling

### Caching

Consider caching for:
- Property search results (5 minutes)
- Property/court details (10 minutes)
- Pricing rules (1 hour)
- Availability (1 minute)

Implementation in future iteration.

### Response Time

Target response times:
- Simple queries (1 tool): < 2 seconds
- Complex queries (2-3 tools): < 4 seconds
- Very complex queries (4+ tools): < 6 seconds

## Security Considerations

### Owner Profile Isolation

- All tools filter by `owner_profile_id`
- Users can only see properties owned by the chat's owner
- Service layer enforces ownership checks

### Input Validation

- Tool schemas validate input types
- Date formats validated (ISO 8601)
- Numeric IDs validated as integers
- String inputs sanitized

### Rate Limiting

- LLM API calls rate-limited by provider
- Database queries use connection pooling
- Consider implementing per-user rate limits in future

## Deployment Considerations

### Environment Variables

Required in `.env`:
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
```

### Dependencies

Add to `requirements.txt`:
```
langchain>=0.1.0
langchain-openai>=0.0.5
```

### Database

No schema changes required - uses existing tables:
- properties
- courts
- court_pricing
- court_availability
- media

### Monitoring

Log key metrics:
- Tool execution times
- Agent iteration counts
- Error rates by tool
- User query patterns

## Future Enhancements

1. **Multi-Property Comparison**
   - Tool to compare multiple properties side-by-side
   - Requires new service function

2. **Smart Recommendations**
   - Use bot_memory to suggest properties based on preferences
   - ML-based ranking

3. **Natural Language Dates**
   - "next Tuesday" → ISO date conversion
   - Requires date parsing utility

4. **Image Analysis**
   - Allow users to upload images and search similar facilities
   - Requires vision model integration

5. **Voice Support**
   - Speech-to-text for voice queries
   - Text-to-speech for responses

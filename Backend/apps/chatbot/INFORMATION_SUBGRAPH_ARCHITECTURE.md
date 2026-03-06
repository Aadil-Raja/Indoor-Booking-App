# Chatbot Architecture - LangChain + LangGraph

## Overview

**LangGraph**: Manages conversation flow and routing between nodes  
**LangChain**: Handles tool calling and LLM interactions within each node

## Architecture Principles

1. **LangGraph** controls workflow (intent detection → routing → nodes)
2. **LangChain agents** used in EVERY node for automatic tool calling
3. **LLM Provider**: LangChain wrapper (ChatOpenAI) - no direct OpenAI API calls
4. **flow_state**: Use as needed for structured data - you decide structure
5. **bot_memory**: Use as needed for context - you decide what to store

## High-Level Flow

```
User Message
    ↓
LangGraph: intent_detection (LangChain agent)
    ↓
LangGraph: Routing
    ↓
┌────────┬──────────────┬──────────┬─────┐
↓        ↓              ↓          ↓     ↓
greeting information   booking    faq   END
(LangChain) (LangChain)  (LangChain) (LangChain)
```

**Every node uses LangChain agents for automatic tool calling**

## Information Node

Handles ALL information-related queries:
- Property search and listing
- Property details (description, amenities, contact)
- Court details and availability
- Pricing information
- Media/photos
- Any combination of above

**LangChain agent automatically:**
- Decides which tools to call
- Calls multiple tools if needed
- Composes natural response

## State Management

### flow_state (Structured - Use as needed)
```python
flow_state = {
    "intent": "booking",
    "step": "select_date",
    "property_id": 6,
    "court_id": 2,
    "date": "2026-03-05",
    "time": "14:00"
}
```
**Purpose**: Track multi-step processes (booking flow, current step)  
**Stored**: Database (chats.flow_state)  
**Usage**: You decide how to structure and use this - be correct and consistent

### bot_memory (Flexible - Use as needed)
```python
bot_memory = {
    "context": {
        "last_search_results": ["6"],
        "last_tools_used": ["get_property_details"]
    },
    "user_preferences": {
        "preferred_sport": "tennis"
    }
}
```
**Purpose**: Store conversation context, search history, preferences  
**Stored**: Database (chats.bot_memory)  
**Usage**: You decide what to store here - be correct and consistent  
**Note**: Full conversation history in messages table, not bot_memory

## Node Implementation Pattern

Every node follows this pattern:

```python
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import StructuredTool

async def node_handler(state, tools, llm_provider):
    """
    Standard node pattern using LangChain agent.
    Tools parameter is OPTIONAL - can be None for nodes that don't need tools.
    """
    # 1. Extract state
    user_message = state["user_message"]
    owner_profile_id = state["owner_profile_id"]
    flow_state = state.get("flow_state", {})
    bot_memory = state.get("bot_memory", {})
    
    # 2. Convert tools to LangChain format (if tools provided)
    langchain_tools = create_langchain_tools(tools) if tools else []
    
    # 3. Create LangChain LLM
    llm = ChatOpenAI(model="gpt-4", api_key=llm_provider.api_key)
    
    # 4. Create agent with context
    prompt = create_prompt_with_context(owner_profile_id, bot_memory)
    agent = create_openai_functions_agent(llm, langchain_tools, prompt)
    
    # 5. Execute agent (automatic tool calling if tools available)
    agent_executor = AgentExecutor(agent=agent, tools=langchain_tools)
    result = await agent_executor.ainvoke({"input": user_message})
    
    # 6. Update state
    state["response_content"] = result["output"]
    state["response_type"] = "text"
    
    # 7. Update flow_state (if needed for multi-step)
    if "booking" in flow_state.get("intent", ""):
        flow_state["step"] = "next_step"
        state["flow_state"] = flow_state
    
    # 8. Update bot_memory (store context)
    bot_memory["context"]["last_action"] = "search"
    state["bot_memory"] = bot_memory
    
    return state
```

**Note**: Tools parameter can be None for nodes that don't need external tools (e.g., greeting node)

## Tool Integration

### Converting Custom Tools to LangChain

```python
from langchain.tools import StructuredTool

def create_langchain_tools(tool_registry):
    """Convert custom tools to LangChain format."""
    
    property_details_tool = StructuredTool.from_function(
        func=tool_registry["get_property_details"],
        name="get_property_details",
        description="Get detailed property information",
        coroutine=tool_registry["get_property_details"]
    )
    
    return [property_details_tool, ...]
```

### Automatic Tool Calling

LangChain agent automatically:
- Decides which tools to call
- Extracts parameters from user message
- Executes tools
- Composes natural response

## Benefits

✅ **No manual extraction** - LangChain handles tool selection  
✅ **Multi-tool support** - Can call multiple tools per request  
✅ **Context-aware** - Uses flow_state and bot_memory  
✅ **Consistent pattern** - Same structure for all nodes  
✅ **Easy to extend** - Add new tools without changing node logic

# Architecture Specification Prompt

Use this prompt when creating specs for the chatbot system.

---

## System Architecture Context

Read `INFORMATION_SUBGRAPH_ARCHITECTURE.md` for complete architecture details.

### Key Architecture Decisions

**Framework Stack:**
- **LangGraph**: Controls conversation flow and routing between nodes
- **LangChain**: Handles all LLM interactions and automatic tool calling
- **LLM Provider**: LangChain wrapper (ChatOpenAI from langchain-openai)
- **No direct OpenAI API calls**: All LLM operations through LangChain agents

**Node Pattern:**
- Every node uses LangChain AgentExecutor
- Tools parameter is OPTIONAL (can be None for nodes without tools, e.g., greeting)
- Automatic tool selection and execution (when tools provided)
- No manual tool extraction or calling
- information node handles: property search, details, courts, availability, pricing, media

**State Management:**
- **flow_state**: Use as needed for structured data (booking steps, selections) - you decide structure
- **bot_memory**: Use as needed for context (search history, preferences) - you decide what to store
- **messages table**: Full conversation history (not in bot_memory)
- **Important**: Be correct and consistent in how you use flow_state and bot_memory

**Tool Integration:**
- Custom tools wrapped as LangChain StructuredTool
- Tools automatically called by LangChain agents
- Multiple tools can be called in single request

### Implementation Requirements

When writing specs, ensure:

1. **All nodes use LangChain agents** - No manual tool calling
2. **LLM via LangChain wrapper** - Use ChatOpenAI from langchain-openai
3. **Tools are OPTIONAL** - Some nodes don't need tools (e.g., greeting), tools can be None
4. **information node handles all queries** - Property details, courts, availability, pricing, media
5. **flow_state usage defined** - Specify what structured data you'll store (be correct)
6. **bot_memory usage defined** - Specify what context you'll store (be correct)
7. **LangGraph for routing** - Intent detection → node selection
8. **Tool schemas defined** - Each tool has LangChain-compatible schema (when tools used)

### Example Spec Format

```
Feature: [Feature Name]

Architecture:
- Node: [node_name]
- Uses: LangChain AgentExecutor
- Tools: [list of tools]
- flow_state updates: [what gets stored]
- bot_memory updates: [what context gets saved]

Flow:
1. User message → intent_detection
2. Route to [node_name]
3. LangChain agent calls tools automatically
4. Update flow_state and bot_memory
5. Return response

Implementation:
- Create LangChain tools for [functionality]
- Define agent prompt with context
- Update state management
```

---

**When creating specs, reference this architecture to ensure consistency with LangGraph + LangChain pattern.**

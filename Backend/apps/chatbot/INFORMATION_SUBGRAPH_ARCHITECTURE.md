# Information Subgraph Architecture

## Overview

The Information Subgraph is an intelligent query handling system that processes customer questions about properties, courts, availability, pricing, and media. It can handle single or multiple questions in one message and maintains context to avoid asking users for the same information repeatedly.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        MAIN GRAPH                                │
│                                                                  │
│  User Message → Intent Detection → Router                       │
│                                      ↓                           │
│              ┌──────────────────────┴──────────────────┐        │
│              ↓                      ↓                   ↓        │
│         greeting              information          booking       │
│                              (subgraph)          (subgraph)      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              INFORMATION SUBGRAPH                                │
│                                                                  │
│  Entry: analyze_query (LLM-powered)                             │
│         ↓                                                        │
│    [Extract: entities, actions, context]                        │
│         ↓                                                        │
│  orchestrator_node                                               │
│         ↓                                                        │
│    [Calls multiple tools in parallel]                           │
│    - list_properties                                             │
│    - property_details                                            │
│    - court_details                                               │
│    - check_availability                                          │
│    - get_pricing                                                 │
│    - get_media                                                   │
│         ↓                                                        │
│  response_composer                                               │
│         ↓                                                        │
│    [Combines results + Updates bot_memory]                      │
│         ↓                                                        │
│       END                                                        │
└─────────────────────────────────────────────────────────────────┘
```

## Changes Required

### 1. Intent Detection Updates

**File:** `Backend/apps/chatbot/app/agent/nodes/intent_detection.py`

**Change:** Replace "search" intent with "information" intent

```python
# OLD
SEARCH_PATTERNS = [
    r'\b(search|find|looking\s+for|show\s+me|available)\b',
    ...
]

# NEW
INFORMATION_PATTERNS = [
    r'\b(search|find|looking\s+for|show\s+me|available)\b',
    r'\b(tell|what|which|how\s+much|details|information)\b',
    r'\b(price|cost|pricing|courts|facilities|media|photos)\b',
]

# Intent classification
def _rule_based_classification(message: str) -> str:
    # ... other patterns ...
    
    # Check information patterns (replaces search)
    for pattern in INFORMATION_PATTERNS:
        if re.search(pattern, message, re.IGNORECASE):
            return "information"  # Changed from "search"
```

### 2. Main Graph Updates

**File:** `Backend/apps/chatbot/app/agent/graphs/main_graph.py`

**Change:** Replace indoor_search with information_subgraph

```python
# OLD
from app.agent.nodes.indoor_search import indoor_search_handler
graph.add_node("indoor_search", indoor_search_node)

# Routing
{
    "greeting": "greeting",
    "search": "indoor_search",  # OLD
    "booking": "booking",
    "faq": "faq"
}

# NEW
from app.agent.graphs.information_subgraph import create_information_subgraph

# Add information subgraph
information_subgraph = create_information_subgraph(tools, llm_provider)
graph.add_node("information", information_subgraph)

# Routing
{
    "greeting": "greeting",
    "information": "information",  # NEW
    "booking": "booking",
    "faq": "faq"
}
```

## Node 1: Analyze Query

### Purpose
Extract structured information from user query using LLM with a defined schema.

### Input
- `user_message`: User's question
- `bot_memory`: Previous context

### Output Schema
```python
{
    "entities": {
        "property_name": str or None,      # "SportsX"
        "property_id": int or None,        # 6
        "court_name": str or None,         # "Court 1"
        "court_id": int or None,           # 2
        "court_type": str or None,         # "tennis"
        "date": str or None,               # "2026-03-05"
        "time": str or None                # "14:00"
    },
    "actions": [str],                      # ["property_details", "check_availability"]
    "implicit_context": str or None        # "referring to last property"
}
```

### LLM Prompt (Structured Output)

```python
prompt = f"""
Analyze this user query and extract information.

User Query: "{user_message}"
Previous Context: {context_info}

Extract the following (use "none" if not found):

ENTITIES:
- property_name: Name of property mentioned (e.g., "SportsX") or "none"
- property_id: ID if known from context or "none"
- court_name: Specific court mentioned (e.g., "Court 1") or "none"
- court_id: Court ID if known or "none"
- court_type: Sport type (tennis, basketball, etc.) or "none"
- date: Date mentioned (YYYY-MM-DD format) or "none"
- time: Time mentioned (HH:MM format) or "none"

ACTIONS (list all that apply):
- list_properties: User wants to see all properties
- property_details: User wants details about a property
- court_details: User wants details about courts
- check_availability: User wants to check if something is available
- get_pricing: User wants pricing information
- get_media: User wants to see photos/videos

IMPLICIT_CONTEXT:
- If user says "it", "there", "that place", what are they referring to?

Format your response as:
ENTITIES:
property_name: [value or none]
property_id: [value or none]
court_name: [value or none]
court_id: [value or none]
court_type: [value or none]
date: [value or none]
time: [value or none]

ACTIONS:
- [action1]
- [action2]

IMPLICIT_CONTEXT:
[description or none]

Examples:

Query: "show me properties"
ENTITIES:
property_name: none
property_id: none
court_name: none
court_id: none
court_type: none
date: none
time: none
ACTIONS:
- list_properties
IMPLICIT_CONTEXT:
none

Query: "tell me about SportsX courts and check availability"
ENTITIES:
property_name: SportsX
property_id: none
court_name: none
court_id: none
court_type: none
date: none
time: none
ACTIONS:
- property_details
- court_details
- check_availability
IMPLICIT_CONTEXT:
none

Query: "what's the price there?"
ENTITIES:
property_name: none
property_id: 6
court_name: none
court_id: none
court_type: none
date: none
time: none
ACTIONS:
- get_pricing
IMPLICIT_CONTEXT:
referring to property from last search (id: 6)

Now analyze:
"""
```

### Parsing LLM Response

```python
def parse_llm_analysis(response: str, bot_memory: dict) -> dict:
    """
    Parse structured LLM response into schema.
    """
    lines = response.strip().split('\n')
    
    entities = {}
    actions = []
    implicit_context = None
    
    current_section = None
    
    for line in lines:
        line = line.strip()
        
        if line == "ENTITIES:":
            current_section = "entities"
        elif line == "ACTIONS:":
            current_section = "actions"
        elif line == "IMPLICIT_CONTEXT:":
            current_section = "implicit"
        elif current_section == "entities" and ":" in line:
            key, value = line.split(":", 1)
            value = value.strip()
            if value != "none":
                # Convert to appropriate type
                if key in ["property_id", "court_id"]:
                    entities[key] = int(value) if value.isdigit() else None
                else:
                    entities[key] = value
        elif current_section == "actions" and line.startswith("-"):
            actions.append(line[1:].strip())
        elif current_section == "implicit" and line != "none":
            implicit_context = line
    
    # Resolve implicit context from bot_memory
    if implicit_context and not entities.get("property_id"):
        last_results = bot_memory.get("context", {}).get("last_property_id")
        if last_results:
            entities["property_id"] = last_results
    
    return {
        "entities": entities,
        "actions": actions,
        "implicit_context": implicit_context
    }
```

## Node 2: Orchestrator

### Purpose
Execute multiple tool calls in parallel based on extracted actions.

### Supported Actions

| Action | Tool Called | Parameters | Returns |
|--------|-------------|------------|---------|
| `list_properties` | `get_owner_properties` | owner_profile_id | List of properties |
| `property_details` | `get_property_details` | property_id, owner_profile_id | Full property info |
| `court_details` | `get_court_details` | court_id OR property_id | Court information |
| `check_availability` | `check_availability` | court_id, date | Available slots |
| `get_pricing` | `get_pricing` | court_id | Pricing info |
| `get_media` | `get_property_media` | property_id | Photos/videos |

### Court Details Tool (NEW)

**File:** `Backend/apps/chatbot/app/agent/tools/court_tool.py`

```python
async def get_court_details_tool(
    court_id: int = None,
    property_id: int = None,
    owner_profile_id: int = None
) -> Dict[str, Any]:
    """
    Get detailed information about courts.
    
    Can get:
    - Specific court by court_id
    - All courts for a property by property_id
    """
    if court_id:
        # Get specific court details
        tool = tools.get("get_court_details")
        return await tool(court_id=court_id)
    
    elif property_id:
        # Get all courts for property
        tool = tools.get("get_property_courts")
        courts = await tool(property_id=property_id)
        
        return {
            "property_id": property_id,
            "courts": courts,
            "total_courts": len(courts)
        }
    
    return None
```

### Parallel Execution

```python
async def orchestrator_node(state, tools):
    """
    Execute multiple tools in parallel.
    """
    analysis = state.get("query_analysis", {})
    entities = analysis.get("entities", {})
    actions = analysis.get("actions", [])
    
    # Prepare all tool calls
    tool_calls = []
    
    for action in actions:
        if action == "list_properties":
            tool_calls.append(_call_list_properties(...))
        
        elif action == "property_details":
            tool_calls.append(_call_property_details(...))
        
        elif action == "court_details":
            tool_calls.append(_call_court_details(...))
        
        elif action == "check_availability":
            tool_calls.append(_call_check_availability(...))
        
        elif action == "get_pricing":
            tool_calls.append(_call_get_pricing(...))
        
        elif action == "get_media":
            tool_calls.append(_call_get_media(...))
    
    # Execute ALL in parallel
    results = await asyncio.gather(*tool_calls, return_exceptions=True)
    
    state["tool_results"] = {
        "actions": actions,
        "results": results,
        "entities": entities
    }
    
    return state
```

## Node 3: Response Composer

### Purpose
1. Combine multiple tool results into coherent response
2. Update bot_memory with context for future queries

### bot_memory Updates

```python
async def compose_response_node(state, llm_provider):
    """
    Compose response and update bot_memory.
    """
    tool_results = state.get("tool_results", {})
    entities = tool_results.get("entities", {})
    
    # ... compose response using LLM ...
    
    # UPDATE BOT_MEMORY
    bot_memory = state.get("bot_memory", {})
    
    if "context" not in bot_memory:
        bot_memory["context"] = {}
    
    # Save property context
    if entities.get("property_id"):
        bot_memory["context"]["last_property_id"] = entities["property_id"]
        bot_memory["context"]["last_property_name"] = entities.get("property_name")
    
    # Save court context
    if entities.get("court_id"):
        bot_memory["context"]["last_court_id"] = entities["court_id"]
        bot_memory["context"]["last_court_type"] = entities.get("court_type")
    
    # Save date/time if mentioned
    if entities.get("date"):
        bot_memory["context"]["last_mentioned_date"] = entities["date"]
    if entities.get("time"):
        bot_memory["context"]["last_mentioned_time"] = entities["time"]
    
    # Save query analysis for debugging
    bot_memory["context"]["last_query_analysis"] = state.get("query_analysis")
    
    # Save tool results summary
    bot_memory["context"]["last_actions_performed"] = tool_results.get("actions", [])
    
    state["bot_memory"] = bot_memory
    
    return state
```

### bot_memory Schema

```python
bot_memory = {
    "context": {
        # Property context
        "last_property_id": 6,
        "last_property_name": "SportsX",
        
        # Court context
        "last_court_id": 2,
        "last_court_type": "tennis",
        
        # Time context
        "last_mentioned_date": "2026-03-05",
        "last_mentioned_time": "14:00",
        
        # Query history
        "last_query_analysis": {...},
        "last_actions_performed": ["property_details", "check_availability"],
        
        # Search results (legacy)
        "last_search_results": ["6"]
    },
    "user_preferences": {
        "preferred_sport": "tennis",
        "preferred_location": "Karachi"
    }
}
```

## Example Scenarios

### Scenario 1: Simple Query
```
User: "show me properties"

analyze_query:
  entities: {}
  actions: ["list_properties"]

orchestrator:
  - calls get_owner_properties()

compose_response:
  "Here are the available facilities: SportsX in Karachi"
  
bot_memory updated:
  context.last_property_id = 6
```

### Scenario 2: Multiple Questions
```
User: "tell me about SportsX courts and check if tennis is available"

analyze_query:
  entities: {property_name: "SportsX", court_type: "tennis"}
  actions: ["property_details", "court_details", "check_availability"]

orchestrator (parallel):
  - get_property_details(property_id=6)
  - get_court_details(property_id=6)
  - check_availability(court_id=X, sport_type="tennis")

compose_response:
  "SportsX is located at Maidan at KMC Sports Complex, Karachi.
   We have 2 tennis courts available:
   - Court 1: Available today at 2pm, 4pm, 6pm
   - Court 2: Available today at 3pm, 5pm, 7pm"

bot_memory updated:
  context.last_property_id = 6
  context.last_property_name = "SportsX"
  context.last_court_type = "tennis"
  context.last_actions_performed = ["property_details", "court_details", "check_availability"]
```

### Scenario 3: Follow-up Question (Uses Context)
```
User: "what's the price there?"

analyze_query:
  entities: {property_id: 6}  ← from bot_memory!
  actions: ["get_pricing"]
  implicit_context: "referring to last property"

orchestrator:
  - get_pricing(property_id=6)

compose_response:
  "At SportsX, tennis courts are $50/hour"

bot_memory updated:
  (no new context, maintains existing)
```

## File Structure

```
Backend/apps/chatbot/app/agent/
├── graphs/
│   ├── main_graph.py                    [UPDATE]
│   ├── booking_subgraph.py              [NO CHANGE]
│   └── information_subgraph.py          [NEW]
├── nodes/
│   ├── intent_detection.py              [UPDATE]
│   ├── information/                     [NEW FOLDER]
│   │   ├── __init__.py
│   │   ├── analyze_query.py
│   │   ├── orchestrator.py
│   │   └── compose_response.py
│   ├── indoor_search.py                 [DEPRECATED]
│   └── ...
└── tools/
    ├── property_tool.py                 [NO CHANGE]
    ├── court_tool.py                    [UPDATE - add get_court_details]
    ├── availability_tool.py             [NO CHANGE]
    ├── pricing_tool.py                  [NO CHANGE]
    └── media_tool.py                    [NEW]
```

## Implementation Checklist

- [ ] Update `intent_detection.py` - Replace "search" with "information"
- [ ] Update `main_graph.py` - Replace indoor_search with information_subgraph
- [ ] Create `information_subgraph.py` - New subgraph file
- [ ] Create `information/analyze_query.py` - Query analysis node
- [ ] Create `information/orchestrator.py` - Tool orchestration node
- [ ] Create `information/compose_response.py` - Response composition node
- [ ] Update `court_tool.py` - Add get_court_details_tool
- [ ] Create `media_tool.py` - Media retrieval tool
- [ ] Update bot_memory schema in documentation
- [ ] Test single-question queries
- [ ] Test multi-question queries
- [ ] Test context-aware follow-up questions
- [ ] Update CHATBOT_TESTING_GUIDE.md with new test cases

## Benefits

✅ **Handles Complex Queries**: Multiple questions in one message  
✅ **Parallel Execution**: Faster responses (tools run simultaneously)  
✅ **Context-Aware**: Remembers previous queries, no repeated questions  
✅ **Natural Responses**: LLM composes coherent answers  
✅ **Scalable**: Easy to add new actions/tools  
✅ **Maintainable**: Clear separation of concerns  
✅ **Structured**: Defined schemas, no JSON parsing errors  
✅ **Memory Management**: Intelligent bot_memory updates  

## Notes

- LLM responses use structured text format (not JSON) to avoid parsing errors
- bot_memory stores context to avoid asking users for same info
- All tool calls execute in parallel for performance
- Implicit references are resolved using bot_memory context
- Court details can be fetched by court_id OR property_id

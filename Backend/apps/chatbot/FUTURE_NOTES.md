# Session Management - Future Enhancements

## Current (MVP - Simplified)
```python
# determine_session() - Reuse existing or create new
existing = get_latest_by_user_owner(user_id, owner_profile_id)
return existing if existing else create_new()
```

## Future Enhancements

### 1. Session Expiry (24-hour threshold)
- Check `is_session_expired(chat, threshold_hours=24)` after finding existing chat
- Ask user: "Continue previous conversation? (yes/no)"
- Handle yes → reuse, no → create new

### 2. Keyword Detection
- Detect: "new topic", "start over", "reset", "fresh start"
- Auto-create new session when detected

### 3. Available Functions (Not Removed)
- `ChatRepository.is_session_expired(chat, threshold_hours)` - Check expiry
- `ChatService.create_chat(user_id, owner_profile_id)` - Force new chat
- `POST /api/chat/new` - UI button to start fresh chat


---

# Intent Detection - Simplification (Current Session)

## What We Removed

### 1. State Updates in Intent Node
**Removed:** LLM extracting user preferences during routing
```python
# OLD: Intent node extracted preferences
state_updates = {
    "bot_memory": {
        "user_preferences": {"preferred_sport": "tennis"}
    }
}
```

**Why:** 
- Intent node should ONLY route (one job)
- Preferences extracted without full context
- Made routing slower

**Future:** If needed, add preference extraction to:
- Information node: LangChain agent can extract naturally
- Booking node: Already collects during flow

### 2. Message Field in Intent Response
**Removed:** LLM generating transition messages
```python
# OLD: Intent node could return message
message = "Great! Let me help you book a court"
state["response_content"] = message
```

**Why:**
- Handlers generate their own responses anyway
- Message gets overwritten immediately
- Wasted LLM tokens
- Graph doesn't support ending at intent node

**Future:** If you want intent to respond directly:
- Modify graph to support `next_node = None` → END
- Useful for simple acknowledgments ("You're welcome!")
- Adds complexity, only add if needed

## Current Intent Node (Simplified)

**Job:** ONLY routing
- Input: user_message
- Output: next_node ("greeting" | "information" | "booking")
- Fast, simple, one responsibility

**Flow:**
```
User: "I want to book a tennis court"
↓
Intent Node: Analyzes message
↓
Returns: next_node = "booking"
↓
Graph routes to booking handler
↓
Booking handler: Generates response + extracts preferences
```

## Benefits of Simplification
- Faster routing (less LLM work)
- Simpler prompt (easier to maintain)
- Clear separation of concerns
- Each node has one job
- Easier to debug



---

# Intent Detection - Context-Aware Routing (Current Session)

## What We Added

### 1. Conversation Context in Routing
**Added:** Recent messages (last 5) to intent routing prompt

**Why:**
- Helps LLM understand ambiguous messages like "book it", "yes", "that one"
- Provides conversation history for better context
- Improves routing accuracy

**Example:**
```
User: "Show me tennis courts"
Bot: "Here are tennis courts..."
User: "book it"  ← Without context: unclear
                 ← With context: clearly wants to book
```

### 2. Last Node Tracking
**Added:** `flow_state.last_node` field

**What it does:**
- Tracks which handler processed the last message
- Values: "greeting", "information", "booking", or None (new chat)
- Persists in database across messages
- Helps LLM understand conversation flow

**Example:**
```python
flow_state = {
    "current_intent": "information",
    "last_node": "information",  # User was browsing
    "property_id": 123,
    ...
}
```

### 3. Current Intent in Routing
**Added:** `flow_state.current_intent` to routing prompt

**What it does:**
- Shows LLM what the user is currently doing
- Helps maintain conversation flow
- Values: "greeting", "information", "booking", or None

## Implementation Details

**Intent Prompt Now Includes:**
```
Recent Conversation:
- User: "Show me tennis courts"
- Bot: "Here are courts..."
- User: "book it"

Current Context:
- Last action: information
- Current intent: None

User Message: "book it"
```

**Handlers Track Last Node:**
- Greeting handler: Sets `flow_state["last_node"] = "greeting"`
- Information handler: Sets `flow_state["last_node"] = "information"`
- Booking handler: Sets `flow_state["last_node"] = "booking"`

## Benefits

✅ Better routing for ambiguous messages
✅ Understands follow-up questions
✅ Maintains conversation context
✅ Uses existing data (messages already loaded)
✅ Minimal code changes

## Example Scenarios

**Scenario 1: Ambiguous follow-up**
```
User: "Show me tennis courts"
Bot: "Here are 3 tennis courts..."
User: "book it"

Without context: Routes to greeting (doesn't understand)
With context: Routes to booking (understands user wants to book)
```

**Scenario 2: Continuing conversation**
```
User: "What's available tomorrow?"
Bot: "Here are available slots..."
User: "the morning one"

Without context: Routes to greeting (unclear)
With context: Routes to booking (knows user is selecting a slot)
```



---

# Flow State Initialization - Moved to Agent Service (Current Session)

## Problem Identified

**Issue 1:** `last_node` field was not included in `initialize_flow_state()`
- Handlers were setting it manually
- Not part of the default structure

**Issue 2:** Only greeting handler initialized flow_state
- If user went directly to booking/information → flow_state was empty `{}`
- Could cause errors when handlers tried to access fields

**Example of problem:**
```
User: "I want to book a tennis court"
↓
Intent: Routes to booking (skips greeting)
↓
Booking handler: Tries to access flow_state.property_id
↓
Error: flow_state is {} (empty)
```

## Solution Implemented

### 1. Added last_node to initialize_flow_state()
```python
flow_state = {
    "current_intent": None,
    "property_id": None,
    ...
    "last_node": None,  # NEW
    "context": {}
}
```

### 2. Moved initialization to agent_service
**Before:** Greeting handler initialized flow_state
**After:** Agent service initializes flow_state for ALL handlers

```python
# agent_service._prepare_conversation_state()
flow_state = chat.flow_state or {}
if not flow_state or not validate_flow_state(flow_state):
    flow_state = initialize_flow_state()
```

### 3. Removed initialization from greeting handler
Greeting now just uses the already-initialized flow_state.

## Benefits

✅ All handlers get properly initialized flow_state
✅ Works for direct booking/information messages
✅ Consistent structure across all flows
✅ last_node field always available
✅ Simpler greeting handler

## Flow Now

```
User: "I want to book a tennis court"
↓
Agent Service: Initializes flow_state with all fields
↓
Intent: Routes to booking
↓
Booking handler: flow_state is properly initialized ✓
```



---

# Bot Memory Initialization - Moved to Agent Service (Current Session)

## Problem Identified

**Issue:** Only greeting handler initialized bot_memory properly
- Used `_initialize_bot_memory()` and `_ensure_bot_memory_structure()`
- If user went directly to booking/information → bot_memory might be incomplete
- Agent service only set basic fields manually

**Example of problem:**
```
User: "I want to book a tennis court"
↓
Intent: Routes to booking (skips greeting)
↓
Booking handler: Tries to access bot_memory.user_preferences
↓
Might be incomplete or missing fields
```

## Solution Implemented

### Moved bot_memory initialization to agent_service

**Before:**
```python
# agent_service: Manual field setup
bot_memory = chat.bot_memory or {}
if "conversation_history" not in bot_memory:
    bot_memory["conversation_history"] = []
# ... repeat for each field

# greeting_handler: Proper initialization
bot_memory = _initialize_bot_memory()
bot_memory = _ensure_bot_memory_structure(bot_memory)
```

**After:**
```python
# agent_service: Proper initialization
bot_memory = chat.bot_memory or {}
if not bot_memory or not isinstance(bot_memory, dict):
    bot_memory = _initialize_bot_memory()
else:
    bot_memory = _ensure_bot_memory_structure(bot_memory)

# greeting_handler: Just uses it
bot_memory = state.get("bot_memory", {})
```

### Removed initialization from greeting handler
- Removed imports: `_initialize_bot_memory`, `_ensure_bot_memory_structure`
- Removed initialization logic
- Greeting now just uses the already-initialized bot_memory

## Benefits

✅ All handlers get properly initialized bot_memory
✅ Works for direct booking/information messages
✅ Consistent with flow_state initialization
✅ Uses proper initialization functions
✅ Simpler greeting handler

## Summary: Centralized Initialization

Both flow_state and bot_memory are now initialized in one place:
- **agent_service._prepare_conversation_state()**
- All handlers receive properly initialized state
- No duplicate initialization logic
- Consistent across all flows



---

# Greeting Handler - Smart Property Display (Current Session)

## Overview

Implemented intelligent greeting system that adapts based on:
- User type (new vs returning)
- Property count (single vs multiple)
- Selection state (property/court selected)

## Phase 0: Refactored Owner Profile Fetching

**Moved to shared:**
- `owner_service.py` → `Backend/shared/services/`
- `owner_repo.py` → `Backend/shared/repositories/`

**Created tool:**
- `get_owner_profile_tool` in chatbot tools
- Uses shared service via sync_bridge
- Consistent with other tools

## Phase 1: Added Initialization Flag

**Added to flow_state:**
- `owner_properties_initialized: False`
- Tracks if greeting has fetched properties
- Used by intent detection for routing

**Created helper:**
- `ensure_flow_state_fields()` - Adds missing fields without losing data
- Prevents data loss when structure updates

## Phase 2: Force New Users to Greeting

**Intent detection:**
- Checks `owner_properties_initialized` flag
- If `False` → forces route to "greeting"
- Sets `is_first_message = True`

**Greeting handler:**
- Sets `owner_properties_initialized = True` after fetching
- Respects `is_first_message` flag from intent

## Phase 3: Smart Property Display for New Users

**Three cases handled:**

**Case A: Multiple properties**
```
Here are our available facilities:
1. Downtown Arena (New York)
2. Uptown Courts (Brooklyn)
```

**Case B: Single property**
```
📍 Downtown Arena
Location: 123 Main St, New York

🏟️ Available Courts (3):
• Tennis, Basketball, Futsal
```
- Auto-sets `property_id`
- Fetches and displays court types

**Case C: Single property + single court**
```
📍 Downtown Arena
🏟️ Court: Tennis Court 1 (Tennis)
```
- Auto-sets both `property_id` and `court_id`
- Skips obvious selections

## Phase 4: Context-Aware Returning User Greetings

**Three cases handled:**

**Case A: No property selected**
```
Welcome back! Which facility would you like to book?
1. Downtown Arena (New York)
2. Uptown Courts (Brooklyn)
```

**Case B: Property selected**
```
Welcome back! Continuing with Downtown Arena (123 Main St, New York).
How can I help you today?
```

**Case C: Property + Court selected**
```
Welcome back! I see you were looking at Downtown Arena - Tennis Court 1.
Ready to continue with your booking?
```

## Phase 5: Edge Cases

**Handled:**
1. **No properties found** - Helpful error message
2. **Property not in cache** - Uses property_name fallback
3. **Data inconsistency** - Clears court_id if property_id missing

## Benefits

✅ New users always see greeting with properties
✅ Single property/court auto-selected (saves clicks)
✅ Returning users see relevant context
✅ Smart routing based on state, not message count
✅ Graceful error handling
✅ No data loss on structure updates

## Technical Details

**Functions created:**
- `ensure_flow_state_fields()` - Safe field addition
- `_fetch_property_courts()` - Fetch courts for property
- `_generate_multi_property_greeting()` - Multiple properties
- `_generate_single_property_greeting()` - Single property
- `_generate_single_property_single_court_greeting()` - Single court
- `_find_property_by_id()` - Find in cached list
- `_generate_selected_property_greeting()` - Show selected
- `_generate_property_selection_greeting()` - Show list

**State management:**
- Auto-sets `property_id`, `property_name` for single property
- Auto-sets `court_id`, `court_name` for single court
- Clears inconsistent data automatically
- Preserves existing booking data



---

# Frontend - Line Break Handling

## Issue

Backend sends properly formatted messages with `\n` line breaks, but frontend displays them as one continuous line.

**Example backend response:**
```
Hello, I am SportX's assistant!

📍 SportX Location: Maidan at KMC Sports Complex
Location: Karachi, Sindh
View on map: https://maps.app.goo.gl/...

🏟️ Court: Futsal Court (Football)

How can I help you today? I can:
• Show you available time slots
• Help you make a booking
• Answer questions about pricing
```

**Frontend displays:**
```
Hello, I am SportX's assistant! 📍 SportX Location: Maidan at KMC Sports Complex, Karachi, Sindh View on map: https://maps.app.goo.gl/... 🏟️ Court: Futsal Court (Football) How can I help you today? I can: • Show you available time slots • Help you make a booking • Answer questions about pricing
```

## Solution

Frontend needs to render `\n` as line breaks. Options:

### Option 1: CSS white-space (Recommended)
```css
.message-content {
  white-space: pre-wrap;
  /* or */
  white-space: pre-line;
}
```

### Option 2: Replace \n with <br> in JavaScript
```javascript
const formattedMessage = message.content.replace(/\n/g, '<br>');
```

### Option 3: Use <pre> tag
```html
<pre class="message-content">{message.content}</pre>
```

## Recommendation

Use `white-space: pre-line` in CSS:
- Preserves line breaks
- Collapses multiple spaces
- Wraps text naturally
- No JavaScript processing needed

```css
.chat-message-content {
  white-space: pre-line;
  word-wrap: break-word;
}
```







handle duplicate court sport types
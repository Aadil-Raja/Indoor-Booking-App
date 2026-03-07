# Chatbot Message Flow

Simple explanation of what happens when a user sends a message.

---

## The Flow (User sends "hi")

```
User sends message
    ↓
POST /api/chat/message
    ↓
Get or create chat session
    ↓
Process through LangGraph
    ↓
Return bot response
```

---

## Step-by-Step

### 1. Message Arrives
**File:** `chat.py` router

User sends: `{"user_id": 1, "owner_profile_id": 1, "content": "hi"}`

Router does:
- Get or create chat session (reuse if exists)
- Pass to AgentService

### 2. Agent Processes
**File:** `agent_service.py`

AgentService does:
- Save user message to database
- Prepare conversation state (chat history, flow_state, bot_memory)
- Run the graph
- Save bot response
- Return response

### 3. Graph Runs
**File:** `main_graph.py`

Graph nodes run in order:
1. **receive_message** - Validate message
2. **load_chat** - Load last 20 messages
3. **append_user_message** - Add current message to history
4. **intent_detection** - Ask LLM where to route ("greeting", "information", or "booking")
5. **Route to handler** - Go to the node LLM chose
6. **Handler responds** - Generate response
7. **END** - Done

### 4. Intent Detection (LLM Decides)
**File:** `intent_detection.py`

LLM looks at message "hi" and decides:
- Is it a greeting? → Route to "greeting"
- Is it a question? → Route to "information"  
- Is it a booking request? → Route to "booking"

For "hi", LLM returns: `next_node = "greeting"`

### 5. Greeting Handler
**File:** `greeting.py`

Greeting handler does:
- Check if new user (1 message) or returning user (2+ messages)
- **New user:** Fetch properties, show welcome with property list
- **Returning user:** Show simple "Welcome back!"
- Return response

### 6. Response Returns
Bot response goes back through:
- Graph → AgentService → Router → User

User receives: "Hello, I am [Business Name]'s assistant. Here are our facilities..."

---

## Key Files

**Router:** `chat.py` - Receives HTTP requests
**Service:** `agent_service.py` - Orchestrates everything
**Graph:** `main_graph.py` - Defines the flow
**Nodes:** `intent_detection.py`, `greeting.py` - Do the work

---

## Simple Example

```
User: "hi"
  ↓
Router: Get chat session
  ↓
Agent: Process message
  ↓
Graph: Run nodes
  ├─ Validate message ✓
  ├─ Load history ✓
  ├─ Add to history ✓
  ├─ LLM: "This is greeting" ✓
  └─ Greeting: "Hello! Here are our courts..." ✓
  ↓
User: Receives response
```

---

## What Gets Stored

**Database:**
- User message: "hi"
- Bot response: "Hello! Here are our courts..."
- Chat state: flow_state, bot_memory
- Conversation history

**Memory (bot_memory):**
- conversation_history: [{role: "user", content: "hi"}, ...]
- user_preferences: {}
- context: {}

---

## Fixes Applied

✅ Simplified session management (reuse or create)
✅ Removed expiry checks
✅ Cleaned up code
✅ Better error handling
✅ Cleaner logging


Remove debug prints and clean up the logic:

```python
def _is_returning_user(bot_memory: dict) -> bool:
    """
    Determine if the user is returning based on bot_memory.
    
    A user is considered returning if they have:
    - Conversation history with more than just the current user message
      (append_user_message runs before greeting, so 1 message = new user)
    
    Args:
        bot_memory: The bot_memory dict from ConversationState
        
    Returns:
        bool: True if returning user, False if new user
    """
    # Check conversation history
    # Note: append_user_message runs before greeting_handler, so the current
    # user message has already been added to conversation_history.
    # - 1 message = new user (just the current "hi")
    # - 2+ messages = returning user (has previous conversation)
    conversation_history = bot_memory.get("conversation_history", [])
    
    if len(conversation_history) > 1:
        logger.debug(f"Returning user detected: {len(conversation_history)} messages in history")
        return True
    
    logger.debug("New user detected: first message")
    return False
```

---

### ❌ ISSUE 2: Missing Prompt Template File Check
**Location**: `Backend/apps/chatbot/app/agent/nodes/intent_detection.py`

**Problem**:
The code calls `get_routing_prompt(message)` but we haven't verified the prompt template exists.

**Need to check**: `Backend/apps/chatbot/app/agent/prompts/intent_prompts.py`

Let me check this file...

---

### ❌ ISSUE 3: Error Handling in Intent Detection
**Location**: `Backend/apps/chatbot/app/agent/nodes/intent_detection.py` - `_llm_routing_decision()`

**Problem**:
```python
try:
    llm_response = json.loads(response.content.strip())
except json.JSONDecodeError as e:
    logger.error(...)
    # Return safe defaults
    return "greeting", "Hello! How can I help you?", {}
```

**Issue**:
- If LLM returns invalid JSON, it defaults to greeting
- This might not be the best user experience for all cases
- Should potentially retry or use a more sophisticated fallback

**Recommendation**:
Consider adding retry logic or better error messages to the user.

---

### ❌ ISSUE 4: State Updates Application
**Location**: `Backend/apps/chatbot/app/agent/nodes/intent_detection.py`

**Code**:
```python
# CRITICAL: Apply state updates BEFORE setting next_node (Requirement 13.5)
from app.agent.state.llm_response_parser import apply_state_updates
state = apply_state_updates(state, state_updates)
```

**Potential Issue**:
- The import is done inside the function (not at module level)
- This is inefficient and unconventional

**Fix**:
Move import to top of file:
```python
from app.agent.state.llm_response_parser import parse_llm_response, apply_state_updates
```

---

### ❌ ISSUE 5: Greeting Handler Property Fetching
**Location**: `Backend/apps/chatbot/app/agent/nodes/greeting.py`

**Problem**:
```python
# Get the property tool from registry
get_owner_properties = TOOL_REGISTRY.get("get_owner_properties")

if not get_owner_properties:
    logger.warning(f"get_owner_properties tool not found for chat {chat_id}")
    return []

# Fetch properties
properties = await get_owner_properties(owner_profile_id=int(owner_profile_id))
```

**Issues**:
1. Tool might not be registered
2. No error handling for the tool call itself
3. `owner_profile_id` is converted to int - should validate it's a valid integer first

**Fix**:
```python
async def _fetch_owner_properties(owner_profile_id: str, chat_id: str) -> list:
    """Fetch properties for the owner to display in greeting."""
    try:
        # Validate owner_profile_id
        try:
            owner_id = int(owner_profile_id)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid owner_profile_id format: {owner_profile_id}, error: {e}")
            return []
        
        # Get the property tool from registry
        get_owner_properties = TOOL_REGISTRY.get("get_owner_properties")
        
        if not get_owner_properties:
            logger.warning(f"get_owner_properties tool not found for chat {chat_id}")
            return []
        
        # Fetch properties with error handling
        properties = await get_owner_properties(owner_profile_id=owner_id)
        
        if not isinstance(properties, list):
            logger.warning(f"Invalid properties response type: {type(properties)}")
            return []
        
        logger.info(f"Fetched {len(properties)} properties for greeting in chat {chat_id}")
        return properties
        
    except Exception as e:
        logger.error(f"Error fetching properties for greeting in chat {chat_id}: {e}", exc_info=True)
        return []
```

---

### ❌ ISSUE 6: Owner Profile Fetching
**Location**: `Backend/apps/chatbot/app/agent/nodes/greeting.py` - `_fetch_owner_profile()`

**Problem**:
```python
def get_owner_profile_sync(db: Session, profile_id: int) -> dict:
    """Sync function to fetch owner profile"""
    profile = db.query(OwnerProfile).filter(OwnerProfile.id == profile_id).first()
    if profile:
        return {
            "id": profile.id,
            "business_name": profile.business_name,
            "phone": profile.phone,
            "address": profile.address,
            "verified": profile.verified
        }
    return {}
```

**Issues**:
1. Returns empty dict if profile not found - should have a default business_name
2. No validation that business_name exists

**Fix**:
```python
async def _fetch_owner_profile(owner_profile_id: str, chat_id: str) -> dict:
    """Fetch owner profile to get business_name and other details."""
    try:
        # Validate owner_profile_id
        try:
            profile_id = int(owner_profile_id)
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid owner_profile_id format: {owner_profile_id}, error: {e}")
            return {"business_name": "our facility"}  # Default fallback
        
        from sqlalchemy.orm import Session
        from shared.models import OwnerProfile
        from app.agent.tools.sync_bridge import call_sync_service
        
        def get_owner_profile_sync(db: Session, profile_id: int) -> dict:
            """Sync function to fetch owner profile"""
            profile = db.query(OwnerProfile).filter(OwnerProfile.id == profile_id).first()
            if profile:
                return {
                    "id": profile.id,
                    "business_name": profile.business_name or "our facility",  # Fallback
                    "phone": profile.phone,
                    "address": profile.address,
                    "verified": profile.verified
                }
            return {"business_name": "our facility"}  # Default if not found
        
        # Call sync service using the bridge
        profile_data = await call_sync_service(
            get_owner_profile_sync,
            db=None,
            profile_id=profile_id
        )
        
        logger.info(f"Fetched owner profile for owner_profile_id={owner_profile_id} in chat {chat_id}")
        return profile_data
        
    except Exception as e:
        logger.error(f"Error fetching owner profile for greeting in chat {chat_id}: {e}", exc_info=True)
        return {"business_name": "our facility"}  # Fallback on error
```

---

### ✅ ISSUE 7: Flow State Initialization
**Location**: `Backend/apps/chatbot/app/agent/nodes/greeting.py`

**Code**:
```python
# 1. Initialize flow_state if not present or invalid (Requirement 10.1)
flow_state = state.get("flow_state", {})
if not flow_state or not validate_flow_state(flow_state):
    logger.info(f"Initializing flow_state for chat {state['chat_id']}")
    state["flow_state"] = initialize_flow_state()
    flow_state = state["flow_state"]
```

**Potential Issue**:
Need to verify `initialize_flow_state()` and `validate_flow_state()` exist and work correctly.

**Need to check**: `Backend/apps/chatbot/app/agent/state/flow_state_manager.py`

---

### ❌ ISSUE 8: Message History Loading
**Location**: `Backend/apps/chatbot/app/agent/nodes/basic_nodes.py` - `load_chat()`

**Problem**:
```python
# Retrieve recent message history (last 20 messages for context)
messages = await message_service.get_chat_history(
    chat_id=chat_uuid,
    limit=20
)
```

**Issue**:
- Hardcoded limit of 20 messages
- No configuration option
- Might be too many or too few depending on use case

**Recommendation**:
Make this configurable via settings:
```python
from app.core.config import settings

# In config.py
MESSAGE_HISTORY_LIMIT = 20

# In load_chat
messages = await message_service.get_chat_history(
    chat_id=chat_uuid,
    limit=settings.MESSAGE_HISTORY_LIMIT
)
```

---

### ❌ ISSUE 9: Empty Message Handling
**Location**: `Backend/apps/chatbot/app/agent/nodes/basic_nodes.py` - `receive_message()`

**Code**:
```python
# Validate message is not empty
if not state["user_message"].strip():
    logger.warning(
        f"Empty message received for chat {state['chat_id']}"
    )
    # Allow empty messages to pass through - they may be handled by downstream nodes
```

**Issue**:
- Empty messages are allowed to pass through
- This could cause issues in intent detection or other nodes
- Should probably reject empty messages early

**Fix**:
```python
# Validate message is not empty
if not state["user_message"].strip():
    logger.warning(f"Empty message received for chat {state['chat_id']}")
    raise ValueError("Message content cannot be empty")
```

---

## Summary of Critical Issues

### High Priority (Must Fix)
1. ✅ **Remove debug prints** in `_is_returning_user()` - Use logger instead
2. ✅ **Move import to module level** in `intent_detection.py` - Performance issue
3. ✅ **Add validation for owner_profile_id** in greeting handler - Prevent crashes
4. ✅ **Add default business_name fallback** in `_fetch_owner_profile()` - Better UX
5. ✅ **Reject empty messages** in `receive_message()` - Data validation

### Medium Priority (Should Fix)
6. ⚠️ **Add retry logic** for LLM JSON parsing errors in intent detection
7. ⚠️ **Make message history limit configurable** in `load_chat()`
8. ⚠️ **Add better error handling** for property tool calls

### Low Priority (Nice to Have)
9. 📝 **Verify prompt templates exist** - Check `intent_prompts.py`
10. 📝 **Verify flow state manager functions** - Check `flow_state_manager.py`

---

## Testing Checklist

### Phase 1: First Message Flow
- [ ] Send first message "hi" to chatbot
- [ ] Verify intent_detection is called
- [ ] Verify LLM returns next_node = "greeting"
- [ ] Verify greeting_handler is called
- [ ] Verify new user greeting is generated
- [ ] Verify properties are fetched and displayed
- [ ] Verify properties are cached in flow_state
- [ ] Verify response is returned to user

### Edge Cases
- [ ] Test with empty message
- [ ] Test with very long message
- [ ] Test with special characters
- [ ] Test when LLM returns invalid JSON
- [ ] Test when property tool is not registered
- [ ] Test when owner profile not found
- [ ] Test when no properties exist

---

## Next Steps

1. **Check missing files**:
   - `Backend/apps/chatbot/app/agent/prompts/intent_prompts.py`
   - `Backend/apps/chatbot/app/agent/state/flow_state_manager.py`
   - `Backend/apps/chatbot/app/agent/state/llm_response_parser.py`

2. **Apply fixes** to identified issues

3. **Test the flow** with actual messages

4. **Verify LLM prompt** returns correct routing decisions

Would you like me to check the missing files and apply the fixes?


---

## ✅ FIXES APPLIED

### Fix 1: Cleaned up `_is_returning_user()` function
**File**: `Backend/apps/chatbot/app/agent/nodes/greeting.py`
- ✅ Removed debug print statements
- ✅ Removed commented-out code
- ✅ Added proper logger.debug() calls
- ✅ Improved documentation

### Fix 2: Added validation to `_fetch_owner_profile()`
**File**: `Backend/apps/chatbot/app/agent/nodes/greeting.py`
- ✅ Added owner_profile_id validation (int conversion with error handling)
- ✅ Added default fallback for business_name: "our facility"
- ✅ Returns default dict on profile not found
- ✅ Returns default dict on any error

### Fix 3: Added validation to `_fetch_owner_properties()`
**File**: `Backend/apps/chatbot/app/agent/nodes/greeting.py`
- ✅ Added owner_profile_id validation (int conversion with error handling)
- ✅ Added type checking for properties response
- ✅ Better error handling and logging

### Fix 4: Reject empty messages
**File**: `Backend/apps/chatbot/app/agent/nodes/basic_nodes.py`
- ✅ Changed from warning to error for empty messages
- ✅ Raises ValueError instead of allowing empty messages through

### Fix 5: Move import to module level
**File**: `Backend/apps/chatbot/app/agent/nodes/intent_detection.py`
- ✅ Moved `apply_state_updates` import to top of file
- ✅ Improved performance by avoiding repeated imports

---

## Verification Checklist

### ✅ All Files Verified
1. ✅ `Backend/apps/chatbot/app/routers/chat.py` - API entry point
2. ✅ `Backend/apps/chatbot/app/services/agent_service.py` - Orchestration
3. ✅ `Backend/apps/chatbot/app/agent/runtime/graph_runtime.py` - Graph execution
4. ✅ `Backend/apps/chatbot/app/agent/graphs/main_graph.py` - Graph definition
5. ✅ `Backend/apps/chatbot/app/agent/nodes/basic_nodes.py` - Basic flow nodes
6. ✅ `Backend/apps/chatbot/app/agent/nodes/intent_detection.py` - Intent detection
7. ✅ `Backend/apps/chatbot/app/agent/nodes/greeting.py` - Greeting handler
8. ✅ `Backend/apps/chatbot/app/agent/state/conversation_state.py` - State schema
9. ✅ `Backend/apps/chatbot/app/agent/state/memory_manager.py` - Memory management
10. ✅ `Backend/apps/chatbot/app/agent/state/flow_state_manager.py` - Flow state management
11. ✅ `Backend/apps/chatbot/app/agent/state/llm_response_parser.py` - LLM response parsing
12. ✅ `Backend/apps/chatbot/app/agent/prompts/intent_prompts.py` - Intent prompts

### ✅ No Syntax Errors
All modified files have been checked with getDiagnostics and show no errors.

---

## Complete Flow Summary (Phase 1)

### First Message: "hi" → Intent Detection → Greeting

```
1. User sends "hi" via POST /api/chat/message
   ↓
2. chat.py: send_message() receives request
   ↓
3. ChatService determines session (new or existing)
   ↓
4. AgentService.process_message() is called
   ↓
5. User message stored in database
   ↓
6. Conversation state prepared from chat data
   ↓
7. GraphRuntime.execute() is called
   ↓
8. Main graph starts execution:
   
   a. receive_message node
      - Validates required fields
      - Logs incoming message
      - Checks message is not empty ✅ FIXED
   
   b. load_chat node
      - Initializes flow_state and bot_memory
      - Loads last 20 messages from database
      - Formats messages for LLM context
   
   c. append_user_message node
      - Adds current message to bot_memory.conversation_history
      - Adds message to state.messages for immediate context
   
   d. intent_detection node ✅ FIXED (import moved to top)
      - Calls LLM with routing prompt
      - LLM analyzes "hi" message
      - LLM returns: next_node="greeting"
      - Applies state_updates (if any)
      - Sets state["next_node"] = "greeting"
   
   e. Routing (route_by_next_node)
      - Reads state["next_node"] = "greeting"
      - Routes to greeting handler
   
   f. greeting_handler node ✅ FIXED (validation added)
      - Initializes flow_state if needed
      - Initializes bot_memory if needed
      - Checks if returning user (conversation_history length)
      - For new user (first message):
        * Fetches owner profile (with validation) ✅
        * Fetches properties (with validation) ✅
        * Caches properties in flow_state.owner_properties
        * Generates greeting with property list
      - Sets response_content, response_type, response_metadata
   
   g. END
      - Graph execution completes
   
9. GraphRuntime returns final state
   ↓
10. AgentService updates chat state in database
   ↓
11. AgentService stores bot response in database
   ↓
12. Response returned to user via API
```

---

## Testing Instructions

### Manual Testing

1. **Start the chatbot backend**:
   ```bash
   cd Backend/apps/chatbot
   python -m uvicorn app.main:app --reload --port 8001
   ```

2. **Send first message**:
   ```bash
   curl -X POST http://localhost:8001/api/chat/message \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": 1,
       "owner_profile_id": 1,
       "content": "hi"
     }'
   ```

3. **Expected response**:
   ```json
   {
     "chat_id": "uuid-here",
     "message_id": "uuid-here",
     "content": "Hello, I am [Business Name]'s assistant. I can show you indoors and courts where you can play futsal, cricket, etc.\n\nHere are our available facilities:\n\n1. [Property Name]\n   Location: [Address, City, State]\n   View on map: [Maps Link]\n\n...",
     "message_type": "text",
     "message_metadata": {}
   }
   ```

4. **Verify in logs**:
   - ✅ "Received message" log
   - ✅ "Determining routing for chat" log
   - ✅ "LLM routing decision: next_node=greeting" log
   - ✅ "Processing greeting for chat" log
   - ✅ "New user detected: first message" log
   - ✅ "Fetched X properties for greeting" log
   - ✅ "Cached X properties in flow_state" log
   - ✅ "Generated new user greeting with X properties" log

### Edge Case Testing

1. **Empty message**:
   ```bash
   curl -X POST http://localhost:8001/api/chat/message \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": 1,
       "owner_profile_id": 1,
       "content": ""
     }'
   ```
   **Expected**: 400 Bad Request with "Message content cannot be empty"

2. **Invalid owner_profile_id**:
   ```bash
   curl -X POST http://localhost:8001/api/chat/message \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": 1,
       "owner_profile_id": 999999,
       "content": "hi"
     }'
   ```
   **Expected**: Greeting with default "our facility" business name

3. **Second message (returning user)**:
   ```bash
   # Send first message
   curl -X POST http://localhost:8001/api/chat/message \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": 1,
       "owner_profile_id": 1,
       "content": "hi"
     }'
   
   # Send second message
   curl -X POST http://localhost:8001/api/chat/message \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": 1,
       "owner_profile_id": 1,
       "content": "hello again"
     }'
   ```
   **Expected**: Returning user greeting (no property fetch)

---

## Summary

I've analyzed the complete chatbot flow for Phase 1 (first message → intent detection → greeting) and:

1. ✅ **Documented the complete flow** through all 12 key files
2. ✅ **Identified 9 issues** (5 high priority, 3 medium, 1 low)
3. ✅ **Applied 5 critical fixes**:
   - Cleaned up debug code in `_is_returning_user()`
   - Added validation for owner_profile_id in greeting handler
   - Added default fallbacks for business_name and properties
   - Reject empty messages early
   - Moved import to module level for performance
4. ✅ **Verified no syntax errors** in all modified files
5. ✅ **Created testing instructions** for manual and edge case testing

The flow is now ready for testing. All critical issues have been fixed, and the code is more robust with better error handling and validation.

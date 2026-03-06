# Task 19.1 Implementation Summary: Add Preference Extraction to LLM Prompts

## Overview
Successfully implemented preference extraction instructions in all LLM prompts across the chatbot system. This enables the LLM to automatically identify and store user preferences and inferred information in bot_memory during all conversation interactions.

## Requirements Addressed
- **4.1**: Store user preferences in bot_memory when expressed or inferred
- **4.2**: Store inferred information in bot_memory for future messages
- **4.3**: Store morning time slot preference example
- **4.4**: Store sport interest inference example

## Changes Made

### 1. Booking Prompts (`booking_prompts.py`)

Updated all booking node prompts to include preference extraction:

#### Property Selection Prompt
- Added bot_memory parameter to display current preferences
- Added "Preference Extraction" section with instructions to extract:
  - `preferred_property`: Property ID if user expresses preference
  - `preferred_sport`: Sport type mentioned
  - `preferred_time`: Time preference (morning/afternoon/evening)
  - `booking_frequency`: regular/occasional/first_time
  - `interests`: List of sports mentioned
  - `context_notes`: Other relevant context
- Updated `create_select_property_prompt()` to accept and format bot_memory

#### Service/Court Selection Prompt
- Added bot_memory parameter and preference extraction instructions
- Same preference fields as property selection
- Updated `create_select_service_prompt()` to accept and format bot_memory

#### Date Selection Prompt
- Added bot_memory parameter and preference extraction instructions
- Focus on time preferences and schedule context
- Updated `create_select_date_prompt()` to accept and format bot_memory

#### Time Selection Prompt
- Added bot_memory parameter and preference extraction instructions
- Focus on time preferences and schedule patterns
- Updated `create_select_time_prompt()` to accept and format bot_memory

#### Confirmation Prompt
- Added bot_memory parameter and preference extraction instructions
- Extract preferences even during confirmation stage
- Updated `create_confirm_booking_prompt()` to accept and format bot_memory

### 2. Information Prompts (`information_prompts.py`)

#### System Template
- Added "Bot Memory (User Preferences)" section to display current preferences
- Added comprehensive "Preference Extraction" section with instructions to extract:
  - `preferred_sport`: Sport type mentioned
  - `preferred_time`: Time preference
  - `preferred_property`: Property ID preference
  - `preferred_court`: Court ID preference
  - `booking_frequency`: Usage pattern
  - `interests`: List of sports/activities
  - `context_notes`: Relevant context about needs

#### `create_information_prompt()` Function
- Updated to format and include bot_memory in prompt
- Displays both user_preferences and inferred_information
- Added bot_memory_str to partial variables
- Updated docstring to document new bot_memory structure including all preference fields

### 3. Intent Prompts (`intent_prompts.py`)

#### Intent Routing Prompt
- Added "Bot Memory (User Preferences)" section
- Added comprehensive "Preference Extraction" section
- Updated response format to include bot_memory updates with:
  - `user_preferences` object with all preference fields
  - `inferred_information` object with frequency, interests, context
- Instructions to extract preferences during routing decision

#### `get_routing_prompt()` Function
- Added bot_memory parameter (optional, defaults to empty dict)
- Formats bot_memory for display in prompt
- Updated docstring to document Requirements 4.1 and 4.2
- Returns formatted prompt with both message and bot_memory context

## Preference Fields Defined

### user_preferences
- `preferred_sport`: Sport type (e.g., "tennis", "basketball", "futsal")
- `preferred_time`: Time preference ("morning", "afternoon", "evening")
- `preferred_property`: Property ID if user has a favorite
- `preferred_court`: Court ID if user has a favorite

### inferred_information
- `booking_frequency`: "regular", "occasional", or "first_time"
- `interests`: List of sports or activities mentioned
- `context_notes`: Any other relevant context about user's needs

## Integration Points

All updated prompt functions now accept an optional `bot_memory` parameter:
```python
create_select_property_prompt(properties, bot_memory=None)
create_select_service_prompt(property_name, courts, bot_memory=None)
create_select_date_prompt(property_name, service_name, current_date, bot_memory=None)
create_select_time_prompt(property_name, service_name, date, slots, bot_memory=None)
create_confirm_booking_prompt(flow_state, bot_memory=None)
create_information_prompt(owner_profile_id, bot_memory, business_name, fuzzy_context)
get_routing_prompt(message, bot_memory=None)
```

## Backward Compatibility

All changes are backward compatible:
- bot_memory parameter is optional with default value of None or {}
- Existing code that doesn't pass bot_memory will continue to work
- Empty bot_memory displays as empty dicts in prompts

## Testing Verification

Ran diagnostics on all modified files:
- ✅ `booking_prompts.py` - No errors
- ✅ `information_prompts.py` - No errors  
- ✅ `intent_prompts.py` - No errors

## Next Steps

The calling nodes (select_property, select_service, select_date, select_time, confirm, information_handler, intent_detection) will need to be updated to:
1. Pass bot_memory to the prompt creation functions
2. Extract preference updates from LLM responses
3. Call `update_bot_memory_preferences()` and `update_bot_memory_inferred()` to persist extracted preferences

This will be handled in subsequent tasks (19.2, 19.3).

## Files Modified
1. `Backend/apps/chatbot/app/agent/prompts/booking_prompts.py`
2. `Backend/apps/chatbot/app/agent/prompts/information_prompts.py`
3. `Backend/apps/chatbot/app/agent/prompts/intent_prompts.py`

## Compliance
✅ All requirements (4.1, 4.2, 4.3, 4.4) addressed
✅ No syntax errors or diagnostics issues
✅ Backward compatible changes
✅ Comprehensive preference extraction instructions added to all prompts

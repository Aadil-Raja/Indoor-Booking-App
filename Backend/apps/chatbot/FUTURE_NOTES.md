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


handle duplicate court sport types
maybe add fuzzy matching

allow selection using 1 , 2, 3 numbers courtd
handle this if there exist a court with multiple and one with one sport types then how court selection will be handled as it is currently using first id for details

## Property Version-Based Cache Invalidation
flow_state caches property and court data which becomes stale when owners add/delete/update properties or courts in the database, showing outdated information. Solution: Add property_version (integer) field to properties table that auto-increments whenever the property itself OR any of its courts OR pricing rules change. Store this version in flow_state alongside cached property data. Before critical operations (showing details, booking), compare cached version with current DB version - if mismatch detected, refetch property data and clear dependent selections. 

what happens if llm says proeprty selection but no properyt or court was matched etc and requested action is also get property details or get court details


add fallbacks if llm replies does not matches the options given to it 

what if the user gives reply but it is not clear for eg user first court 


add fallbacks if llm replies does not matches the options given to it 

what if the user gives reply but it is not clear for eg user first court 

what happens 

fallback the params and functions matches , else add urself if notmatches

check if there is extra call in console 


improve msgs in case of asking to tell selcet a sport for knwoing pricing 

improve greeting welcome back 

handle fallbacks of failurei n tools
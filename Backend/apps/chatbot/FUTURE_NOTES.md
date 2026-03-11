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
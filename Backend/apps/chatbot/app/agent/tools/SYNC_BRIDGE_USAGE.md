# Sync-to-Async Bridge Usage Guide

## Overview

The sync bridge utility allows async agent code to safely call synchronous services from the main database. This is necessary because:

1. The chatbot uses an **async database** for chat/message data
2. The main application uses a **sync database** for properties, courts, bookings, etc.
3. The agent needs to call sync services (property_service, court_service, etc.) from async code

## Key Components

### 1. `run_sync_in_executor(func, *args, **kwargs)`

Execute any sync function from async code.

```python
from app.agent.tools.sync_bridge import run_sync_in_executor

# Call a sync function
result = await run_sync_in_executor(
    some_sync_function,
    arg1,
    arg2,
    kwarg1=value1
)
```

### 2. `call_sync_service(service_func, db=None, **kwargs)`

Convenience wrapper for calling sync services with automatic DB session management.

```python
from app.agent.tools.sync_bridge import call_sync_service
from Backend.apps.management.app.services import property_service

# Call a sync service - db session is auto-created
result = await call_sync_service(
    property_service.get_owner_properties,
    db=None,  # Will be auto-created and managed
    owner_id=owner_id
)
```

### 3. `@sync_to_async` Decorator

Convert a sync function to async at definition time.

```python
from app.agent.tools.sync_bridge import sync_to_async

@sync_to_async
def my_sync_function(x: int, y: int) -> int:
    return x + y

# Now callable as async
result = await my_sync_function(5, 10)
```

### 4. `SyncDBContext` Context Manager

For multiple service calls that need to share a transaction.

```python
from app.agent.tools.sync_bridge import SyncDBContext, run_sync_in_executor

async with SyncDBContext() as db:
    # Multiple calls using the same session
    properties = await run_sync_in_executor(
        property_service.get_owner_properties,
        db=db,
        owner_id=owner_id
    )
    
    courts = await run_sync_in_executor(
        court_service.get_courts_by_property,
        db=db,
        property_id=properties[0]['id']
    )
    # Session is committed on exit
```

## Usage in Agent Tools

When implementing agent tools (tasks 7.2-7.6), use the sync bridge to call main database services:

### Example: Property Search Tool

```python
# Backend/apps/chatbot/app/agent/tools/property_tool.py

from typing import List, Dict, Any
from app.agent.tools.sync_bridge import call_sync_service

# Import the sync service from management app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "management"))
from app.services import property_service


async def search_properties_tool(
    owner_id: str,
    sport_type: str = None,
    location: str = None
) -> List[Dict[str, Any]]:
    """
    Search for properties owned by the specified owner.
    
    This tool wraps the sync property_service.get_owner_properties
    and makes it callable from async agent code.
    """
    # Call sync service using the bridge
    result = await call_sync_service(
        property_service.get_owner_properties,
        db=None,  # Auto-managed
        owner_id=owner_id
    )
    
    # Extract data from response
    if result.get('success'):
        properties = result.get('data', [])
        
        # Filter by sport type if specified
        if sport_type:
            # Additional filtering logic here
            pass
        
        return properties
    
    return []
```

### Example: Booking Tool

```python
# Backend/apps/chatbot/app/agent/tools/booking_tool.py

from typing import Dict, Any
from app.agent.tools.sync_bridge import call_sync_service
from datetime import date, time

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "management"))
from app.services import booking_service
from shared.schemas.booking import BookingCreate


async def create_booking_tool(
    customer_id: int,
    court_id: int,
    booking_date: date,
    start_time: time,
    end_time: time,
    notes: str = None
) -> Dict[str, Any]:
    """
    Create a new booking through the sync booking service.
    """
    booking_data = BookingCreate(
        court_id=court_id,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        notes=notes
    )
    
    result = await call_sync_service(
        booking_service.create_booking,
        db=None,
        customer_id=customer_id,
        data=booking_data
    )
    
    return result
```

## Session Management

### Automatic Session Management

When you pass `db=None` to `call_sync_service` or `run_sync_in_executor`:

1. A new sync DB session is created
2. The function is executed
3. On success: session is committed
4. On error: session is rolled back
5. Session is always closed

### Manual Session Management

Use `SyncDBContext` when you need:

- Multiple service calls in one transaction
- More control over commit/rollback timing
- To share a session across multiple operations

```python
async with SyncDBContext() as db:
    # All operations use the same session
    result1 = await run_sync_in_executor(func1, db=db, ...)
    result2 = await run_sync_in_executor(func2, db=db, ...)
    # Committed together on exit
```

## Error Handling

The sync bridge automatically handles errors:

```python
try:
    result = await call_sync_service(
        some_service_function,
        db=None,
        param=value
    )
except Exception as e:
    # Session is automatically rolled back
    logger.error(f"Service call failed: {e}")
    # Handle error appropriately
```

## Best Practices

1. **Use `call_sync_service` for service calls** - It handles DB sessions automatically
2. **Use `run_sync_in_executor` for non-service functions** - More flexible
3. **Use `SyncDBContext` for transactions** - When multiple calls need to be atomic
4. **Always handle exceptions** - Service calls can fail
5. **Log operations** - Use structured logging for debugging
6. **Don't block the event loop** - The bridge uses a thread pool to prevent blocking

## Performance Considerations

- The thread pool has a maximum of 10 workers
- Each sync call runs in a separate thread
- Database connections are pooled (size: 5, max overflow: 10)
- Sessions are created per-call unless using `SyncDBContext`

## Testing

When testing tools that use the sync bridge:

```python
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_property_search_tool():
    mock_result = {
        'success': True,
        'data': [{'id': 1, 'name': 'Test Property'}]
    }
    
    with patch('app.agent.tools.sync_bridge.get_sync_db'):
        with patch('app.services.property_service.get_owner_properties', return_value=mock_result):
            result = await search_properties_tool(owner_id='123')
            assert len(result) == 1
```

## Troubleshooting

### Issue: "No module named 'app.services'"

**Solution**: Ensure the management app is in the Python path:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "management"))
```

### Issue: "Session is closed"

**Solution**: Don't reuse sessions across await boundaries. Let the bridge manage sessions.

### Issue: "Deadlock detected"

**Solution**: Use `SyncDBContext` to ensure all operations in a transaction use the same session.

## Next Steps

Now that the sync bridge is implemented, you can proceed with:

- Task 7.2: Implement property search tool
- Task 7.3: Implement court search tool
- Task 7.4: Implement availability tool
- Task 7.5: Implement pricing tool
- Task 7.6: Implement booking tool

Each tool should use the sync bridge to call the corresponding sync service from the management app.

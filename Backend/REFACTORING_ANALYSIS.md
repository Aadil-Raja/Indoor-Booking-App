# Chatbot Dependencies Analysis & Refactoring Plan

## Current State: What Chatbot Uses from Management

### Direct Service Calls (via dynamic imports)

The chatbot **ONLY** imports services from management, never repositories directly. This is good architecture!

#### Services Used:

1. **property_service** ⚠️ SIGNATURE MISMATCH
   - Chatbot calls: `get_property_details(db, property_id, owner_id)` 
   - Actual signature: `get_property_details(db, property_id, current_owner: OwnerContext)`
   - Chatbot calls: `get_owner_properties(db, owner_id)`
   - Actual signature: `get_owner_properties(db, current_owner: OwnerContext)`

2. **court_service** ⚠️ SIGNATURE MISMATCH
   - Chatbot calls: `get_property_courts(db, property_id, owner_id)`
   - Actual signature: `get_property_courts(db, property_id, current_owner: OwnerContext)`

3. **booking_service** ✓ COMPATIBLE
   - `create_booking(db, customer_id, data)` - Uses raw customer_id
   - `get_booking_details(db, booking_id, user_id)` - Uses raw user_id
   - `cancel_booking(db, booking_id, user_id)` - Uses raw user_id

4. **availability_service** ⚠️ SIGNATURE MISMATCH
   - Chatbot calls: `get_blocked_slots(db, court_id, owner_id, from_date)`
   - Actual signature: `get_blocked_slots(db, court_id, current_owner: OwnerContext, from_date)`

5. **public_service** ✓ COMPATIBLE (most used, no auth context)
   - `search_properties(db, city, sport_type, min_price, max_price, page, limit)`
   - `get_property_details(db, property_id)`
   - `get_court_details(db, court_id)`
   - `get_available_slots(db, court_id, date_val)`
   - `get_court_pricing_for_date(db, court_id, date_val)`

### Chatbot Tool Functions (13 total):

**Property Tools:**
- `search_properties_tool()` → uses `public_service.search_properties()`
- `get_property_details_tool()` → uses `property_service.get_property_details()` or `public_service.get_property_details()`
- `get_owner_properties_tool()` → uses `property_service.get_owner_properties()`

**Court Tools:**
- `search_courts_tool()` → uses `public_service.search_properties()` + `public_service.get_property_details()`
- `get_court_details_tool()` → uses `public_service.get_court_details()`
- `get_property_courts_tool()` → uses `court_service.get_property_courts()` or `public_service.get_property_details()`

**Availability Tools:**
- `check_availability_tool()` → uses `availability_service.get_blocked_slots()`
- `get_available_slots_tool()` → uses `public_service.get_available_slots()`

**Pricing Tools:**
- `get_pricing_tool()` → uses `public_service.get_court_pricing_for_date()`
- `calculate_total_price()` → uses `get_pricing_tool()` (internal)

**Booking Tools:**
- `create_booking_tool()` → uses `booking_service.create_booking()`
- `get_booking_details_tool()` → uses `booking_service.get_booking_details()`
- `cancel_booking_tool()` → uses `booking_service.cancel_booking()`

### Current Import Method (PROBLEMATIC):

```python
def _get_management_services():
    """Dynamically import management services to avoid import conflicts."""
    import sys
    from pathlib import Path
    
    # Path manipulation to add management app to sys.path
    backend_path = Path(__file__).parent.parent.parent.parent.parent.parent
    management_path = backend_path / "apps" / "management"
    sys.path.insert(0, str(management_path))
    
    # Temporarily remove chatbot path
    chatbot_path = str(Path(__file__).parent.parent.parent.parent.parent)
    original_path = sys.path.copy()
    
    try:
        if chatbot_path in sys.path:
            sys.path.remove(chatbot_path)
        
        from app.services import property_service, public_service
        return property_service, public_service
    finally:
        sys.path = original_path
```

**Problems:**
- Fragile path manipulation
- Tight coupling between apps
- Hard to test
- Violates separation of concerns
- sys.path manipulation is error-prone

---

## Management Services Dependencies

### What Services Import:

Each service imports:
- **Repositories** (property_repo, court_repo, booking_repo, etc.)
- **Utils** (response_utils, shared_utils)
- **Shared schemas** (already in shared/)
- **Shared models** (already in shared/)

Example from `property_service.py`:
```python
from app.repositories import property_repo
from app.utils.response_utils import make_response
from app.utils.shared_utils import OwnerContext
from shared.schemas.property import PropertyCreate, PropertyUpdate
```

---

## Important Discovery: OwnerContext vs Raw IDs

**Management services now use `OwnerContext`:**
```python
def get_owner_properties(db: Session, *, current_owner: OwnerContext):
    # Uses current_owner.owner_profile_id
```

**Chatbot calls with raw IDs:**
```python
property_service.get_owner_properties(db, owner_id=owner_id_int)  # ❌ Signature mismatch!
```

**Solution:** The chatbot should primarily use `public_service` which doesn't require auth context. For owner-specific operations, we need wrapper functions.

---

## Recommended Refactoring Strategy

### Option 1: Move Shared Services & Repos to `shared/` (RECOMMENDED)

**Structure:**
```
Backend/
├── shared/
│   ├── models/          ✓ Already here
│   ├── schemas/         ✓ Already here
│   ├── repos/           → Move shared repos here
│   │   ├── property_repo.py
│   │   ├── court_repo.py
│   │   ├── booking_repo.py
│   │   ├── availability_repo.py
│   │   ├── pricing_repo.py
│   │   └── media_repo.py
│   ├── services/        → Move shared services here
│   │   ├── property_service.py
│   │   ├── court_service.py
│   │   ├── booking_service.py
│   │   ├── availability_service.py
│   │   ├── pricing_service.py
│   │   └── public_service.py
│   └── utils/           → Move shared utils here
│       ├── response_utils.py
│       └── shared_utils.py
├── apps/
│   ├── management/
│   │   └── app/
│   │       ├── services/    → Keep ONLY management-specific
│   │       │   ├── auth_service.py
│   │       │   ├── email_service.py
│   │       │   ├── media_service.py
│   │       │   ├── owner_service.py
│   │       │   └── storage/
│   │       ├── repositories/ → Keep ONLY management-specific
│   │       │   ├── auth_repo.py
│   │       │   ├── owner_repo.py
│   │       │   └── users_repo.py
│   │       ├── routers/     → Keep all (API layer)
│   │       └── deps/        → Keep (auth, db)
│   └── chatbot/
│       └── app/
│           ├── services/    → Keep chatbot-specific
│           │   ├── chat_service.py
│           │   ├── message_service.py
│           │   └── agent_service.py
│           ├── repositories/ → Keep chatbot-specific
│           │   ├── chat_repository.py
│           │   └── message_repository.py
│           └── agent/       → Keep all
```

**After refactoring, imports become:**
```python
# In chatbot tools - CLEAN!
from shared.services import property_service, public_service, booking_service
from shared.schemas.booking import BookingCreate

# No more path manipulation!
```

**Pros:**
- Clean separation of concerns
- No path manipulation
- Easy to test
- Both apps can import from shared
- Follows DRY principle
- Maintainable

**Cons:**
- Requires moving files
- Need to update all imports in both apps

---

### Option 2: Create a Separate Package (Alternative)

Create `Backend/core/` as a separate installable package:
```
Backend/
├── core/              → New shared business logic package
│   ├── services/
│   ├── repos/
│   └── utils/
├── shared/            → Keep for models/schemas only
├── apps/
```

**Pros:**
- Very clean separation
- Could be published as separate package
- Clear dependency hierarchy

**Cons:**
- More complex setup
- Overkill for current needs

---

## Recommended Action Plan

### Phase 1: Move Shared Code (RECOMMENDED)

1. **Move repositories to `Backend/shared/repos/`:**
   - property_repo.py
   - court_repo.py
   - booking_repo.py
   - availability_repo.py
   - pricing_repo.py
   - media_repo.py

2. **Move services to `Backend/shared/services/`:**
   - property_service.py
   - court_service.py
   - booking_service.py
   - availability_service.py
   - pricing_service.py
   - public_service.py

3. **Move utils to `Backend/shared/utils/`:**
   - response_utils.py
   - shared_utils.py

4. **Update imports in moved files:**
   - Change `from app.repositories import X` → `from shared.repos import X`
   - Change `from app.utils import X` → `from shared.utils import X`

5. **Update chatbot tools:**
   - Remove `_get_management_services()` functions
   - Add simple imports: `from shared.services import property_service`

6. **Update management app:**
   - Update routers to import from `shared.services`
   - Remove duplicate service files

7. **Update `Backend/setup.py`:**
   ```python
   setup(
       name="shared",
       version="0.1.0",
       packages=find_packages(),
       package_dir={"shared": "shared"},
       install_requires=[
           "sqlalchemy",
           "pydantic",
       ],
   )
   ```

8. **Test both apps:**
   - Run management app tests
   - Run chatbot app tests
   - Verify imports work correctly

---

## Files to Move

### Services (6 files):
- ✓ Backend/apps/management/app/services/property_service.py
- ✓ Backend/apps/management/app/services/court_service.py
- ✓ Backend/apps/management/app/services/booking_service.py
- ✓ Backend/apps/management/app/services/availability_service.py
- ✓ Backend/apps/management/app/services/pricing_service.py
- ✓ Backend/apps/management/app/services/public_service.py

### Repositories (6 files):
- ✓ Backend/apps/management/app/repositories/property_repo.py
- ✓ Backend/apps/management/app/repositories/court_repo.py
- ✓ Backend/apps/management/app/repositories/booking_repo.py
- ✓ Backend/apps/management/app/repositories/availability_repo.py
- ✓ Backend/apps/management/app/repositories/pricing_repo.py
- ✓ Backend/apps/management/app/repositories/media_repo.py

### Utils (2 files):
- ✓ Backend/apps/management/app/utils/response_utils.py
- ✓ Backend/apps/management/app/utils/shared_utils.py

### Keep in Management (management-specific):
- ✗ auth_service.py
- ✗ email_service.py
- ✗ media_service.py
- ✗ owner_service.py
- ✗ storage/
- ✗ auth_repo.py
- ✗ owner_repo.py
- ✗ users_repo.py

---

## Benefits After Refactoring

1. **Clean imports** - No more path manipulation
2. **Testability** - Easy to mock and test
3. **Maintainability** - Single source of truth
4. **Scalability** - Easy to add more apps
5. **Type safety** - Better IDE support
6. **Documentation** - Clear what's shared vs app-specific

---

## Estimated Effort

- Moving files: 30 minutes
- Updating imports: 1-2 hours
- Testing: 1 hour
- **Total: 2-3 hours**

---

## Next Steps

1. Review this analysis
2. Confirm approach
3. Execute refactoring
4. Test thoroughly
5. Update documentation

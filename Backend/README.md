# Indoor Booking App - Backend

## Overview

The backend consists of two FastAPI services that share common business logic through a shared package:

- **Management Service** (Port 8001): Property and booking management
- **Chatbot Service** (Port 8002): AI-powered conversational interface

Both services follow consistent import patterns and use the shared package for common functionality.

## Architecture

```
Backend/
├── apps/
│   ├── management/     # Management service
│   │   └── app/
│   │       ├── deps/   # FastAPI dependencies
│   │       ├── models/ # Management-specific models
│   │       ├── routers/# API endpoints
│   │       └── services/# Business logic
│   └── chatbot/        # Chatbot service
│       └── app/
│           ├── agent/  # LangGraph agent
│           ├── deps/   # FastAPI dependencies
│           ├── models/ # Chat-specific models
│           ├── routers/# API endpoints
│           └── services/# Business logic
├── shared/             # Shared package
│   ├── models/         # Shared business models
│   ├── services/       # Shared business services
│   ├── schemas/        # Shared API schemas
│   └── utils/          # Shared utilities
└── alembic/            # Database migrations
```

## Import Patterns

Both services follow **absolute import patterns** for consistency and maintainability.

### Shared Package Usage

The shared package contains common functionality used by both services:

**Models** (`shared.models`):
- User, Property, Court, Booking
- Base model and common database models

**Services** (`shared.services`):
- property_service, court_service, booking_service
- availability_service, pricing_service

**Schemas** (`shared.schemas`):
- PropertyResponse, CourtResponse, BookingResponse
- Common API request/response schemas

**Utilities** (`shared.utils`):
- OwnerContext, response utilities
- Common helper functions

### Import Examples

**Management App**:
```python
# App-internal imports (absolute)
from app.models.user import User
from app.services.auth_service import AuthService
from app.deps.db import get_db

# Shared package imports
from shared.models import Property, Court
from shared.services import property_service
from shared.schemas import PropertyResponse
```

**Chatbot App**:
```python
# App-internal imports (absolute)
from app.models.chat import Chat
from app.services.chat_service import ChatService
from app.deps.db import get_async_db

# Shared package imports
from shared.models import User, Property
from shared.services import booking_service
from shared.utils import OwnerContext
```

### Import Rules

1. **Use absolute imports** - No relative imports (no `from ..module import`)
2. **Import from shared when available** - Avoid code duplication
3. **Keep app-specific code in apps** - Only shared functionality goes in shared package
4. **Follow PEP 8 import order**:
   - Standard library
   - Third-party packages
   - Shared package
   - App-specific imports

## Setup Instructions

### 1. Create Virtual Environment
```bash
cd Backend
python -m venv venv
```

### 2. Activate Virtual Environment

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Shared Package
```bash
pip install -e .
```

### 5. Configure Database
Update the DATABASE_URL in app .env files:
- `Backend/apps/management/.env`
- `Backend/apps/chatbot/.env`

Replace with your PostgreSQL connection string:
```
postgresql://username:password@host:port/database_name
```

### 6. Run Migrations

**Main migrations (shared models):**
```bash
cd Backend
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

**Chatbot migrations:**
```bash
cd Backend/apps/chatbot
alembic revision --autogenerate -m "Add chat messages"
alembic upgrade head
```

### 7. Start Services

**Management Service:**
```bash
cd Backend/apps/management
uvicorn app.main:app --port 8001 --reload
```

**Chatbot Service:**
```bash
cd Backend/apps/chatbot
uvicorn app.main:app --port 8002 --reload
```

## API Endpoints

- Management API: http://localhost:8001/docs
- Chatbot API: http://localhost:8002/docs

## Database Commands

### Create new migration
```bash
alembic revision --autogenerate -m "description"
```

### Apply migrations
```bash
alembic upgrade head
```

### Rollback migration
```bash
alembic downgrade -1
```

### View migration history
```bash
alembic history
```

### Check current version
```bash
alembic current
```


## Shared Package

### What's in the Shared Package?

The shared package provides common functionality used by both services:

**Business Models**:
- User, Property, Court, Booking, Availability
- Base model with common fields (id, created_at, updated_at)

**Business Services**:
- property_service: Property CRUD operations
- court_service: Court management
- booking_service: Booking operations
- availability_service: Availability checking
- pricing_service: Price calculations

**API Schemas**:
- Request/response schemas for properties, courts, bookings
- Common validation schemas

**Utilities**:
- OwnerContext: Owner-specific context management
- Response utilities: Standardized API responses

### Installing the Shared Package

The shared package must be installed in editable mode:

```bash
cd Backend
pip install -e .
```

This makes the `shared` module available to both services.

### Verifying Shared Package Installation

```bash
python -c "import shared; print('Shared package installed successfully')"
```

### When to Add to Shared Package

Add functionality to shared when:
- Used by both management and chatbot services
- Contains business logic that should be consistent
- Represents core domain models or operations

Keep in app-specific directories when:
- Only used by one service
- Service-specific implementation details
- Not part of core business logic

## Import Troubleshooting

### Common Import Issues

#### Issue: `ModuleNotFoundError: No module named 'app'`

**Cause**: Running Python from wrong directory or incorrect import path

**Solution**: 
```bash
# Ensure you're in the correct app directory
cd Backend/apps/management  # or chatbot
uvicorn app.main:app --reload
```

#### Issue: `ModuleNotFoundError: No module named 'shared'`

**Cause**: Shared package not installed

**Solution**:
```bash
cd Backend
pip install -e .
```

#### Issue: Relative import errors

**Cause**: Using relative imports instead of absolute imports

**Solution**: Replace relative imports with absolute imports:
```python
# ❌ Wrong
from ..models.user import User
from .auth_service import AuthService

# ✅ Correct
from app.models.user import User
from app.services.auth_service import AuthService
```

#### Issue: Circular import errors

**Cause**: Modules importing each other

**Solution**:
- Use dependency injection
- Import at function level if needed
- Restructure code to break circular dependency

#### Issue: IDE not recognizing imports

**Cause**: IDE not configured with correct Python interpreter

**Solution**:
- Select the virtual environment as Python interpreter
- Restart IDE after installing shared package
- Mark Backend directory as sources root

### Import Verification

Both services include import verification scripts:

**Management Service**:
```bash
cd Backend/apps/management
python test_imports.py
```

**Chatbot Service**:
```bash
cd Backend/apps/chatbot
python test_imports.py
```

These scripts verify that all imports resolve correctly.

## Development Guidelines

### Code Organization

1. **Shared Package**: Common business logic, models, and utilities
2. **App-Specific**: Service-specific implementations and features
3. **Dependencies**: Use FastAPI dependency injection
4. **Configuration**: Environment-based configuration with Pydantic

### Import Best Practices

1. **Always use absolute imports**:
   ```python
   from app.models.user import User  # ✅
   from ..models.user import User     # ❌
   ```

2. **Import from shared for common functionality**:
   ```python
   from shared.services import property_service  # ✅
   from apps.management.app.services import property_service  # ❌
   ```

3. **Follow PEP 8 import order**:
   ```python
   # 1. Standard library
   from typing import Optional
   from datetime import datetime
   
   # 2. Third-party
   from fastapi import APIRouter
   from sqlalchemy.orm import Session
   
   # 3. Shared package
   from shared.models import Property
   from shared.services import property_service
   
   # 4. App-specific
   from app.models.user import User
   from app.deps.db import get_db
   ```

4. **Keep imports organized and minimal**:
   - Only import what you need
   - Remove unused imports
   - Group related imports

### Testing

Run tests for each service:

```bash
# Management service
cd Backend/apps/management
pytest

# Chatbot service
cd Backend/apps/chatbot
pytest
```

### Code Quality

- Follow PEP 8 style guide
- Use type hints
- Write docstrings for public functions
- Keep functions focused and small
- Use meaningful variable names

## Additional Resources

- [Management Service README](apps/management/README.md)
- [Chatbot Service README](apps/chatbot/README.md)
- [Shared Package Documentation](shared/README.md)
- [Import Refactor Spec](.kiro/specs/chatbot-import-refactor/)

## Support

For issues or questions:
1. Check the troubleshooting sections above
2. Review the import verification scripts
3. Consult the service-specific README files
4. Check the spec documentation for detailed design decisions

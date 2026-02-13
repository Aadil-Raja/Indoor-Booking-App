# Indoor Booking App - Project Structure & Setup Instructions

## Backend Structure

```
Backend/
├── alembic/                          # Main migrations (shared models)
│   └── versions/
│
├── apps/
│   ├── chatbot/
│   │   ├── alembic/                  # Chatbot-specific migrations
│   │   │   └── versions/
│   │   ├── app/
│   │   │   ├── agent/                # LangGraph AI agent
│   │   │   │   ├── graphs/           # Graph definitions & workflows
│   │   │   │   ├── state/            # State management schemas
│   │   │   │   ├── nodes/            # Graph node implementations
│   │   │   │   ├── tools/            # Agent tools & functions
│   │   │   │   ├── runtime/          # Runtime configuration & execution
│   │   │   │   └── prompts/          # System & user prompts
│   │   │   ├── core/
│   │   │   ├── deps/
│   │   │   ├── models/               # Chat-specific models only
│   │   │   ├── repositories/
│   │   │   ├── routers/
│   │   │   ├── schemas/
│   │   │   ├── services/
│   │   │   └── utils/
│   │   ├── .env
│   │   ├── .gitignore
│   │   └── alembic.ini
│   │
│   └── management/
│       ├── app/
│       │   ├── core/
│       │   ├── deps/
│       │   ├── repositories/
│       │   ├── routers/
│       │   ├── schemas/
│       │   ├── services/
│       │   └── utils/
│       ├── .env
│       └── .gitignore
│
├── shared/
│   ├── models/                       # All main models (property, user, booking, etc.)
│   ├── repos/
│   ├── schemas/
│   └── services/
│
├── .gitignore
├── alembic.ini                       # Points to shared models
├── requirements.txt                  # Python dependencies
├── setup.py                          # Shared package setup
└── README.md                         # Setup instructions
```

---

## Frontend Structure

```
Frontend/
├── src/
├── .env
└── .gitignore
```

---

## Instructions for LLM

**IMPORTANT: Only create the folder structure and files. DO NOT run any commands. All commands are documented in README.md for the user to run manually.**

### Files to Create

### 2. Backend/requirements.txt

```txt
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.36
alembic==1.14.0
psycopg2-binary==2.9.10
pydantic==2.10.3
pydantic-settings==2.6.1
python-dotenv==1.0.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.17
langchain==0.3.13
langchain-openai==0.2.14
langgraph==0.2.59
```

---

### 3. Backend/.env

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/indoor_booking_db

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Security
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI (for chatbot)
OPENAI_API_KEY=your-openai-api-key
```

---

### 4. Backend/apps/management/.env

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/indoor_booking_db

# API
SERVICE_NAME=management
API_HOST=0.0.0.0
API_PORT=8001

# Security
SECRET_KEY=your-secret-key-change-this-in-production
```

---

### 5. Backend/apps/chatbot/.env

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/indoor_booking_db

# API
SERVICE_NAME=chatbot
API_HOST=0.0.0.0
API_PORT=8002

# OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini

# LangGraph
LANGGRAPH_CHECKPOINT_ENABLED=True
```

---

### 6. Backend/alembic.ini

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os

sqlalchemy.url = postgresql://user:password@localhost:5432/indoor_booking_db

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

---

### 7. Backend/apps/chatbot/alembic.ini

```ini
[alembic]
script_location = alembic
prepend_sys_path = ../..
version_path_separator = os

sqlalchemy.url = postgresql://user:password@localhost:5432/indoor_booking_db

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

---

### 8. Backend/setup.py

```python
from setuptools import setup, find_packages

setup(
    name="shared",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[],
)
```

---

### 9. Test Models

**Backend/shared/models/property.py**
```python
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Property(Base):
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    address = Column(String(500))
    price_per_hour = Column(Float, nullable=False)
    capacity = Column(Integer)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

**Backend/apps/chatbot/app/models/chat_message.py**
```python
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    message = Column(Text, nullable=False)
    response = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

---

### 10. Backend/README.md

```markdown
# Indoor Booking App - Backend

## Setup Instructions

### 1. Install Dependencies
```bash
cd Backend
pip install -r requirements.txt
```

### 2. Install Shared Package
```bash
pip install -e .
```

### 3. Configure Database
Update the DATABASE_URL in all .env files:
- `Backend/.env`
- `Backend/apps/management/.env`
- `Backend/apps/chatbot/.env`
- `Backend/alembic.ini`
- `Backend/apps/chatbot/alembic.ini`

Replace with your PostgreSQL connection string:
```
postgresql://username:password@host:port/database_name
```

### 4. Run Migrations

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

### 5. Start Services

**Management Service:**
```bash
cd Backend/apps/management
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**Chatbot Service:**
```bash
cd Backend/apps/chatbot
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
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
```

---

## LangGraph Agent Structure

### Purpose of Each Folder:

**agent/graphs/**
- Define conversation flows and state machines
- Multi-step reasoning workflows
- Graph topology and edge conditions
- Example: `booking_assistant_graph.py`, `property_search_graph.py`

**agent/state/**
- State schemas for graph execution
- Conversation context management
- User session state
- Example: `conversation_state.py`, `booking_state.py`

**agent/nodes/**
- Individual processing nodes in the graph
- Business logic for each step
- Decision-making functions
- Example: `search_properties.py`, `check_availability.py`, `confirm_booking.py`

**agent/tools/**
- External tools the agent can call
- Database queries, API calls
- Utility functions for agent
- Example: `property_search_tool.py`, `booking_tool.py`, `calendar_tool.py`

**agent/runtime/**
- Graph execution engine
- Checkpointing and persistence
- Error handling and retries
- Example: `executor.py`, `checkpointer.py`

**agent/prompts/**
- System prompts for LLM
- User message templates
- Few-shot examples
- Example: `system_prompt.py`, `booking_prompts.py`

---

## Quick Start Checklist

1. ✅ Create all folders and files as specified
2. ✅ Install dependencies: `pip install -r requirements.txt`
3. ✅ Install shared package: `pip install -e .`
4. ✅ Update DATABASE_URL in all .env files and alembic.ini files
5. ✅ Run main migrations: `alembic upgrade head`
6. ✅ Run chatbot migrations: `cd apps/chatbot && alembic upgrade head`
7. ✅ Start management service: `uvicorn app.main:app --port 8001 --reload`
8. ✅ Start chatbot service: `uvicorn app.main:app --port 8002 --reload`
9. ✅ Access API docs at http://localhost:8001/docs and http://localhost:8002/docs

---

## Notes

- Both services share the same database
- Main alembic manages shared models (Property, User, Booking, etc.)
- Chatbot alembic manages chat-specific models (ChatMessage)
- Update OpenAI API key in chatbot .env for AI features
- All services must be run from their respective directories


---

### 11. Backend/.gitignore

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Database
*.db
*.sqlite

# Logs
*.log
```

---

### 12. Backend/apps/management/.gitignore

```
__pycache__/
*.pyc
.env
```

---

### 13. Backend/apps/chatbot/.gitignore

```
__pycache__/
*.pyc
.env
```

---

### 14. Frontend/.env

```env
VITE_API_URL=http://localhost:8001
VITE_CHATBOT_API_URL=http://localhost:8002
```

---

### 15. Frontend/.gitignore

```
# Dependencies
node_modules/

# Production
dist/
build/

# Environment
.env
.env.local
.env.*.local

# IDE
.vscode/
.idea/

# Logs
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# OS
.DS_Store
Thumbs.db
```

---

## Summary for LLM

**Create the following:**
1. All folder structures as shown in the Backend and Frontend sections
2. All configuration files (.env, alembic.ini, .gitignore)
3. requirements.txt with dependencies
4. setup.py for shared package
5. Test models (Property and ChatMessage)
6. README.md with all commands

**DO NOT:**
- Run pip install
- Run alembic commands
- Start any services
- Execute any shell commands

The user will run all commands manually following the README.md inst
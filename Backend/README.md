# Indoor Booking App - Backend

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

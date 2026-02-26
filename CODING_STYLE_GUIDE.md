# Coding Style Guide

## Architecture Pattern

**Layered Architecture: Router → Service → Repository → Model**

- **Router**: HTTP endpoints, auth, input validation
- **Service**: Business logic, orchestration, validation
- **Repository**: Database operations, queries
- **Model**: Database schema (SQLAlchemy ORM)

---

## 1. Router Layer

**Responsibilities:** Define endpoints, validate input, handle auth, delegate to services

```python
@router.post("/resource", status_code=status.HTTP_201_CREATED)
def create_resource(
    payload: ResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        return service.create(db, user_id=current_user.id, data=payload)
    except Exception as e:
        return make_response(False, "Failed", status_code=500, error=str(e))
```

**Rules:**
- Use `Depends()` for db and auth
- Wrap in try-except
- Keep thin - no business logic
- Add docstrings

---

## 2. Service Layer

**Responsibilities:** Business rules, validation, orchestration

```python
def create_resource(db: Session, *, user_id: int, data: ResourceCreate):
    # Validate
    if not _validate(data):
        return make_response(False, "Invalid", status_code=400)
    
    # Call repo
    resource = repo.create(db, user_id=user_id, **data.dict())
    
    # Transform response
    return make_response(True, "Created", data={"id": resource.id}, status_code=201)
```

**Rules:**
- Use keyword-only args: `def func(db, *, param1, param2)`
- Always return `make_response()`
- No direct DB queries - use repos
- Handle business validation

---

## 3. Repository Layer

**Responsibilities:** Database CRUD, queries, joins

```python
def create_resource(db: Session, *, user_id: int, title: str) -> Resource:
    resource = Resource(user_id=user_id, title=title)
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource

def get_with_relations(db: Session, id: int) -> Optional[Resource]:
    return db.query(Resource).options(joinedload(Resource.items)).filter(Resource.id == id).first()
```

**Rules:**
- Use keyword-only args
- Return ORM objects (not dicts/responses)
- Use `joinedload()` for eager loading
- Always `commit()` and `refresh()`

---

## 4. Response Handling

**Standardized response utility:**

```python
def make_response(success: bool, message: str, data: Any = None, *, status_code: int = 200, error: Optional[str] = None):
    payload = {"success": success, "message": message}
    if data is not None:
        payload["data"] = data
    if error is not None:
        payload["error"] = error
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))
```

**Usage:**
```python
return make_response(True, "Success", data={"id": 1}, status_code=201)
return make_response(False, "Not found", status_code=404, error="Details")
```

---

## 5. Configuration

**Pydantic Settings:**

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    jwt_secret: str
    api_key: str | None = None

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

---

## 6. Database Models

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship

class MyModel(Base):
    __tablename__ = "my_models"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="items")
    children = relationship("Child", cascade="all, delete-orphan", passive_deletes=True)
```

**Rules:**
- Use `__tablename__` (snake_case, plural)
- Index FKs and frequently queried columns
- Use `nullable=False` explicitly
- Use `func.now()` for timestamps
- Use `cascade="all, delete-orphan"` with `passive_deletes=True`

---

## 7. Pydantic Schemas

```python
from pydantic import BaseModel, Field
from typing import Optional

class ResourceBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)

class ResourceCreate(ResourceBase):
    pass

class ResourceResponse(ResourceBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
```

**Rules:**
- Use `Base`, `Create`, `Update`, `Response` suffixes
- Use `Field()` for validation
- Use `from_attributes = True` for ORM compatibility

---

## 8. Authentication

```python
def get_current_user(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    
    user = users_repo.get_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

---

## 9. Database Session

```python
engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=5)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## 10. Error Handling

**HTTP Status Codes:**
- `200`: Success (GET, PUT, DELETE)
- `201`: Created (POST)
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `409`: Conflict
- `500`: Internal Server Error

---

## 11. Naming Conventions

**Python:**
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`

**Database:**
- Tables: `snake_case` (plural)
- Columns: `snake_case`
- FKs: `table_id`

**API:**
- Paths: `/resources`, `/resources/{id}`
- Multi-word: `/admin-resources`
- Actions: `/resources/{id}/publish`

---

## 12. FastAPI Setup

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(router, prefix="/api", tags=["resources"])
```

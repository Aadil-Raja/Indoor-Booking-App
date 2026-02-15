from pydantic import BaseModel, EmailStr
from typing import Optional ,Literal

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: Literal["customer", "owner"] = "customer"
class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: str

    class Config:
        from_attributes = True   # ✅ replaces orm_mode
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError
from typing import Optional

from app.core.config import get_settings
from app.deps.db import get_db
from app.repositories import users_repo
from shared.utils import OwnerContext
from shared.models import UserRole

settings = get_settings()


def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """
    Dependency: verifies JWT and returns the current user (any role).
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate token")

    user = users_repo.get_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


def get_current_customer(current_user = Depends(get_current_user)):
    """
    Dependency: ensures the current user is a customer.
    """
    if current_user.role != UserRole.customer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customers only")
    return current_user


def get_current_owner(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """
    Dependency: ensures the current user is an owner and returns OwnerContext.
    OwnerContext contains user_id and owner_profile_id from token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        role = payload.get("role")
        owner_profile_id = payload.get("owner_profile_id")
        
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
        # Verify user is an owner
        if role != UserRole.owner.value:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Property owners only")
        
        # owner_profile_id should always exist (created on signup)
        if not owner_profile_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner profile not found")
        
        return OwnerContext(user_id=int(user_id), owner_profile_id=owner_profile_id)
        
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate token")


def get_current_admin(current_user = Depends(get_current_user)):
    """
    Dependency: ensures the current user is an admin.
    """
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins only")
    return current_user

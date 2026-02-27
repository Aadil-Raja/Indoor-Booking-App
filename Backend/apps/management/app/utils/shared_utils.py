# app/services/shared_utils.py
from __future__ import annotations
import os, hmac, hashlib, time, jwt
from typing import Iterable, Optional
from passlib.context import CryptContext
from fastapi import HTTPException
# single password context for the whole app
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------- Owner Context ----------
class OwnerContext:
    """Context object for authenticated owner (profile always exists)"""
    def __init__(self, user_id: int, owner_profile_id: int):
        self.user_id = user_id
        self.owner_profile_id = owner_profile_id

# ---------- time ----------
def now_ts() -> int:
    return int(time.time())

# ---------- email ----------
def normalize_email(email: str) -> str:
    return email.strip().lower()

def domain_allowed(email: str, allowed_domains: Optional[Iterable[str]] = None) -> bool:
    if not allowed_domains:
        return True
    domain = email.split("@")[-1].lower()
    return domain in {d.lower() for d in allowed_domains}

# ---------- password hashing ----------
def hash_password(p: str) -> str:
    return _pwd_ctx.hash(p)

def verify_password(p: str, p_hash: Optional[str]) -> bool:
    if not p_hash:
        return False
    return _pwd_ctx.verify(p, p_hash)

# ---------- OTP / codes ----------
def gen_code_6() -> str:
    # 6-digit numeric code
    return f"{int.from_bytes(os.urandom(3), 'big') % 1_000_000:06d}"

def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def safe_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)

# ---------- JWT ----------
def issue_access_token(
    *,
    user_id: int | str,
    role: Optional[str] = None,
    owner_profile_id: Optional[int] = None,
    token_version: int = 0,
    ttl_seconds: int,
    jwt_secret: str,
    jwt_algorithm: str,
    aud: Optional[str] = None,
) -> str:
    now = now_ts()
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + ttl_seconds,
        "tv": token_version,
        "typ": "access",
    }
    if role:
        payload["role"] = role
    if owner_profile_id:
        payload["owner_profile_id"] = owner_profile_id
    if aud:
        payload["aud"] = aud
    return jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)

def issue_reset_token(
    *,
    user_id: int | str,
    token_version: int = 0,
    ttl_seconds: int,
    jwt_secret: str,
    jwt_algorithm: str,
) -> str:
    now = now_ts()
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + ttl_seconds,
        "tv": token_version,
        "typ": "reset",
    }
    return jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)

def decode_token(
    token: str,
    *,
    jwt_secret: str,
    jwt_algorithm: str,
) -> dict:
    return jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])

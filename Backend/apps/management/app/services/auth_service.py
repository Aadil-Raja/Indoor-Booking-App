from __future__ import annotations
import os, hmac, hashlib, time, jwt
from typing import Optional
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from app.repositories import auth_repo, users_repo
from app.core.config import get_settings
from app.services.email_service import send_otp_email, send_password_reset_email
from shared.utils.response_utils import make_response

settings = get_settings()

# Password context for the auth service
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------- Helper Functions ----------
def now_ts() -> int:
    return int(time.time())


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(p: str) -> str:
    return _pwd_ctx.hash(p)


def verify_password(p: str, p_hash: Optional[str]) -> bool:
    if not p_hash:
        return False
    return _pwd_ctx.verify(p, p_hash)


def gen_code_6() -> str:
    # 6-digit numeric code
    return f"{int.from_bytes(os.urandom(3), 'big') % 1_000_000:06d}"


def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def safe_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


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


# ---------- Service Functions ----------


async def signup(
    db: Session,
    *,
    email: str,
    password: str,
    name: str,
    role: str,
    background_tasks: BackgroundTasks,
):
    """Create a new user account and send OTP."""
    email_norm = normalize_email(email)

    if users_repo.get_by_email(db, email_norm):
        return make_response(False, "Email already registered", status_code=409)

    password_hash = hash_password(password)
    user = users_repo.create(db, email=email_norm, password_hash=password_hash, name=name, role=role)

    # Auto-create owner profile for owners
    from shared.models import UserRole
    if role == UserRole.owner.value:
        from shared.repositories import owner_repo
        owner_repo.create(db, user_id=user.id)

    # Send OTP
    code = gen_code_6()
    code_hash = sha256_str(code)
    auth_repo.create_otp(db, email=email_norm, code_hash=code_hash, ttl_minutes=10)
    background_tasks.add_task(send_otp_email, email_norm, code)
    
    return make_response(
        True,
        "Account created. Please verify your email.",
        data={"email": email_norm},
        status_code=201,
    )


async def request_code(
    db: Session,
    *,
    email: str,
    background_tasks: BackgroundTasks,
):
    """Resend verification code."""
    email_norm = normalize_email(email)
    user = users_repo.get_by_email(db, email_norm)
    
    if not user:
        return make_response(False, "Account not found", status_code=404)

    code = gen_code_6()
    code_hash = sha256_str(code)
    auth_repo.create_otp(db, email=email_norm, code_hash=code_hash, ttl_minutes=10)
    background_tasks.add_task(send_otp_email, email_norm, code)
    
    return make_response(True, "Verification code sent", status_code=200)


async def verify_code(
    db: Session,
    *,
    email: str,
    code: str,
    background_tasks: BackgroundTasks,
):
    """Verify email with OTP code."""
    email_norm = normalize_email(email)
    user = users_repo.get_by_email(db, email_norm)
    
    if not user:
        return make_response(False, "Account not found", status_code=404)

    otp = auth_repo.get_latest_active(db, email_norm)
    if not otp:
        return make_response(False, "No active code", status_code=400)

    if not safe_equals(otp.code_hash, sha256_str(code)):
        auth_repo.increment_attempts(db, otp)
        return make_response(False, "Invalid code", status_code=400)
    
    auth_repo.consume(db, otp)
    return make_response(True, "Email verified successfully", status_code=200)


async def login_password(
    db: Session,
    *,
    email: str,
    password: str,
    background_tasks: BackgroundTasks,
):
    """Login with email/password."""
    email_norm = normalize_email(email)
    user = users_repo.get_by_email(db, email_norm)
    
    if not user or not verify_password(password, user.password_hash):
        return make_response(False, "Invalid email or password", status_code=401)

    # Get owner_profile_id for owners (always exists after signup)
    owner_profile_id = None
    if user.role.value == "owner":
        from shared.repositories import owner_repo
        owner_profile = owner_repo.get_by_user_id(db, user.id)
        owner_profile_id = owner_profile.id if owner_profile else None

    token = issue_access_token(
        user_id=user.id,
        role=user.role.value,
        owner_profile_id=owner_profile_id,
        ttl_seconds=3600,
        jwt_secret=settings.jwt_secret,
        jwt_algorithm=settings.jwt_algorithm,
    )
    
    return make_response(
        True,
        "Login successful",
        data={
            "access_token": token,
            "token_type": "bearer",
            "name": user.Name
        },
        status_code=200
    )


async def login_send_code(
    db: Session,
    *,
    email: str,
    background_tasks: BackgroundTasks,
):
    """Send login OTP."""
    email_norm = normalize_email(email)
    user = users_repo.get_by_email(db, email_norm)
    
    if not user:
        return make_response(False, "Account not found", status_code=404)

    code = gen_code_6()
    auth_repo.create_otp(db, email=email_norm, code_hash=sha256_str(code), ttl_minutes=10)
    background_tasks.add_task(send_otp_email, email_norm, code)
    
    return make_response(True, "Login code sent", status_code=200)


async def login_verify_code(
    db: Session,
    *,
    email: str,
    code: str,
):
    """Verify login OTP and issue token."""
    email_norm = normalize_email(email)
    user = users_repo.get_by_email(db, email_norm)
    
    if not user:
        return make_response(False, "Account not found", status_code=404)

    otp = auth_repo.get_latest_active(db, email_norm)
    if not otp or not safe_equals(otp.code_hash, sha256_str(code)):
        if otp:
            auth_repo.increment_attempts(db, otp)
        return make_response(False, "Invalid code", status_code=400)

    auth_repo.consume(db, otp)

    # Get owner_profile_id for owners (always exists after signup)
    owner_profile_id = None
    if user.role.value == "owner":
        from shared.repositories import owner_repo
        owner_profile = owner_repo.get_by_user_id(db, user.id)
        owner_profile_id = owner_profile.id if owner_profile else None

    token = issue_access_token(
        user_id=user.id,
        role=user.role.value,
        owner_profile_id=owner_profile_id,
        ttl_seconds=3600,
        jwt_secret=settings.jwt_secret,
        jwt_algorithm=settings.jwt_algorithm,
    )
    
    return make_response(
        True,
        "Login successful",
        data={
            "access_token": token,
            "token_type": "bearer",
            "name": user.Name
        },
        status_code=200
    )


def request_password_reset(
    db: Session,
    *,
    email: str,
    background_tasks: BackgroundTasks,
):
    """Request password reset link."""
    email_norm = normalize_email(email)
    user = users_repo.get_by_email(db, email_norm)

    if user:
        token = issue_reset_token(
            user_id=user.id,
            ttl_seconds=3600,
            jwt_secret=settings.jwt_secret,
            jwt_algorithm=settings.jwt_algorithm,
        )
        link = f"{settings.reset_password_url}?token={token}"
        background_tasks.add_task(send_password_reset_email, email_norm, link)

    return make_response(True, "If account exists, reset link sent", status_code=200)


def confirm_password_reset(
    db: Session,
    *,
    token: str,
    new_password: str,
):
    """Reset password using token."""
    try:
        data = decode_token(token, jwt_secret=settings.jwt_secret, jwt_algorithm=settings.jwt_algorithm)
    except Exception as e:
        msg = "Reset link expired" if "expired" in str(e).lower() else "Invalid reset link"
        return make_response(False, msg, status_code=400)

    if data.get("typ") != "reset":
        return make_response(False, "Invalid reset link", status_code=400)

    user = users_repo.get_by_id(db, int(data.get("sub")))
    if not user:
        return make_response(False, "Invalid reset link", status_code=400)

    user.password_hash = hash_password(new_password)
    db.commit()
    
    return make_response(True, "Password updated successfully", status_code=200)
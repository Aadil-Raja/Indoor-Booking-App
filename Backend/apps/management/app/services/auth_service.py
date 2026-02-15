from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from app.repositories import auth_repo, users_repo
from app.core.config import get_settings
from app.services.email_service import send_otp_email, send_password_reset_email
from app.utils.response_utils import make_response
from app.utils.shared_utils import (
    normalize_email,
    hash_password,
    verify_password,
    gen_code_6,
    sha256_str,
    safe_equals,
    issue_access_token,
    issue_reset_token,
    decode_token,
)

settings = get_settings()


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

    token = issue_access_token(
        user_id=user.id,
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

    token = issue_access_token(
        user_id=user.id,
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
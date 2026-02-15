from fastapi import APIRouter, Depends, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.deps.db import get_db
from app.utils.response_utils import make_response
import shared.schemas as schemas
from app.services import auth_service

router = APIRouter()


@router.post("/signup", status_code=status.HTTP_200_OK)
async def signup(
    payload: schemas.UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create account and send OTP."""
    try:
        return await auth_service.signup(
            db,
            email=payload.email,
            password=payload.password,
            name=payload.name,
            role=payload.role,
            background_tasks=background_tasks
        )
    except Exception as e:
        return make_response(False, "Could not create account", status_code=500, error=str(e))


@router.post("/request-code", status_code=status.HTTP_200_OK)
async def request_code(
    payload: schemas.RequestCodeIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Resend OTP."""
    try:
        return await auth_service.request_code(db, email=payload.email, background_tasks=background_tasks)
    except Exception as e:
        return make_response(False, "Could not send code", status_code=500, error=str(e))


@router.post("/verify-code", status_code=status.HTTP_200_OK)
async def verify_code(
    payload: schemas.VerifyCodeIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Verify OTP."""
    try:
        return await auth_service.verify_code(db, email=payload.email, code=payload.code, background_tasks=background_tasks)
    except Exception as e:
        return make_response(False, "Could not verify code", status_code=500, error=str(e))


@router.post("/login/password", status_code=status.HTTP_200_OK)
async def login_password(
    payload: schemas.LoginPasswordIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Password login."""
    try:
        return await auth_service.login_password(db, email=payload.email, password=payload.password, background_tasks=background_tasks)
    except Exception as e:
        return make_response(False, "Login failed", status_code=500, error=str(e))


@router.post("/login/request-code", status_code=status.HTTP_200_OK)
async def login_request_code(
    payload: schemas.RequestCodeIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Send login code."""
    try:
        return await auth_service.login_send_code(db, email=payload.email, background_tasks=background_tasks)
    except Exception as e:
        return make_response(False, "Could not send login code", status_code=500, error=str(e))


@router.post("/login/verify-code", status_code=status.HTTP_200_OK)
async def login_verify_code(
    payload: schemas.VerifyCodeIn,
    db: Session = Depends(get_db)
):
    """Verify login code."""
    try:
        return await auth_service.login_verify_code(db, email=payload.email, code=payload.code)
    except Exception as e:
        return make_response(False, "Could not verify code", status_code=500, error=str(e))


@router.post("/password-reset/request", status_code=status.HTTP_200_OK)
def password_reset_request(
    payload: schemas.PasswordResetRequestIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Request password reset."""
    try:
        return auth_service.request_password_reset(db, email=payload.email, background_tasks=background_tasks)
    except Exception as e:
        return make_response(False, "Could not process request", status_code=500, error=str(e))


@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
def password_reset_confirm(
    payload: schemas.PasswordResetConfirmIn,
    db: Session = Depends(get_db)
):
    """Reset password with token."""
    try:
        return auth_service.confirm_password_reset(db, token=payload.token, new_password=payload.new_password)
    except Exception as e:
        return make_response(False, "Could not reset password", status_code=500, error=str(e))
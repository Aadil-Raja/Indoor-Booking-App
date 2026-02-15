from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from shared.models import EmailOTP

def create_otp(db: Session, *, email: str, code_hash: str, ttl_minutes: int = 10) -> EmailOTP:
    otp = EmailOTP(
        email=email,
        code_hash=code_hash,
        expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
        consumed=False,
        attempts=0,
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)
    return otp

def get_latest_active(db: Session, email: str) -> EmailOTP | None:
    return (
        db.query(EmailOTP)
        .filter(
            EmailOTP.email == email,
            EmailOTP.consumed == False,
            EmailOTP.expires_at > datetime.utcnow(),
        )
        .order_by(EmailOTP.id.desc())
        .first()
    )

def consume(db: Session, otp: EmailOTP):
    otp.consumed = True
    db.commit()

def increment_attempts(db: Session, otp: EmailOTP):
    otp.attempts = (otp.attempts or 0) + 1
    db.commit()

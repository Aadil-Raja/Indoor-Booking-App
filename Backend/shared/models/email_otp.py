from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from .base import Base


class EmailOTP(Base):
    __tablename__ = "email_otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    code_hash = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0)
    consumed = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

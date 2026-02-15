from sqlalchemy.orm import Session
from shared.models import User, UserRole


def get_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def create(db: Session, *, email: str, password_hash: str, name: str, role: str = "customer") -> User:
    user = User(
        email=email,
        password_hash=password_hash,
        Name=name,
        role=UserRole[role],  # Convert string to enum
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    message = Column(Text, nullable=False)
    response = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

import datetime
from typing import List
import uuid
from pydantic import BaseModel
from sqlalchemy import JSON, UUID, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base


Base = declarative_base()
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    stocks = Column(JSON, nullable=True, default=list)  
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"))
    sender = Column(String)
    message = Column(String)
    timestamp = Column(DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc))
    sources = Column(JSON, nullable=True)


class FinanceNews(Base):
    __tablename__ = "finance_news"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), index=True)
    news_data = Column(JSON, nullable=False)

class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class ChatInput(BaseModel):
    session_id: str
    message: str
    tool_type: str


class ChatResponse(BaseModel):
    message: str
    sources: List = []


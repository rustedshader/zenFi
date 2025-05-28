import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UUID,
    Float,
    Date,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(
        DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc)
    )
    stocks = relationship("Stock", back_populates="user", cascade="all, delete-orphan")
    bank_accounts = relationship(
        "BankAccount", back_populates="user", cascade="all, delete-orphan"
    )


class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc)
    )
    user = relationship("User", back_populates="stocks")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(
        DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc)
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"))
    sender = Column(String)
    message = Column(String)
    timestamp = Column(
        DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc)
    )
    sources = Column(JSON, nullable=True)


class FinanceNews(Base):
    __tablename__ = "finance_news"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), index=True)
    news_data = Column(JSON, nullable=False)


class BankAccount(Base):
    __tablename__ = "bank_accounts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    linked_acc_ref = Column(String, nullable=False)
    masked_acc_number = Column(String, nullable=False)
    bank_name = Column(String, nullable=False)
    current_balance = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    account_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc)
    )
    user = relationship("User", back_populates="bank_accounts")
    transactions = relationship(
        "Transaction", back_populates="bank_account", cascade="all, delete-orphan"
    )


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    bank_account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False)
    txn_id = Column(String, nullable=False)
    type = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    current_balance = Column(Float, nullable=False)
    transaction_timestamp = Column(DateTime(timezone=True), nullable=False)
    value_date = Column(Date, nullable=False)
    narration = Column(String, nullable=False)
    reference = Column(String, nullable=False)
    bank_account = relationship("BankAccount", back_populates="transactions")


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


class StockInput(BaseModel):
    symbol: str = Field(..., min_length=1)


class StockSearchInput(BaseModel):
    input_query: str = Field(..., min_length=1)


class LinkBankAccountInput(BaseModel):
    bank_name: str


class BankAccountOutput(BaseModel):
    id: int
    bank_name: str
    masked_acc_number: str
    current_balance: float
    currency: str
    account_type: str
    status: str

    class Config:
        from_attributes = True


class TransactionOutput(BaseModel):
    id: int
    txn_id: str
    type: str
    mode: str
    amount: float
    current_balance: float
    transaction_timestamp: datetime.datetime
    value_date: datetime.date
    narration: str
    reference: str

    class Config:
        from_attributes = True


class AddTransactionInput(BaseModel):
    type: str
    mode: str
    amount: float
    current_balance: float
    narration: str
    reference: str
    transaction_timestamp: datetime.datetime
    value_date: datetime.date


class UpdateTransactionInput(BaseModel):
    type: Optional[str]
    mode: Optional[str]
    amount: Optional[float]
    current_balance: Optional[float]
    narration: Optional[str]
    reference: Optional[str]
    transaction_timestamp: Optional[datetime.datetime]
    value_date: Optional[datetime.date]

import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UUID,
    Float,
    Date,
)
import sqlalchemy
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
    portfolios = relationship(
        "Portfolio", back_populates="user", cascade="all, delete-orphan"
    )
    knowledge_bases = relationship(
        "KnowledgeBase", back_populates="user", cascade="all, delete-orphan"
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
    summary = Column(String, nullable=True)


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


class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    gcs_document_link = Column(String, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc)
    )
    user = relationship("User", back_populates="portfolios")
    assets = relationship(
        "Asset", back_populates="portfolio", cascade="all, delete-orphan"
    )


class Asset(Base):
    __tablename__ = "assets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    portfolio_id = Column(
        UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False
    )
    asset_type = Column(String, nullable=False)
    identifier = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    purchase_price = Column(Float, nullable=False)
    purchase_date = Column(Date, nullable=False)
    current_value = Column(Float, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=datetime.datetime.now(datetime.timezone.utc)
    )
    portfolio = relationship("Portfolio", back_populates="assets")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    meta_data = Column(JSON, nullable=True)  # Renamed from 'metadata'
    table_id = Column(String, nullable=False, unique=True)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    user = relationship("User", back_populates="knowledge_bases")

    __table_args__ = (
        sqlalchemy.UniqueConstraint(
            "user_id", "name", name="uq_user_knowledge_base_name"
        ),
        Index(
            "uq_one_default_knowledge_base_per_user",
            "user_id",
            unique=True,
            postgresql_where=(is_default),
        ),
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_valid = Column(Boolean, default=True, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    user = relationship("User", backref="refresh_tokens")


# --- Pydantic Models ---


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class NewChatInput(BaseModel):
    message: str
    isDeepSearch: bool


class ChatInput(BaseModel):
    session_id: str
    message: str
    isDeepSearch: bool


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
    type: Optional[str] = None
    mode: Optional[str] = None
    amount: Optional[float] = None
    current_balance: Optional[float] = None
    narration: Optional[str] = None
    reference: Optional[str] = None
    transaction_timestamp: Optional[datetime.datetime] = None
    value_date: Optional[datetime.date] = None


# --- New Pydantic Models for Portfolio ---


class AssetBase(BaseModel):
    asset_type: str
    identifier: str
    quantity: float
    purchase_price: float
    purchase_date: datetime.date
    notes: Optional[str] = None


class AssetCreate(AssetBase):
    pass


class AssetOutput(AssetBase):
    id: uuid.UUID
    portfolio_id: uuid.UUID
    created_at: datetime.datetime
    market_value: Optional[float] = None
    total_cost: Optional[float] = None
    profit_loss: Optional[float] = None
    percentage_change: Optional[float] = None
    stock_info: Optional[dict] = None
    news: Optional[list] = None

    class Config:
        from_attributes = True


class PortfolioBase(BaseModel):
    name: str
    description: Optional[str] = None
    gcs_document_link: Optional[str] = None
    is_default: bool = False


class PortfolioCreateInput(BaseModel):
    name: str
    description: Optional[str] = None
    is_default: Optional[bool] = False


class PortfolioCreate(PortfolioBase):
    pass


class PortfolioOutput(PortfolioBase):
    id: uuid.UUID
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class KnowledgeBaseCreateInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
    is_default: bool = False


class SetDefaultKnowledgeBaseInput(BaseModel):
    knowledge_base_id: str


class KnowledgeBaseOutput(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    meta_data: Optional[Dict[str, Any]]
    table_id: str
    is_default: bool
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    message: str
    file_name: str
    status: str


class DocumentChunk(BaseModel):
    doc_id: str
    content: str
    embedding: List[float]
    meta_data: Dict[str, Any]


class QueryRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5
    filter: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    query: str
    knowledge_base_id: str


class NewsBase(BaseModel):
    heading: str
    description: str
    content: str
    sources: str

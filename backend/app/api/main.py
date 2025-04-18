import os
import json
import re
import uuid
import asyncio
from datetime import datetime, timedelta
from uuid import UUID as uuid_UUID

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import sqlalchemy
import uvicorn
from passlib.context import CryptContext
from typing import AsyncGenerator, List

from langchain_google_community import GoogleSearchAPIWrapper
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
    HarmBlockThreshold,
    HarmCategory,
)
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools import BraveSearch
from app.chat_provider.service.chat_service import ChatService
from redis.asyncio import Redis


# Load environment variables
load_dotenv()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
redis_client = Redis.from_url(redis_url, decode_responses=True)


# Database Connection
def connect_tcp_socket() -> sqlalchemy.engine.base.Engine:
    db_host = os.environ.get("INSTANCE_HOST", "some-db-ip")
    db_user = os.environ.get("DB_USER", "postgres")
    db_pass = os.environ.get("DB_PASS", "some-db-password")
    db_name = os.environ.get("DB_NAME", "postgres")
    db_port = os.environ.get("DB_PORT", "5432")
    pool = sqlalchemy.create_engine(
        sqlalchemy.engine.url.URL.create(
            drivername="postgresql+pg8000",
            username=db_user,
            password=db_pass,
            host=db_host,
            port=db_port,
            database=db_name,
        ),
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
    )
    return pool


sync_engine = connect_tcp_socket()
engine = create_async_engine(
    sqlalchemy.engine.url.URL.create(
        drivername="postgresql+asyncpg",
        username=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASS", "some-password"),
        host=os.environ.get("INSTANCE_HOST", "some-db-ip"),
        port=os.environ.get("DB_PORT", "5432"),
        database=os.environ.get("DB_NAME", "postgres"),
    ),
    echo=True,
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


# Database Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"))
    sender = Column(String)
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    sources = Column(JSON, nullable=True)


class FinanceNews(Base):
    __tablename__ = "finance_news"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    news_data = Column(JSON, nullable=False)


@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(sync_engine)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


SECRET_KEY = os.environ.get("SECRET_KEY", "some-secrey-key")
ALGORITHM = "HS256"
JWT_EXPIRE_TIME = int(os.environ.get("JWT_EXPIRE_TIME", 15))


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRE_TIME))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise credentials_exception
    return user


# Pydantic Models
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


class ChatResponse(BaseModel):
    message: str
    sources: List = []


# LLM Safety Settings
safety_settings = {
    HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}

GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY")
BRAVE_API_KEY = os.environ.get("BRAVE_SEARCH_API_KEY")
GOOGLE_SEARCH_API_KEY = os.environ.get("GOOGLE_SEARCH_API_KEY")
TAVILY_SEARCH_API_KEY = os.environ.get("TAVILY_API_KEY")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_SEACH_ENGINE_ID")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro-exp-03-25",
    api_key=GEMINI_API_KEY,
    safety_settings=safety_settings,
)
search = GoogleSearchAPIWrapper(
    google_api_key=GOOGLE_SEARCH_API_KEY, google_cse_id=GOOGLE_CSE_ID
)
tavily_tool = TavilySearchResults(tavily_api_key=TAVILY_SEARCH_API_KEY)
google_embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004", google_api_key=GEMINI_API_KEY
)
brave_search = BraveSearch.from_api_key(
    api_key=BRAVE_API_KEY, search_kwargs={"count": 3}
)


# ChatServiceManager with per-session caching and concurrency limiting
class ChatServiceManager:
    def __init__(self):
        self.chat_services = {}
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent requests

    def get_chat_service(self, session_id: str):
        if session_id not in self.chat_services:
            self.chat_services[session_id] = ChatService(
                llm=llm,
                google_search_wrapper=search,
                google_embedings=google_embeddings,
                tavily_tool=tavily_tool,
                brave_search=brave_search,
            )
        return self.chat_services[session_id]

    async def process_message(
        self, session_id: str, message: str, chat_history: list
    ) -> ChatResponse:
        async with self.semaphore:
            chat_service = self.get_chat_service(session_id)
            result = chat_service.process_input(message)
            if asyncio.iscoroutine(result):
                response = await result
            else:
                response = result
            return ChatResponse(message=response, sources=[])

    async def stream_message(
        self, session_id: str, message: str, chat_history: list
    ) -> AsyncGenerator[str, None]:
        async with self.semaphore:
            chat_service = self.get_chat_service(session_id)
            async for token in chat_service.stream_input(message):
                if token and token.strip():
                    # Small sleep can be adjusted or removed if not needed
                    await asyncio.sleep(0.01)
                    yield token


@app.get("/finance/news")
async def get_finance_news(db: AsyncSession = Depends(get_db)):
    today = datetime.utcnow().date()
    stmt = select(FinanceNews).where(func.date(FinanceNews.date) == today)
    result = await db.execute(stmt)
    news_records = result.scalars().all()
    news_record = news_records[-1] if news_records else None

    if news_record:
        # Assuming news_data is stored as a valid JSON string
        return json.loads(news_record.news_data)

    # Otherwise, fetch news and store as JSON
    chat_service = chat_service_manager.get_chat_service("top_news")
    fetched_news = chat_service.fetch_top_finance_news()

    # Convert any datetime objects to ISO strings
    for item in fetched_news.get("news", []):
        if "publishedAt" in item and isinstance(item["publishedAt"], datetime):
            item["publishedAt"] = item["publishedAt"].isoformat()

    new_record = FinanceNews(date=datetime.utcnow(), news_data=json.dumps(fetched_news))
    db.add(new_record)
    await db.commit()
    return fetched_news


async def get_chat_history(
    session_id: str, db: AsyncSession, force_db: bool = False
) -> List[dict]:
    cache_key = f"chat_history:{session_id}"
    if not force_db:
        history_json = await redis_client.get(cache_key)
        if history_json:
            return json.loads(history_json)
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == uuid_UUID(session_id))
        .order_by(ChatMessage.timestamp)
    )
    result = await db.execute(stmt)
    chat_history = [
        {
            "sender": msg.sender,
            "message": msg.message,
            "timestamp": msg.timestamp.isoformat(),
        }
        for msg in result.scalars().all()
    ]
    await redis_client.set(cache_key, json.dumps(chat_history), ex=300)
    return chat_history


chat_service_manager = ChatServiceManager()


@app.post("/register")
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(
        (User.username == user.username) | (User.email == user.email)
    )
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username or email already exists")
    hashed_password = hash_password(user.password)
    new_user = User(
        username=user.username, email=user.email, hashed_password=hashed_password
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"message": "User created successfully"}


@app.post("/login")
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.username == user.username)
    result = await db.execute(stmt)
    db_user = result.scalars().first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/sessions")
async def create_session(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    new_session = ChatSession(user_id=current_user.id)
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    return {"session_id": str(new_session.id)}


@app.get("/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    stmt = select(ChatSession).where(ChatSession.user_id == current_user.id)
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return [
        {"session_id": str(session.id), "created_at": session.created_at.isoformat()}
        for session in sessions
    ]


@app.post("/chat")
async def send_message(
    input_data: ChatInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        session_uuid = uuid_UUID(input_data.session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session id format")
    stmt = select(ChatSession).where(
        ChatSession.id == session_uuid, ChatSession.user_id == current_user.id
    )
    result = await db.execute(stmt)
    session = result.scalars().first()
    if not session:
        raise HTTPException(
            status_code=404, detail="Session not found or not authorized"
        )
    user_message = ChatMessage(
        session_id=session.id,
        sender="user",
        message=input_data.message,
        timestamp=datetime.utcnow(),
    )
    db.add(user_message)
    await db.commit()
    chat_history = await get_chat_history(input_data.session_id, db)
    response = await chat_service_manager.process_message(
        input_data.session_id, input_data.message, chat_history
    )
    bot_message = ChatMessage(
        session_id=session.id,
        sender="bot",
        message=response.message,
        timestamp=datetime.utcnow(),
        sources=response.sources,
    )
    db.add(bot_message)
    await db.commit()
    # Update Redis cache asynchronously
    asyncio.create_task(get_chat_history(input_data.session_id, db, force_db=True))
    return response


# Precompile token-splitting regex outside the generator
token_splitter = re.compile(r"(\s+)")


@app.post("/chat/stream_http")
async def stream_chat(
    input_data: ChatInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        session_uuid = uuid_UUID(input_data.session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session id format")
    stmt = select(ChatSession).where(
        ChatSession.id == session_uuid, ChatSession.user_id == current_user.id
    )
    result = await db.execute(stmt)
    session = result.scalars().first()
    if not session:
        raise HTTPException(
            status_code=404, detail="Session not found or not authorized"
        )
    user_message = ChatMessage(
        session_id=session.id,
        sender="user",
        message=input_data.message,
        timestamp=datetime.utcnow(),
    )
    db.add(user_message)
    await db.commit()
    chat_history = await get_chat_history(input_data.session_id, db)

    async def stream_generator():
        full_response = ""
        sources = []
        try:
            yield 'data: {"type":"heartbeat"}\n\n'
            async for token in chat_service_manager.stream_message(
                input_data.session_id, input_data.message, chat_history
            ):
                if token:
                    # Use precompiled regex to split tokens if needed
                    parts = token_splitter.split(token)
                    for part in parts:
                        if part:
                            full_response += part
                            yield f'data: {{"type":"token","content":{json.dumps(part)}}}\n\n'
                            await asyncio.sleep(0.01)
            bot_message = ChatMessage(
                session_id=session.id,
                sender="bot",
                message=full_response,
                timestamp=datetime.utcnow(),
                sources=sources,
            )
            db.add(bot_message)
            await db.commit()
            asyncio.create_task(
                get_chat_history(input_data.session_id, db, force_db=True)
            )
            yield 'data: {"type":"complete","finishReason":"stop"}\n\n'
        except asyncio.CancelledError:
            yield 'data: {"type":"error","finishReason":"cancelled"}\n\n'
        except Exception as e:
            print(f"Streaming error: {str(e)}")
            yield f'data: {{"type":"error","finishReason":"error","error":{json.dumps(str(e))}}}\n\n'

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/chat/history")
async def get_chat_history_endpoint(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        session_uuid = uuid_UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session id format")
    stmt = select(ChatSession).where(
        ChatSession.id == session_uuid, ChatSession.user_id == current_user.id
    )
    result = await db.execute(stmt)
    session = result.scalars().first()
    if not session:
        raise HTTPException(
            status_code=404, detail="Session not found or not authorized"
        )
    chat_history = await get_chat_history(session_id, db)
    formatted_history = [
        {
            "id": str(uuid.uuid4()),
            "role": "user" if msg["sender"] == "user" else "assistant",
            "content": msg["message"],
            "timestamp": msg["timestamp"],
            "sources": msg.get("sources", []),
        }
        for msg in chat_history
    ]
    return formatted_history


@app.on_event("shutdown")
async def shutdown_event():
    await redis_client.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

from langchain_google_community import GoogleSearchAPIWrapper
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from app.chat_provider.service.chat_service import ChatService
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import AsyncGenerator
import json
from langchain_google_genai import HarmBlockThreshold, HarmCategory
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools import BraveSearch
from dotenv import load_dotenv
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.future import select
from datetime import datetime
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
import sqlalchemy
import uvicorn
from datetime import timedelta


# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database Connection
def connect_tcp_socket() -> sqlalchemy.engine.base.Engine:
    """Initializes a TCP connection pool for a Cloud SQL instance of Postgres."""
    db_host = os.environ.get("INSTANCE_HOST", "34.29.30.181")
    db_user = os.environ.get("DB_USER", "postgres")
    db_pass = os.environ.get("DB_PASS", ":x~4n1uL\#CsQ}15")
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


# Async engine setup
sync_engine = connect_tcp_socket()
engine = create_async_engine(
    sqlalchemy.engine.url.URL.create(
        drivername="postgresql+asyncpg",
        username=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASS", ":x~4n1uL\#CsQ}15"),
        host=os.environ.get("INSTANCE_HOST", "34.29.30.181"),
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
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    sender = Column(String)
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    sources = Column(JSON, nullable=True)


# Create tables on startup
@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(sync_engine)


# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# JWT Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Database Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# Authentication Dependency
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
    session_id: int
    message: str


class ChatResponse(BaseModel):
    message: str
    sources: list = []


# Safety Settings for LLM
safety_settings = {
    HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}

# Environment Variables
GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY")
BRAVE_API_KEY = os.environ.get("BRAVE_SEARCH_API_KEY")
GOOGLE_SEARCH_API_KEY = os.environ.get("GOOGLE_SEARCH_API_KEY")
TAVILY_SEARCH_API_KEY = os.environ.get("TAVILY_API_KEY")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_SEACH_ENGINE_ID")

# Initialize LLM and Tools
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-pro-exp-02-05",
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


# ChatServiceManager
class ChatServiceManager:
    def __init__(self):
        self.chat_service = ChatService(
            llm=llm,
            google_search_wrapper=search,
            google_embedings=google_embeddings,
            tavily_tool=tavily_tool,
            brave_search=brave_search,
        )

    async def process_message(self, message: str) -> ChatResponse:
        try:
            response = await self.chat_service.process_input(message)
            return ChatResponse(message=response, sources=[])
        except Exception as e:
            return ChatResponse(message=f"An error occurred: {str(e)}", sources=[])

    async def stream_message(self, message: str) -> AsyncGenerator[str, None]:
        async for token in self.chat_service.stream_input(message):
            yield token


chat_service_manager = ChatServiceManager()


# Endpoints
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
    return {"session_id": new_session.id}


@app.post("/chat")
async def send_message(
    input_data: ChatInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ChatSession).where(
        ChatSession.id == input_data.session_id, ChatSession.user_id == current_user.id
    )
    result = await db.execute(stmt)
    session = result.scalars().first()
    if not session:
        raise HTTPException(
            status_code=404, detail="Session not found or not authorized"
        )

    user_message = ChatMessage(
        session_id=input_data.session_id,
        sender="user",
        message=input_data.message,
        timestamp=datetime.utcnow(),
    )
    db.add(user_message)
    await db.commit()

    response = await chat_service_manager.process_message(input_data.message)
    bot_message = ChatMessage(
        session_id=input_data.session_id,
        sender="bot",
        message=response.message,
        timestamp=datetime.utcnow(),
        sources=response.sources,
    )
    db.add(bot_message)
    await db.commit()
    return response


@app.post("/chat/stream_http")
async def stream_chat(
    input_data: ChatInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ChatSession).where(
        ChatSession.id == input_data.session_id, ChatSession.user_id == current_user.id
    )
    result = await db.execute(stmt)
    session = result.scalars().first()
    if not session:
        raise HTTPException(
            status_code=404, detail="Session not found or not authorized"
        )

    user_message = ChatMessage(
        session_id=input_data.session_id,
        sender="user",
        message=input_data.message,
        timestamp=datetime.utcnow(),
    )
    db.add(user_message)
    await db.commit()

    async def stream_generator():
        full_response = ""
        try:
            async for token in chat_service_manager.stream_message(input_data.message):
                if token and token.strip():
                    full_response += token
                    yield f"data: {json.dumps({'content': token})}\n\n"
            bot_message = ChatMessage(
                session_id=input_data.session_id,
                sender="bot",
                message=full_response,
                timestamp=datetime.utcnow(),
                sources=[],
            )
            db.add(bot_message)
            await db.commit()
            yield 'data: {"finishReason":"stop"}\n\n'
        except Exception as e:
            yield f'data: {{"finishReason":"error","error":{json.dumps(str(e))}}}\n\n'

    return StreamingResponse(stream_generator(), media_type="text/event-stream")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

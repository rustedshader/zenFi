import os
import json
import re
import asyncio
import datetime
from uuid import UUID as uuid_UUID

from dotenv import load_dotenv
from fastapi import  Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import sqlalchemy
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
from app.api.api_models import  ChatMessage, ChatResponse, User
from pydantic import SecretStr

load_dotenv()


redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
redis_client = Redis.from_url(redis_url, decode_responses=True)

engine = create_async_engine(
    sqlalchemy.engine.url.URL.create(
        drivername="postgresql+asyncpg",
        username=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASS", "mysecretpassword"),
        host=os.environ.get("INSTANCE_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "5432")),
        database=os.environ.get("DB_NAME", "postgres"),
    ),
    echo=False,
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


SECRET_KEY = os.environ.get("SECRET_KEY", "some-secrey-key")
ALGORITHM = "HS256"
JWT_EXPIRE_TIME = int(os.environ.get("JWT_EXPIRE_TIME", 720))


def create_access_token(sub: str , name: str):
    expire =  datetime.datetime.now(datetime.timezone.utc) + (datetime.timedelta(minutes=JWT_EXPIRE_TIME))
    jwt_payload = {"sub": sub , "name": name, "exp": expire}
    return jwt.encode(jwt_payload, SECRET_KEY, algorithm=ALGORITHM)


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


safety_settings = {
    HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}

GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY","")
BRAVE_API_KEY = os.environ.get("BRAVE_SEARCH_API_KEY", "")
GOOGLE_SEARCH_API_KEY = os.environ.get("GOOGLE_SEARCH_API_KEY")
TAVILY_SEARCH_API_KEY = os.environ.get("TAVILY_API_KEY")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_SEACH_ENGINE_ID")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro-preview-03-25",
    api_key=GEMINI_API_KEY,
    safety_settings=safety_settings,
)
search = GoogleSearchAPIWrapper(
    google_api_key=GOOGLE_SEARCH_API_KEY, google_cse_id=GOOGLE_CSE_ID
)
tavily_tool = TavilySearchResults(tavily_api_key=TAVILY_SEARCH_API_KEY)


google_embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004", google_api_key=SecretStr(GEMINI_API_KEY)
)
brave_search = BraveSearch.from_api_key(
    api_key=BRAVE_API_KEY, search_kwargs={"count": 3}
)


class ChatServiceManager:
    def __init__(self):
        self.chat_services = {}
        self.semaphore = asyncio.Semaphore(5)  

    def get_chat_service(self, session_id: str) -> ChatService:
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
                    yield token

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


token_splitter = re.compile(r"(\s+)")
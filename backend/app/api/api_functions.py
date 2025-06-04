import os
import json
import re
import asyncio
import datetime
from uuid import UUID as uuid_UUID

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import sqlalchemy
from passlib.context import CryptContext
from typing import AsyncGenerator, Dict, List, Optional

from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    HarmBlockThreshold,
    HarmCategory,
)
from app.chat_provider.service.chat_service import ChatService
from redis.asyncio import Redis
from app.api.api_models import Base, ChatMessage, ChatResponse, User
from app.chat_provider.service.deepsearch_service import DeepSearchChatService
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.chat_provider.service.portfolio_summary_service import (
    PortfolioSummaryService,
)
from fastapi import status

load_dotenv()

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
redis_client = Redis.from_url(redis_url, decode_responses=True)

engine = create_async_engine(
    sqlalchemy.engine.url.URL.create(
        drivername="postgresql+asyncpg",
        username=os.environ.get("APP_DB_USER", "postgres"),
        password=os.environ.get("APP_DB_PASS", "mysecretpassword"),
        host=os.environ.get("APP_INSTANCE_HOST", "localhost"),
        port=int(os.environ.get("APP_DB_PORT", "5432")),
        database=os.environ.get("APP_DB_NAME", "postgres"),
    ),
    echo=False,
)
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "some-secrey-key")
ALGORITHM = "HS256"
JWT_EXPIRE_TIME = int(os.environ.get("JWT_EXPIRE_TIME", 86400))


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
        username = payload.get("sub")
        if not isinstance(username, str) or not username:
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

GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")

deepresearch_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro-preview-03-25",
    api_key=GEMINI_API_KEY,
    safety_settings=safety_settings,
)

quicksearch_llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",
    api_key=GEMINI_API_KEY,
    safety_settings=safety_settings,
)


class ChatServiceManager:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(5)

    def get_chat_service(self, isDeepSearch: bool):
        if isDeepSearch:
            self.chat_services = DeepSearchChatService(model=quicksearch_llm)
        else:
            self.chat_services = ChatService(
                model=quicksearch_llm,
            )

    async def process_message(
        self, session_id: str, message: str, user_id: str
    ) -> ChatResponse:
        async with self.semaphore:
            DB_URI = "postgresql://postgres:postgres@localhost:5434/postgres"
            async with AsyncPostgresSaver.from_conn_string(DB_URI) as checkpointer:
                await checkpointer.setup()
                self.chat_services.build_graph(checkpointer=checkpointer)

                result = self.chat_services.stream_input(
                    user_input=message,
                    thread_id=session_id,
                    user_id=user_id,
                    session_id=session_id,
                )

                if isinstance(result, AsyncGenerator):
                    full_response = ""
                    async for chunk in result:
                        full_response += chunk
                    response = full_response
                elif asyncio.iscoroutine(result):
                    response = result
                else:
                    response = result

                return ChatResponse(message=response, sources=[])

    async def stream_message(
        self, session_id: str, message: str, isDeepSearch: bool, user_id: str
    ) -> AsyncGenerator[str, None]:
        if not message or not message.strip():
            yield 'data: {"type":"error","finishReason":"error","error":"Message cannot be empty"}\n\n'
            return

        async with self.semaphore:
            self.get_chat_service(isDeepSearch=isDeepSearch)
            response = await self.process_message(
                session_id=session_id, message=message, user_id=user_id
            )
            if response.message and response.message.strip():
                yield response.message


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


async def generate_ai_portfolio_summary(
    portfolio_name: str,
    portfolio_value: float,
    total_day_gain_inr: float,
    total_gain_inr: float,
    assets: List[Dict],
) -> str:
    cc = ChatServiceManager()

    assets_info = ""
    for asset in assets:
        assets_info += f"""
        - Asset: {asset.get("identifier", "N/A")}
          Type: {asset.get("asset_type", "N/A")}
          Quantity: {asset.get("quantity", 0)}
          Purchase Price: {asset.get("purchase_price", 0)}
          Current Value: {asset.get("value_base", 0)}
          Day Gain: {asset.get("day_gain_base", 0)} ({asset.get("day_gain_percent", 0)}%)
          Total Gain: {asset.get("total_gain_base", 0)} ({asset.get("total_gain_percent", 0)}%)
          News: {", ".join([news.get("title", "") for news in asset.get("news", [])]) if asset.get("news") else "No news available"}
        """

    input_prompt = f"""
    This is a my portfolio generate a report on the insights of this portfolio and its future.
    Portfolio Name: {portfolio_name}
    Portfolio Value: {portfolio_value:.2f} INR
    Total Day Gain: {total_day_gain_inr:.2f} INR
    Total Gain: {total_gain_inr:.2f} INR
    Assets:
    {assets_info}

    Generate a concise and professional Portfolio Summary.
    """

    portfolio_summary_service = cc.stream_message(
        "", isDeepSearch=False, message=input_prompt
    )
    summary = ""
    async for chunk in portfolio_summary_service:
        summary += chunk
    return summary

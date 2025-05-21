import asyncio
import datetime 
import json
import uuid
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import  AsyncSession

from app.api.main import ChatServiceManager, create_access_token, get_chat_history, get_current_user, get_db, hash_password, verify_password
from app.api.api_models import Base, ChatInput, ChatMessage, ChatSession, FinanceNews, User, UserCreate, UserLogin
from uuid import UUID as uuid_UUID
from app.api.main import  token_splitter

chat_service_manager = ChatServiceManager()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication
@app.post("/auth/register")
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

@app.post("/auth/login")
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.username == user.username)
    result = await db.execute(stmt)
    db_user = result.scalars().first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(sub=str(db_user.username), name=str(db_user.username))
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/validate_token")
async def validate_token(
current_user: User = Depends(get_current_user)
):
    if current_user:
        return {"message": "Token is valid", "username": current_user.username}


# Session Management
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

# News
@app.get("/finance/news")
async def get_finance_news(db: AsyncSession = Depends(get_db)):
    today = datetime.datetime.now(datetime.timezone.utc).date()
    stmt = select(FinanceNews).where(func.date(FinanceNews.date) == today)
    result = await db.execute(stmt)
    news_records = result.scalars().all()
    news_record = news_records[-1] if news_records else None

    if news_record:
        return json.loads(news_record.news_data)

    chat_service = chat_service_manager.get_chat_service("top_news")
    fetched_news = chat_service.fetch_top_finance_news()

    for item in fetched_news.get("news", []):
        if "publishedAt" in item and isinstance(item["publishedAt"], datetime):
            item["publishedAt"] = item["publishedAt"].isoformat()

    new_record = FinanceNews(date=datetime.datetime.now(datetime.timezone.utc), news_data=json.dumps(fetched_news))
    db.add(new_record)
    await db.commit()
    return fetched_news

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
        timestamp=datetime.datetime.now(datetime.timezone.utc),
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
        timestamp=datetime.datetime.now(datetime.timezone.utc),
        sources=response.sources,
    )
    db.add(bot_message)
    await db.commit()
    asyncio.create_task(get_chat_history(input_data.session_id, db, force_db=True))
    return response


@app.post("/chat/stream")
async def stream_chat(
    input_data: ChatInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        # Creating a UUID Object from the uuid string and validating it too
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
        timestamp=datetime.datetime.now(datetime.timezone.utc),
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
                timestamp=datetime.datetime.now(datetime.timezone.utc),
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

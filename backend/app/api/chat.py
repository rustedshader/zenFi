import asyncio
import datetime
import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.api_functions import (
    ChatServiceManager,
    get_chat_history,
    get_current_user,
    get_db,
)
from app.api.api_models import (
    ChatInput,
    ChatMessage,
    ChatSession,
    User,
)
from uuid import UUID as uuid_UUID
from app.api.api_functions import token_splitter


chat_router = APIRouter(prefix="/chat")
chat_service_manager = ChatServiceManager()


@chat_router.post("/stream")
async def stream_chat(
    input_data: ChatInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        session_uuid = uuid.UUID(input_data.session_id)
        isDeepResearch = input_data.isDeepSearch
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session id format")

    if not input_data.message or not input_data.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

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

    async def stream_generator():
        yield f'data: {{"type":"session","session_id":{json.dumps(str(session.id))}}}\n\n'
        full_response = ""
        sources = []
        try:
            yield 'data: {"type":"heartbeat"}\n\n'
            async for token in chat_service_manager.stream_message(
                input_data.session_id,
                input_data.message,
                isDeepSearch=isDeepResearch,
                user_id=current_user.id,
            ):
                if token:
                    parts = token_splitter.split(token)
                    for part in parts:
                        if part:
                            full_response += part
                            yield f'data: {{"type":"token","content":{json.dumps(part)}}}\n\n'
                            await asyncio.sleep(0.01)
            if full_response.strip():
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


@chat_router.get("/history")
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

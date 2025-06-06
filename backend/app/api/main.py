# main.py - REMOVE the oauth2_scheme definition from here
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# REMOVE THIS LINE: from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.api_functions import init_db, get_current_user, get_db
from app.api.api_models import ChatSession, User
from app.api.dashboard import dashboard_router
from app.api.stocks import stock_router
from app.api.portfolio import portfolio_router
from app.api.chat import chat_router
from app.api.auth import auth_router
from app.api.knowledge_base import knowledge_base_router
from app.api.news import news_api_router

app = FastAPI(
    title="Your API", description="API with OAuth2 authentication", version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()


# Include auth router FIRST
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(stock_router)
app.include_router(portfolio_router)
app.include_router(chat_router)
app.include_router(knowledge_base_router)
app.include_router(news_api_router)


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
        {
            "session_id": str(session.id),
            "created_at": session.created_at.isoformat(),
            "summary": session.summary,
        }
        for session in sessions
    ]


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

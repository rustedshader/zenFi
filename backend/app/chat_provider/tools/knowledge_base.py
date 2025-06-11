from langchain.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import sqlalchemy
import os
from sqlalchemy import select
from app.api.api_models import KnowledgeBase
from app.chat_provider.service.knowledge_base.knowledege_base import search_enhanced

engine = create_async_engine(
    sqlalchemy.engine.url.URL.create(
        drivername="postgresql+asyncpg",
        username=os.environ.get("APP_DB_USER", "postgres"),
        password=os.environ.get("APP_DB_PASS", "mysecretpassword"),
        host=os.environ.get("APP_INSTANCE_HOST", "postgres"),
        port=int(os.environ.get("APP_DB_PORT", "5432")),
        database=os.environ.get("APP_DB_NAME", "postgres"),
    ),
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@tool
async def query_knowledge_base(query: str, user_id: str) -> str:
    """
    Searches and analyzes the user's personal financial knowledge base, which includes their transaction history,
    spending habits, and financial notes. Use this tool to answer questions about the user's specific financial
    data, such as their largest transactions, spending in a certain category, or recent purchases.
    Input: A natural language query (str) about the user's finances and the user_id (str).
    Output: An AI-generated answer based on the retrieved financial data.
    """
    async for db in get_db():
        # Fix the WHERE clause to properly combine conditions
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.is_default, KnowledgeBase.user_id == int(user_id)
        )
        result = await db.execute(stmt)
        knowledge_base = result.scalar_one_or_none()

        if not knowledge_base:
            return "No default knowledge base found. Please create or select a default knowledge base."

        kb_table_id = str(knowledge_base.table_id)

        if not kb_table_id:
            return "Knowledge base has no table_id set."

        try:
            rag_result = search_enhanced(
                table_id=kb_table_id,
                query=query,
                filter={"context": "some_context"},
            )
            if rag_result["answer"]:
                return rag_result["answer"]
            return "No answer found for the query."
        except Exception as e:
            return f"Error processing query: {str(e)}"

    return "No response generated."

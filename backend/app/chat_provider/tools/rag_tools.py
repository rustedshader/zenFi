from langchain.tools import tool
from sqlalchemy import select

from app.api.api_models import Portfolio
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import sqlalchemy
import os

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


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@tool
async def get_user_portfolio_tool(user_id: str) -> str:
    """
    Fetches the user's default portfolio data, including asset details.
    Input: user_id (str)
    Output: A formatted string with portfolio and asset information.
    """
    stmt = (
        select(Portfolio)
        .where(Portfolio.user_id == int(user_id))
        .where(Portfolio.is_default)
        .options(selectinload(Portfolio.assets))
    )
    async for db in get_db():
        result = await db.execute(stmt)
        portfolios = result.scalars().all()
        if not portfolios:
            return "No default portfolio found for this user."

        output_lines = []
        for portfolio in portfolios:
            created_at = str(portfolio.created_at)
            description = str(portfolio.description)

            output_lines.append(f"Portfolio Name: {portfolio.name}")
            output_lines.append(f"Created At: {created_at}")
            output_lines.append(f"Description: {description}")
            if portfolio.assets:
                output_lines.append("Assets:")
                for asset in portfolio.assets:
                    symbol = getattr(asset, "identifier", "N/A")
                    created_at = getattr(asset, "created_at", "N/A")
                    asset_id = getattr(asset, "id", "N/A")
                    asset_type = getattr(asset, "asset_type", "N/A")
                    quantity = getattr(asset, "quantity", "N/A")
                    purchase_price = getattr(asset, "purchase_price", "N/A")
                    purchase_date = getattr(asset, "purchase_date", "N/A")
                    current_value = getattr(asset, "current_value", "N/A")
                    notes = getattr(asset, "notes", "N/A")
                    output_lines.append(
                        f"  - Asset ID: {asset_id}, Asset Type: {asset_type}, Symbol: {symbol}, Created At: {created_at}, Quantity: {quantity}, Purchase Price: {purchase_price}, Purchase Date: {purchase_date}, Current Value: {current_value}, Notes: {notes}"
                    )
            else:
                output_lines.append("Assets: None")
            output_lines.append("")

        return "\n".join(output_lines).strip()

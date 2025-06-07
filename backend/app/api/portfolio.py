import json
import uuid
from typing import List
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.api_functions import (
    generate_ai_portfolio_summary,
    get_current_user,
    get_db,
)
from app.api.api_models import (
    Asset,
    AssetCreate,
    Portfolio,
    PortfolioCreateInput,
    PortfolioOutput,
    User,
)
from app.chat_provider.tools.finance_tools import (
    get_stock_fastinfo,
)
from google.cloud import storage
from app.chat_provider.extra_functions.exchange import get_exchange_rate
from app.config.config import redis_url

portfolio_router = APIRouter(prefix="/portfolio")

# Initialize Redis Client
redis_client = None
if redis_url:
    try:
        redis_client = aioredis.from_url(redis_url)
        print("Successfully initialized Redis client for portfolio.")
    except Exception as e:
        print(
            f"Warning: Failed to initialize Redis client for portfolio: {e}. Caching will be disabled."
        )
        redis_client = None

# Cache expiration set to 1 hour (3600 seconds)
CACHE_EXPIRATION_SECONDS = 3600


@portfolio_router.post("/create")
async def create_portfolio(
    portfolio_data: PortfolioCreateInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new portfolio for the authenticated user."""
    new_portfolio = Portfolio(
        user_id=current_user.id,
        name=portfolio_data.name,
        description=portfolio_data.description,
        gcs_document_link=None,
    )
    db.add(new_portfolio)
    await db.commit()
    await db.refresh(new_portfolio)
    return {
        "message": "Portfolio created successfully",
        "portfolio_id": new_portfolio.id,
    }


@portfolio_router.post("/{portfolio_id}/assets")
async def create_portfolio_assets(
    portfolio_id: str,
    asset_data: AssetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        # Verify portfolio exists and user is authorized
        stmt = select(Portfolio).where(
            Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id
        )
        result = await db.execute(stmt)
        portfolio = result.scalars().first()
        if not portfolio:
            raise HTTPException(
                status_code=404, detail="Portfolio not found or not authorized"
            )

        # Create and add the new asset
        asset = Asset(portfolio_id=portfolio_id, **asset_data.dict())
        db.add(asset)
        await db.commit()
        await db.refresh(asset)

        # Invalidate the cache for this portfolio
        if redis_client:
            try:
                cache_key = f"portfolio:{portfolio_id}"
                await redis_client.delete(cache_key)
                print(f"Deleted cache for {cache_key}")
            except Exception as e:
                print(
                    f"Redis DELETE error for {cache_key}: {e}. Proceeding without cache invalidation."
                )

        return asset

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create asset: {str(e)}")


@portfolio_router.get("/{portfolio_id}")
async def get_portfolio(
    portfolio_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Query the database to verify portfolio existence and authorization
    stmt = (
        select(Portfolio)
        .where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
        .options(selectinload(Portfolio.assets))
    )
    result = await db.execute(stmt)
    portfolio = result.scalars().first()
    if not portfolio:
        raise HTTPException(
            status_code=404, detail="Portfolio not found or not authorized"
        )

    # Check Redis cache
    cache_key = f"portfolio:{portfolio_id}"
    if redis_client:
        try:
            cached_data_bytes = await redis_client.get(cache_key)
            if cached_data_bytes:
                print(f"Cache hit for {cache_key}")
                return json.loads(cached_data_bytes.decode("utf-8"))
        except Exception as e:
            print(f"Redis GET error for {cache_key}: {e}. Proceeding without cache.")

    # Compute portfolio response if cache miss
    total_value_base = 0.0
    total_day_gain_base = 0.0
    total_gain_base = 0.0
    assets_details = []

    if len(portfolio.assets) == 0:
        portfolio_response = {
            "id": str(portfolio.id),
            "name": portfolio.name,
            "total_value_inr": 0,
            "total_day_gain_inr": 0,
            "total_gain_inr": 0,
            "assets": [],
            "ai_summary": "",
        }
    else:
        for asset in portfolio.assets:
            asset_detail = {
                "identifier": asset.identifier,
                "asset_type": asset.asset_type,
                "quantity": asset.quantity,
                "purchase_price": asset.purchase_price,
                "purchase_date": asset.purchase_date.isoformat()
                if asset.purchase_date
                else None,
                "value_base": 0.0,
                "day_gain_base": 0.0,
                "total_gain_base": 0.0,
                "day_gain_percent": 0.0,
                "total_gain_percent": 0.0,
                "news": [],
            }

            if getattr(asset, "asset_type", None) == "Stock":
                asset_identifier: str = getattr(asset, "identifier", "")
                asset_quantity: float = getattr(asset, "quantity", 0)
                asset_purchase_price: float = getattr(asset, "purchase_price", 0)
                stock_fastinfo = await get_stock_fastinfo(asset_identifier)

                # news_data = fetch_finance_news(asset_identifier)
                news_data = []
                if (
                    isinstance(news_data, dict)
                    and news_data.get("status") == "OK"
                    and news_data.get("data", {}).get("tickerStream", {}).get("stream")
                ):
                    news_items = (
                        news_data.get("data", {})
                        .get("tickerStream", {})
                        .get("stream", [])
                    )
                    for item in news_items:
                        content = item.get("content", {})
                        if content.get("contentType") == "STORY" and content.get(
                            "finance", {}
                        ).get("stockTickers"):
                            tickers = [
                                ticker["symbol"]
                                for ticker in content["finance"]["stockTickers"]
                            ]
                            if asset_identifier in tickers:
                                news_entry = {
                                    "title": content.get("title", ""),
                                    "summary": content.get("summary", ""),
                                    "pubDate": content.get("pubDate", ""),
                                    "url": (content.get("clickThroughUrl") or {}).get(
                                        "url", ""
                                    ),
                                }
                                asset_detail["news"].append(news_entry)

                if not isinstance(stock_fastinfo, str):
                    stock_last_price = stock_fastinfo.last_price
                    stock_previous_close = stock_fastinfo.previous_close
                    stock_currency = stock_fastinfo.currency

                    if isinstance(stock_last_price, float):
                        value_asset_currency = stock_last_price * asset_quantity
                        if isinstance(stock_previous_close, float):
                            day_gain_asset_currency = (
                                stock_last_price - stock_previous_close
                            ) * asset_quantity
                            total_gain_asset_currency = (
                                stock_last_price - asset_purchase_price
                            ) * asset_quantity
                            exchange_rate = get_exchange_rate(stock_currency, "INR")
                            exchange_rate = 1  # Assuming INR for simplicity

                            value_base = value_asset_currency * exchange_rate
                            day_gain_base = day_gain_asset_currency * exchange_rate
                            total_gain_base = total_gain_asset_currency * exchange_rate
                            day_gain_percent = (
                                (
                                    (stock_last_price - stock_previous_close)
                                    / stock_previous_close
                                    * 100
                                )
                                if stock_previous_close != 0
                                else 0
                            )
                            total_gain_percent = (
                                (
                                    (stock_last_price - asset_purchase_price)
                                    / asset_purchase_price
                                    * 100
                                )
                                if asset_purchase_price != 0
                                else 0
                            )

                            asset_detail.update(
                                {
                                    "value_base": value_base,
                                    "day_gain_base": day_gain_base,
                                    "total_gain_base": total_gain_base,
                                    "day_gain_percent": day_gain_percent,
                                    "total_gain_percent": total_gain_percent,
                                }
                            )

                            total_value_base += value_base
                            total_day_gain_base += day_gain_base
                            total_gain_base += total_gain_base

            assets_details.append(asset_detail)

        ai_portfolio_summary = await generate_ai_portfolio_summary(
            portfolio_name=str(getattr(portfolio, "name", "")),
            portfolio_value=total_value_base,
            total_day_gain_inr=total_day_gain_base,
            total_gain_inr=total_gain_base,
            assets=assets_details,
        )

        portfolio_response = {
            "id": str(portfolio.id),
            "name": portfolio.name,
            "total_value_inr": total_value_base,
            "total_day_gain_inr": total_day_gain_base,
            "total_gain_inr": total_gain_base,
            "assets": assets_details,
            "ai_summary": ai_portfolio_summary,
        }

    # Cache the response
    if redis_client:
        try:
            await redis_client.set(
                cache_key,
                json.dumps(portfolio_response).encode("utf-8"),
                ex=CACHE_EXPIRATION_SECONDS,
            )
            print(f"Cached data for {cache_key}")
        except Exception as e:
            print(f"Redis SET error for {cache_key}: {e}. Proceeding without caching.")

    return portfolio_response


@portfolio_router.get("/", response_model=List[PortfolioOutput])
async def list_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Portfolio)
        .where(Portfolio.user_id == current_user.id)
        .options(selectinload(Portfolio.assets))
    )
    result = await db.execute(stmt)
    portfolios = result.scalars().all()
    return portfolios


@portfolio_router.put("/{portfolio_id}/default")
async def update_default_portfolio(
    portfolio_id: str,
    set_default: bool = Query(
        ..., description="Set to true to make default, false to remove default"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Update the default status of a portfolio for the authenticated user.
    Setting a portfolio as default will unset any existing default portfolio.
    """
    stmt = select(Portfolio).where(
        Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id
    )
    result = await db.execute(stmt)
    portfolio = result.scalars().first()

    if not portfolio:
        raise HTTPException(
            status_code=404, detail="Portfolio not found or not authorized"
        )

    if set_default:
        await db.execute(
            update(Portfolio)
            .where(Portfolio.user_id == current_user.id, Portfolio.is_default is True)
            .values(is_default=False)
        )
        portfolio.is_default = True
        message = f"Portfolio {portfolio.name} set as default"
    else:
        if portfolio.is_default:
            portfolio.is_default = False
            message = f"Portfolio {portfolio.name} is no longer default"
        else:
            message = f"Portfolio {portfolio.name} was not default"

    await db.commit()
    await db.refresh(portfolio)

    return {
        "message": message,
        "portfolio_id": portfolio_id,
        "is_default": portfolio.is_default,
    }


@portfolio_router.get("/{portfolio_id}/default_status")
async def get_default_status(
    portfolio_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check if a portfolio is the default for the authenticated user."""
    stmt = select(Portfolio).where(
        Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id
    )
    result = await db.execute(stmt)
    portfolio = result.scalars().first()

    if not portfolio:
        raise HTTPException(
            status_code=404, detail="Portfolio not found or not authorized"
        )

    return {
        "portfolio_id": portfolio_id,
        "is_default": portfolio.is_default,
        "name": portfolio.name,
    }

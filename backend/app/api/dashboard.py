import datetime
import json  # Added for JSON serialization/deserialization
import redis.asyncio as aioredis  # Added for Redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.api_functions import (
    get_current_user,
    get_db,
)
from app.api.api_models import (
    Stock,
    StockInput,
    User,
)
from app.chat_provider.tools.finance_tools import (
    get_stock_last_price,
    get_stock_percentage_change,
    get_stock_point_change,
    get_stock_fastinfo,
)
from app.config.config import redis_url

dashboard_router = APIRouter(prefix="/dashboard")

# Initialize Redis Client
redis_client = None
if redis_url:
    try:
        # For a production app, manage the connection pool via FastAPI's lifespan events
        redis_client = aioredis.from_url(redis_url)
        # You might want to add a ping here in an async startup event to ensure connection
        print("Successfully initialized Redis client.")  # Or use a proper logger
    except Exception as e:
        print(
            f"Warning: Failed to initialize Redis client: {e}. Caching will be disabled."
        )  # Or use a proper logger
        redis_client = None

CACHE_EXPIRATION_SECONDS = 180  # 3 minutes


@dashboard_router.get("/market_status")
async def get_market_status(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    cache_key = "dashboard:market_status"
    if redis_client:
        try:
            cached_data_bytes = await redis_client.get(cache_key)
            if cached_data_bytes:
                print(f"Cache hit for {cache_key}")  # Or use a proper logger
                return json.loads(cached_data_bytes.decode("utf-8"))
        except Exception as e:
            print(
                f"Redis GET error for {cache_key}: {e}. Proceeding without cache."
            )  # Or use a proper logger

    try:
        IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        now_ist = datetime.datetime.now(tz=IST)
        market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
        is_weekday = now_ist.weekday() < 5
        if is_weekday and market_open <= now_ist <= market_close:
            market_status = "active"
        else:
            market_status = "closed"

        response_data = {
            "market_status": market_status,
        }

        if redis_client:
            try:
                await redis_client.set(
                    cache_key,
                    json.dumps(response_data).encode("utf-8"),
                    ex=CACHE_EXPIRATION_SECONDS,
                )
                print(f"Cached data for {cache_key}")  # Or use a proper logger
            except Exception as e:
                print(f"Redis SET error for {cache_key}: {e}")  # Or use a proper logger

        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch dashboard info: {str(e)}"
        )


@dashboard_router.post("/stocks/add")
async def add_stock(
    stock: StockInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        stmt = select(Stock).where(
            Stock.user_id == current_user.id, Stock.symbol == stock.symbol.upper()
        )
        result = await db.execute(stmt)
        existing_stock = result.scalars().first()
        if existing_stock:
            raise HTTPException(status_code=400, detail="Stock already in list")

        stmt = select(Stock).where(Stock.user_id == current_user.id)
        result = await db.execute(stmt)
        user_stocks = result.scalars().all()
        if len(user_stocks) >= 50:
            raise HTTPException(status_code=400, detail="Maximum stock limit reached")

        new_stock = Stock(user_id=current_user.id, symbol=stock.symbol.upper())
        db.add(new_stock)
        await db.commit()

        # Invalidate cache for this user's stocks
        if redis_client:
            cache_key = f"user:{current_user.id}:stocks"
            try:
                await redis_client.delete(cache_key)
                print(f"Invalidated cache for {cache_key}")  # Or use a proper logger
            except Exception as e:
                print(
                    f"Redis DELETE error for {cache_key}: {e}"
                )  # Or use a proper logger

        return {"message": f"Stock {stock.symbol} added successfully"}
    except Exception as e:
        await db.rollback()
        # Ensure HTTPException details are properly propagated if they are the source
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to add stock: {str(e)}")


@dashboard_router.post("/stocks/delete")
async def remove_stock(
    stock: StockInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        stmt = select(Stock).where(
            Stock.user_id == current_user.id, Stock.symbol == stock.symbol.upper()
        )
        result = await db.execute(stmt)
        stock_to_remove = result.scalars().first()
        if not stock_to_remove:
            raise HTTPException(
                status_code=400, detail="Stock not found in user's list"
            )

        await db.delete(stock_to_remove)
        await db.commit()

        # Invalidate cache for this user's stocks
        if redis_client:
            cache_key = f"user:{current_user.id}:stocks"
            try:
                await redis_client.delete(cache_key)
                print(f"Invalidated cache for {cache_key}")  # Or use a proper logger
            except Exception as e:
                print(
                    f"Redis DELETE error for {cache_key}: {e}"
                )  # Or use a proper logger

        return {"message": f"Stock {stock.symbol} removed successfully"}
    except Exception as e:
        await db.rollback()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to remove stock: {str(e)}")


@dashboard_router.get("/stocks")
async def get_stocks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"user:{current_user.id}:stocks"
    if redis_client:
        try:
            cached_data_bytes = await redis_client.get(cache_key)
            if cached_data_bytes:
                print(f"Cache hit for {cache_key}")  # Or use a proper logger
                return json.loads(cached_data_bytes.decode("utf-8"))
        except Exception as e:
            print(
                f"Redis GET error for {cache_key}: {e}. Proceeding without cache."
            )  # Or use a proper logger
    try:
        stmt = select(Stock).where(Stock.user_id == current_user.id)
        result = await db.execute(stmt)
        user_stocks = result.scalars().all()

        stocks_data = []
        for stock_obj in user_stocks:  # Renamed stock to stock_obj to avoid conflict
            if isinstance(stock_obj.symbol, str):
                # These external API calls can be slow, making caching valuable
                stock_points_change = get_stock_point_change(stock_obj.symbol)
                stock_percentage_change = get_stock_percentage_change(stock_obj.symbol)
                stock_fastinfo = await get_stock_fastinfo(stock_obj.symbol)
                fast_info_json = json.loads(stock_fastinfo.toJSON())

                stocks_data.append(
                    {
                        "symbol": stock_obj.symbol,
                        "fast_info": fast_info_json,
                        "stock_points_change": stock_points_change,
                        "stocks_percentage_change": stock_percentage_change,
                    }
                )

        response_data = {"stocks": stocks_data}

        if redis_client:
            try:
                await redis_client.set(
                    cache_key,
                    json.dumps(response_data).encode("utf-8"),
                    ex=CACHE_EXPIRATION_SECONDS,
                )
                print(f"Cached data for {cache_key}")  # Or use a proper logger
            except Exception as e:
                print(f"Redis SET error for {cache_key}: {e}")  # Or use a proper logger

        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stocks: {str(e)}")


@dashboard_router.get("/info")
async def get_dashboard_data(  # Original function name was get_dashboard_data for path /info
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    cache_key = "dashboard:info_data"
    if redis_client:
        try:
            cached_data_bytes = await redis_client.get(cache_key)
            if cached_data_bytes:
                print(f"Cache hit for {cache_key}")  # Or use a proper logger
                return json.loads(cached_data_bytes.decode("utf-8"))
        except Exception as e:
            print(
                f"Redis GET error for {cache_key}: {e}. Proceeding without cache."
            )  # Or use a proper logger

    try:
        IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        now_ist = datetime.datetime.now(tz=IST)
        market_open = now_ist.replace(hour=9, minute=15, second=0, microsecond=0)
        market_close = now_ist.replace(hour=15, minute=30, second=0, microsecond=0)
        is_weekday = now_ist.weekday() < 5

        if is_weekday and market_open <= now_ist <= market_close:
            market_status = "active"
        else:
            market_status = "closed"

        important_stocks = [
            "%5ENSEI",
            "%5EBSESN",
            "%5ENSEBANK",
        ]  # NIFTY, SENSEX, BANKNIFTY
        stock_data = {}
        for stock_symbol in important_stocks:  # Renamed stock to stock_symbol
            try:
                price = get_stock_last_price(stock_symbol)
                points_change = get_stock_point_change(stock_symbol)
                percentage_change = get_stock_percentage_change(stock_symbol)
            except Exception:  # Broad exception for external API calls
                price = None
                points_change = None
                percentage_change = None
            stock_data[stock_symbol] = {
                "last_price": price,
                "points_change": points_change,
                "percentage_change": percentage_change,
            }

        response_data = {
            "market_status": market_status,
            "important_stocks": stock_data,
            "current_time_ist": now_ist.isoformat(),  # Already a string
        }

        if redis_client:
            try:
                await redis_client.set(
                    cache_key,
                    json.dumps(response_data).encode("utf-8"),
                    ex=CACHE_EXPIRATION_SECONDS,
                )
                print(f"Cached data for {cache_key}")  # Or use a proper logger
            except Exception as e:
                print(f"Redis SET error for {cache_key}: {e}")  # Or use a proper logger

        return response_data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch dashboard info: {str(e)}"
        )

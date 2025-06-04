import datetime
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


dashboard_router = APIRouter(prefix="/dashboard")


@dashboard_router.get("/market_status")
async def get_market_status(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
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
        return {
            "market_status": market_status,
        }
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
        return {"message": f"Stock {stock.symbol} added successfully"}
    except Exception as e:
        await db.rollback()
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
        return {"message": f"Stock {stock.symbol} removed successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to remove stock: {str(e)}")


@dashboard_router.get("/stocks")
async def get_stocks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        stmt = select(Stock).where(Stock.user_id == current_user.id)
        result = await db.execute(stmt)
        user_stocks = result.scalars().all()
        stocks_data = []
        for stock in user_stocks:
            if isinstance(stock.symbol, str):
                stock_points_change = get_stock_point_change(stock.symbol)
                stock_percentage_change = get_stock_percentage_change(stock.symbol)
                stock_fastinfo = get_stock_fastinfo(stock.symbol)

                stocks_data.append(
                    {
                        "symbol": stock.symbol,
                        "fast_info": stock_fastinfo,
                        "stock_points_change": stock_points_change,
                        "stocks_percentage_change": stock_percentage_change,
                    }
                )
        return {"stocks": stocks_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stocks: {str(e)}")


@dashboard_router.get("/info")
async def get_dashboard_data(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
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

        important_stocks = ["%5ENSEI", "%5EBSESN", "%5ENSEBANK"]
        stock_data = {}
        for stock in important_stocks:
            try:
                price = get_stock_last_price(stock)
                points_change = get_stock_point_change(stock)
                percentage_change = get_stock_percentage_change(stock)
            except Exception:
                price = None
                points_change = None
                percentage_change = None
            stock_data[stock] = {
                "last_price": price,
                "points_change": points_change,
                "percentage_change": percentage_change,
            }

        return {
            "market_status": market_status,
            "important_stocks": stock_data,
            "current_time_ist": now_ist.isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch dashboard info: {str(e)}"
        )

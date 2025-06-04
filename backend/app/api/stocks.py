import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.api_functions import (
    get_current_user,
    get_db,
)
from app.api.api_models import (
    StockInput,
    StockSearchInput,
    User,
)
from app.chat_provider.tools.finance_tools import (
    get_stock_info,
)
from app.chat_provider.tools.news_tools import (
    fetch_finance_news,
)
import requests

from app.chat_provider.extra_functions.charts import get_charts_data


stock_router = APIRouter(prefix="/stocks")


@stock_router.post("/search")
async def search_stock(
    input: StockSearchInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        input_query = input.input_query.lower()
        search_url = f"https://query2.finance.yahoo.com/v1/finance/search?q={input_query}&lang=en-US&region=US&quotesCount=6&newsCount=3&listsCount=2&enableFuzzyQuery=false&quotesQueryId=tss_match_phrase_query&multiQuoteQueryId=multi_quote_single_token_query&newsQueryId=news_cie_vespa&enableCb=false&enableNavLinks=true&enableEnhancedTrivialQuery=true&enableResearchReports=true&enableCulturalAssets=true&enableLogoUrl=true&enableLists=false&recommendCount=5&enablePrivateCompany=true"
        headers = {
            "User-Agent": "PostmanRuntime/7.44.0",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        response = requests.request("GET", search_url, headers=headers)
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code, detail="Failed to Fetch Stock Data"
            )
        return response.json()["quotes"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching stock: {str(e)}")


@stock_router.post("/info")
async def get_stock_information(
    stock: StockInput,
):
    try:
        symbol = stock.symbol if hasattr(stock, "symbol") else str(stock)
        stock_information = get_stock_info(symbol)
        if isinstance(stock_information, str):
            try:
                stock_information = json.loads(stock_information)
            except Exception:
                pass

        finance_news = fetch_finance_news(symbol)
        charts_data = get_charts_data(symbol)

        return {
            "stock_information": stock_information,
            "news": finance_news,
            "charts_data": charts_data,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch stock info: {str(e)}"
        )

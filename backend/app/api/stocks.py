import json
import requests
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# Assuming config is in a reachable path like 'app.config.config'
# You might need to adjust the import path based on your project structure
from app.config.config import redis_url
from app.api.api_functions import get_current_user, get_db
from app.api.api_models import StockInput, StockSearchInput, User
from app.chat_provider.tools.news_tools import fetch_finance_news
from app.chat_provider.extra_functions.charts import get_charts_data, get_stock_info

stock_router = APIRouter(prefix="/stocks")

# --- Caching Setup ---

# Initialize Redis Client
redis_client = None
if redis_url:
    try:
        redis_client = aioredis.from_url(redis_url)
        print(
            "Successfully initialized Redis client for stocks."
        )  # Or use a proper logger
    except Exception as e:
        print(
            f"Warning: Failed to initialize Redis client: {e}. Caching will be disabled."
        )  # Or use a proper logger
        redis_client = None

# Cache expiration set to 12 hours (43,200 seconds)
CACHE_EXPIRATION_SECONDS = 43200

# --- End Caching Setup ---


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
        charts_data = None
        cache_key = f"charts:{symbol}"

        # 1. Check cache first
        if redis_client:
            try:
                cached_data_bytes = await redis_client.get(cache_key)
                if cached_data_bytes:
                    print(f"Cache hit for {cache_key}")  # Or use a proper logger
                    charts_data = json.loads(cached_data_bytes.decode("utf-8"))
            except Exception as e:
                print(
                    f"Redis GET error for {cache_key}: {e}. Proceeding without cache."
                )  # Or use a proper logger

        # 2. If cache miss, fetch data
        if charts_data is None:
            charts_data = get_charts_data(symbol)
            # 3. Store the newly fetched data in the cache
            if redis_client:
                try:
                    await redis_client.set(
                        cache_key,
                        json.dumps(charts_data).encode("utf-8"),
                        ex=CACHE_EXPIRATION_SECONDS,
                    )
                    print(f"Cached data for {cache_key}")  # Or use a proper logger
                except Exception as e:
                    print(
                        f"Redis SET error for {cache_key}: {e}. Proceeding without caching."
                    )  # Or use a proper logger

        # Fetch other related data (these are not cached in this example)
        stock_information = get_stock_info(symbol)
        if isinstance(stock_information, str):
            try:
                stock_information = json.loads(stock_information)
            except Exception:
                pass

        finance_news = fetch_finance_news(symbol)

        return {
            "stock_information": stock_information,
            "news": finance_news,
            "charts_data": charts_data,  # This is now cached
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch stock info: {str(e)}"
        )

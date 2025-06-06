import json
import datetime
import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config.config import GEMINI_API_KEY, redis_url
from app.chat_provider.service.news_service import FinanceNewsService

news_api_router = APIRouter(prefix="/news")

# Initialize Redis Client
redis_client = None
if redis_url:
    try:
        redis_client = aioredis.from_url(redis_url)
        print("Successfully initialized Redis client.")  # Or use a proper logger
    except Exception as e:
        print(
            f"Warning: Failed to initialize Redis client: {e}. Caching will be disabled."
        )  # Or use a proper logger
        redis_client = None

# Cache expiration set to 12 hours (43,200 seconds)
CACHE_EXPIRATION_SECONDS = 43200

model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", api_key=GEMINI_API_KEY)


@news_api_router.get("/")
async def get_latest_news():
    cache_key = "news:latest"
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
        chat_service = FinanceNewsService(model=model)
        graph = chat_service.build_graph()
        x = await chat_service.get_latest_finance_news(graph)
        if "news_report" not in x:
            raise HTTPException(status_code=500, detail="No news report generated")

        # Ensure news_report is a list of dictionaries (serialize FinanceNews objects)
        response_data = [
            report.dict() if hasattr(report, "dict") else report
            for report in x["news_report"]
        ]

        if redis_client:
            try:
                await redis_client.set(
                    cache_key,
                    json.dumps(response_data).encode("utf-8"),
                    ex=CACHE_EXPIRATION_SECONDS,
                )
                print(f"Cached data for {cache_key}")  # Or use a proper logger
            except Exception as e:
                print(
                    f"Redis SET error for {cache_key}: {e}. Proceeding without caching."
                )  # Or use a proper logger

        return response_data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500, detail=f"Error generating news report: {str(e)}"
        )

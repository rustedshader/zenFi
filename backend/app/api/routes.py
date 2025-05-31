import asyncio
import datetime
import json
import random
from typing import List
import uuid
from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.main import (
    ChatServiceManager,
    create_access_token,
    generate_ai_portfolio_summary,
    get_chat_history,
    get_current_user,
    get_db,
    hash_password,
    verify_password,
)
from app.api.api_models import (
    Asset,
    AssetCreate,
    BankAccount,
    BankAccountOutput,
    ChatInput,
    ChatMessage,
    ChatSession,
    LinkBankAccountInput,
    Portfolio,
    PortfolioCreateInput,
    PortfolioOutput,
    Stock,
    StockInput,
    StockSearchInput,
    Transaction,
    TransactionOutput,
    UpdateTransactionInput,
    User,
    UserCreate,
    UserLogin,
)
from uuid import UUID as uuid_UUID
from app.api.main import token_splitter
from app.api.main import init_db
from app.chat_provider.tools.finance_tools import (
    get_stock_last_price,
    get_stock_percentage_change,
    get_stock_point_change,
    get_stock_info,
    get_stock_fastinfo,
)
from app.chat_provider.account_aggreator.account_data import (
    generate_fake_account_data,
)
from app.chat_provider.tools.news_tools import (
    fetch_finance_news,
)
import requests
from google.cloud import storage
from sqlalchemy.orm import selectinload
from forex_python.converter import CurrencyRates

from app.chat_provider.extra_functions.exchange import get_exchange_rate
from app.chat_provider.extra_functions.charts import get_charts_data


chat_service_manager = ChatServiceManager()
c = CurrencyRates()
app = FastAPI()
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


# Authentication
@app.post("/auth/register")
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(
        (User.username == user.username) | (User.email == user.email)
    )
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username or email already exists")
    hashed_password = hash_password(user.password)
    new_user = User(
        username=user.username, email=user.email, hashed_password=hashed_password
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"message": "User created successfully"}


@app.post("/auth/login")
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    stmt = select(User).where(User.username == user.username)
    result = await db.execute(stmt)
    db_user = result.scalars().first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        sub=str(db_user.username), name=str(db_user.username)
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/auth/validate_token")
async def validate_token(current_user: User = Depends(get_current_user)):
    if current_user:
        return {"message": "Token is valid", "username": current_user.username}


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
        {"session_id": str(session.id), "created_at": session.created_at.isoformat()}
        for session in sessions
    ]


# News
# @app.get("/finance/news")
# async def get_finance_news(db: AsyncSession = Depends(get_db)):
#     today = datetime.datetime.now(datetime.timezone.utc).date()
#     stmt = select(FinanceNews).where(func.date(FinanceNews.date) == today)
#     result = await db.execute(stmt)
#     news_records = result.scalars().all()
#     news_record = news_records[-1] if news_records else None

#     if news_record:
#         return json.loads(news_record.news_data)

#     chat_service = chat_service_manager.get_chat_service("top_news")
#     fetched_news = chat_service.fetch_top_finance_news()

#     for item in fetched_news.get("news", []):
#         if "publishedAt" in item and isinstance(item["publishedAt"], datetime):
#             item["publishedAt"] = item["publishedAt"].isoformat()

#     new_record = FinanceNews(date=datetime.datetime.now(datetime.timezone.utc), news_data=json.dumps(fetched_news))
#     db.add(new_record)
#     await db.commit()
#     return fetched_news

# ---------------------------------

# Portfolio Related Stuff

portfolio_router = APIRouter(prefix="/portfolio")


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


@portfolio_router.post("/{portfolio_id}/upload_pdf")
async def upload_pdf(
    portfolio_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF to an existing portfolio and store it in GCP bucket."""
    stmt = select(Portfolio).where(
        Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id
    )
    result = await db.execute(stmt)
    portfolio = result.scalars().first()
    if not portfolio:
        raise HTTPException(
            status_code=404, detail="Portfolio not found or not authorized"
        )

    try:
        client = storage.Client()
        bucket = client.bucket("portfolios_bucket")
        if file.filename and "." in file.filename:
            file_extension = file.filename.split(".")[-1]
        else:
            file_extension = "pdf"
        blob_name = f"user_{current_user.id}/portfolio_{portfolio_id}/{uuid.uuid4()}.{file_extension}"
        blob = bucket.blob(blob_name)
        blob.upload_from_file(file.file, content_type=file.content_type)
        gcs_url = f"https://storage.googleapis.com/portfolios_bucket/{blob_name}"

        setattr(portfolio, "gcs_document_link", gcs_url)
        await db.commit()
        return {"message": "PDF uploaded successfully", "gcs_document_link": gcs_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload PDF: {str(e)}")


@portfolio_router.post("/{portfolio_id}/assets")
async def create_portfolio_assets(
    portfolio_id: str,
    asset_data: AssetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        stmt = select(Portfolio).where(
            Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id
        )
        result = await db.execute(stmt)
        portfolio = result.scalars().first()
        if not portfolio:
            raise HTTPException(
                status_code=404, detail="Portfolio not found or not authorized"
            )
        asset = Asset(portfolio_id=portfolio_id, **asset_data.dict())
        db.add(asset)
        await db.commit()
        await db.refresh(asset)
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

    total_value_base = 0.0
    total_day_gain_base = 0.0
    total_gain_base = 0.0
    assets_details = []

    for asset in portfolio.assets:
        asset: Asset = asset
        asset_detail = {
            "identifier": asset.identifier,
            "asset_type": asset.asset_type,
            "quantity": asset.quantity,
            "purchase_price": asset.purchase_price,
            "purchase_date": asset.purchase_date,
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
            stock_fastinfo = get_stock_fastinfo(asset_identifier)

            news_data = fetch_finance_news(asset_identifier)
            if (
                isinstance(news_data, dict)
                and news_data.get("status") == "OK"
                and news_data.get("data", {}).get("tickerStream", {}).get("stream")
            ):
                news_items = (
                    news_data.get("data", {}).get("tickerStream", {}).get("stream", [])
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
            total_gain_inr=total_day_gain_base,
            assets=assets_details,
        )

    portfolio_response = {
        "id": portfolio.id,
        "name": portfolio.name,
        "total_value_inr": total_value_base,
        "total_day_gain_inr": total_day_gain_base,
        "total_gain_inr": total_gain_base,
        "assets": assets_details,
        "ai_summary": ai_portfolio_summary,
    }

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


# ---------------------------------

# Stocks Related Stuff
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


# --------------------------------#

# Dashboard Management Functions


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


# --------------------------------#

# Bank Account Related Stuff

bank_account_link_router = APIRouter(prefix="/bank_account")


@bank_account_link_router.post("/link")
async def link_bank_account(
    input_data: LinkBankAccountInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bank_name = input_data.bank_name
    linked_acc_ref = f"{bank_name.replace(' ', '_')}_{random.randint(100000, 999999)}"

    stmt = select(BankAccount).where(BankAccount.linked_acc_ref == linked_acc_ref)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=400, detail="Generated reference already exists"
        )

    account_data = generate_fake_account_data(transaction_count=50)
    account_data["Account"]["_linkedAccRef"] = linked_acc_ref
    summary = account_data["Account"]["Summary"]

    new_bank_account = BankAccount(
        user_id=current_user.id,
        linked_acc_ref=linked_acc_ref,
        masked_acc_number=account_data["Account"]["_maskedAccNumber"],
        bank_name=bank_name,
        current_balance=float(summary["_currentBalance"]),
        currency=summary["_currency"],
        account_type=summary["_type"],
        status=summary["_status"],
    )
    db.add(new_bank_account)
    await db.commit()
    await db.refresh(new_bank_account)

    transactions = account_data["Account"]["Transactions"]["Transaction"]
    for txn in transactions:
        new_transaction = Transaction(
            bank_account_id=new_bank_account.id,
            txn_id=txn["_txnId"],
            type=txn["_type"],
            mode=txn["_mode"],
            amount=float(txn["_amount"]),
            current_balance=float(txn["_currentBalance"]),
            transaction_timestamp=datetime.datetime.fromisoformat(
                txn["_transactionTimestamp"]
            ),
            value_date=datetime.datetime.fromisoformat(txn["_valueDate"]).date(),
            narration=txn["_narration"],
            reference=txn["_reference"],
        )
        db.add(new_transaction)
    await db.commit()

    return {
        "message": "Bank account linked successfully",
        "bank_account_id": new_bank_account.id,
    }


@bank_account_link_router.get("/", response_model=List[BankAccountOutput])
async def get_bank_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BankAccount).where(BankAccount.user_id == current_user.id)
    result = await db.execute(stmt)
    bank_accounts = result.scalars().all()
    return [BankAccountOutput.from_orm(account) for account in bank_accounts]


@bank_account_link_router.get(
    "/{bank_account_id}/transactions", response_model=List[TransactionOutput]
)
async def get_transactions(
    bank_account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BankAccount).where(
        BankAccount.id == bank_account_id, BankAccount.user_id == current_user.id
    )
    result = await db.execute(stmt)
    bank_account = result.scalars().first()
    if not bank_account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    stmt = select(Transaction).where(Transaction.bank_account_id == bank_account_id)
    result = await db.execute(stmt)
    transactions = result.scalars().all()
    return [TransactionOutput.from_orm(txn) for txn in transactions]


@bank_account_link_router.put("/transactions/{transaction_id}")
async def update_transaction(
    transaction_id: int,
    input_data: UpdateTransactionInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Transaction).where(Transaction.id == transaction_id)
    result = await db.execute(stmt)
    transaction = result.scalars().first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    stmt = select(BankAccount).where(
        BankAccount.id == transaction.bank_account_id,
        BankAccount.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    bank_account = result.scalars().first()
    if not bank_account:
        raise HTTPException(
            status_code=403, detail="Not authorized to update this transaction"
        )

    update_data = input_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(transaction, key, value)
    await db.commit()
    await db.refresh(transaction)

    if "current_balance" in update_data:
        bank_account.current_balance = transaction.current_balance
        await db.commit()

    return {"message": "Transaction updated successfully"}


@bank_account_link_router.delete("/transactions/{transaction_id}")
async def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Transaction).where(Transaction.id == transaction_id)
    result = await db.execute(stmt)
    transaction = result.scalars().first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    stmt = select(BankAccount).where(
        BankAccount.id == transaction.bank_account_id,
        BankAccount.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    bank_account = result.scalars().first()
    if not bank_account:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this transaction"
        )

    await db.delete(transaction)
    await db.commit()

    return {"message": "Transaction deleted successfully"}


# --------------------------------#

# Chat

chat_router = APIRouter(prefix="/chat")


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
                input_data.session_id, input_data.message, isDeepSearch=isDeepResearch
            ):
                if token:
                    parts = token_splitter.split(token)
                    for part in parts:
                        if part:
                            full_response += part
                            yield f'data: {{"type":"token","content":{json.dumps(part)}}}\n\n'
                            await asyncio.sleep(0.01)
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


# --------------------------------#


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


app.include_router(dashboard_router)
app.include_router(stock_router)
app.include_router(portfolio_router)
app.include_router(chat_router)

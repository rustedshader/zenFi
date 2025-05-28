import asyncio
import datetime
import json
import random
from typing import List
import uuid
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.main import (
    ChatServiceManager,
    create_access_token,
    get_chat_history,
    get_current_user,
    get_db,
    hash_password,
    verify_password,
)
from app.api.api_models import (
    BankAccount,
    BankAccountOutput,
    ChatInput,
    ChatMessage,
    ChatSession,
    LinkBankAccountInput,
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
    yahoo_finance_news_tool,
    duckduckgo_news_search_tool,
)
import requests

chat_service_manager = ChatServiceManager()

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

        try:
            yahoo_finance_news = yahoo_finance_news_tool.invoke(symbol)
            if isinstance(yahoo_finance_news, str):
                try:
                    yahoo_finance_news = json.loads(yahoo_finance_news)
                except Exception:
                    pass
        except Exception:
            yahoo_finance_news = []

        try:
            duckduckgo_finance_news = duckduckgo_news_search_tool.invoke(symbol)
            if isinstance(duckduckgo_finance_news, str):
                try:
                    duckduckgo_finance_news = json.loads(duckduckgo_finance_news)
                except Exception:
                    pass
        except Exception:
            duckduckgo_finance_news = []

        return {
            "stock_information": stock_information,
            "yahoo_finance_news": yahoo_finance_news,
            "duckduckgo_finance_news": duckduckgo_finance_news,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch stock info: {str(e)}"
        )


# --------------------------------#

# Dashboard Management Functions


dashboard_router = APIRouter(prefix="/dashboard")


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
@app.post("/chat/stream")
async def stream_chat(
    input_data: ChatInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        # Creating a UUID Object from the uuid string and validating it too
        session_uuid = uuid_UUID(input_data.session_id)
        tool_type = input_data.tool_type
        print(f"Tool type: {tool_type}")
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
        full_response = ""
        sources = []
        try:
            yield 'data: {"type":"heartbeat"}\n\n'
            async for token in chat_service_manager.stream_message(
                input_data.session_id, input_data.message, tool_type
            ):
                if token:
                    # Use precompiled regex to split tokens if needed
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


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/chat/history")
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


app.include_router(dashboard_router)
app.include_router(stock_router)

import datetime
import random
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.api_functions import (
    get_current_user,
    get_db,
)
from app.api.api_models import (
    BankAccount,
    BankAccountOutput,
    LinkBankAccountInput,
    Transaction,
    TransactionOutput,
    UpdateTransactionInput,
    User,
)
from app.chat_provider.account_aggreator.account_data import (
    generate_fake_account_data,
)


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

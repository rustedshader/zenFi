# app/api/auth.py - Clean auth router without OAuth2PasswordBearer definition
import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.api_models import (
    User,
    UserCreate,
)
from app.chat_provider.auth import (
    authenticate_user,
    create_refresh_token,
    store_refresh_token,
)
from app.chat_provider.auth import create_access_token
from app.api.api_functions import get_current_user, get_db, hash_password

# Clean router definition
auth_router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={404: {"description": "Not found"}},
)


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    stmt = select(User).where(
        (User.username == user.username) | (User.email == user.email)
    )
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists",
        )

    hashed_password = hash_password(user.password)
    new_user = User(
        username=user.username, email=user.email, hashed_password=hashed_password
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"message": "User created successfully", "username": new_user.username}


@auth_router.post("/login")
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db),
):
    print(form_data)
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # if not user.is_allowed:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Inactive user!! Please connect to Data Science team for activation."
    #     )
    # Create access token
    access_token_expires = datetime.timedelta(minutes=3600)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    # Create refresh token
    refresh_token_expires = datetime.timedelta(days=1)
    refresh_token = create_refresh_token(
        data={
            "sub": user.email,
        },
        expires_delta=refresh_token_expires,
    )

    await store_refresh_token(db, user.id, refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@auth_router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "username": current_user.username,
        "email": current_user.email,
        "id": current_user.id,
    }


@auth_router.post("/validate_token")
async def validate_token(current_user: User = Depends(get_current_user)):
    """Validate if the current token is valid"""
    return {
        "valid": True,
        "message": "Token is valid",
        "username": current_user.username,
    }

from typing import Optional, Union

from jose import JWTError
from sqlalchemy import select

from app.api.api_models import RefreshToken, User, UserCreate
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from passlib.context import CryptContext
import datetime
import os


MAX_REFRESH_TOKEN_USES = 5

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "some-secrey-key")
ALGORITHM = "HS256"
JWT_EXPIRE_TIME = int(os.environ.get("JWT_EXPIRE_TIME", 86400))


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(
    data: dict, expires_delta: Optional[datetime.timedelta] = None
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            minutes=15
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def create_refresh_token(
    data: dict, expires_delta: Optional[datetime.timedelta] = None
) -> str:
    """Create JWT refresh token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            days=1
        )

    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm="HS256",
    )
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def decode_token(token: str) -> Union[dict, None]:
    """Decode and verify JWT token."""
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return (
            decoded_token
            if decoded_token["exp"] >= datetime.datetime.utcnow().timestamp()
            else None
        )
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Union[dict, None]:
    """Decode and verify JWT refresh token."""
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if (
            decoded_token["exp"] >= datetime.datetime.utcnow().timestamp()
            and decoded_token.get("type") == "refresh"
        ):
            return decoded_token
        return None
    except JWTError:
        return None


async def store_refresh_token(
    db: AsyncSession, user_id: int, token: str
) -> RefreshToken:
    """Store refresh token in database."""
    # First, invalidate all existing refresh tokens for the user
    existing_tokens = select(RefreshToken).where(
        RefreshToken.user_id == user_id, RefreshToken.is_valid
    )
    result = await db.execute(existing_tokens)
    for existing_token in result.scalars().all():
        existing_token.is_valid = False
        db.add(existing_token)

    # Create new refresh token
    refresh_token = RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(days=1),
        is_valid=True,
        usage_count=0,
    )
    db.add(refresh_token)
    await db.commit()
    await db.refresh(refresh_token)
    return refresh_token


async def verify_refresh_token_db(
    db: AsyncSession, token: str
) -> Union[RefreshToken, None]:
    """Verify refresh token in database and update usage count."""
    db_token = (
        (
            await db.execute(
                select(RefreshToken).where(
                    RefreshToken.token == token, RefreshToken.is_valid
                )
            )
        )
        .scalars()
        .first()
    )

    if not db_token:
        return None

    expiry = db_token.expires_at
    expiry = expiry.replace(tzinfo=datetime.timezone.utc)

    # Check if token is expired
    if expiry < datetime.datetime.now(datetime.timezone.utc):
        db_token.is_valid = False
        await db.commit()
        return None

    # Check usage count
    if db_token.usage_count >= MAX_REFRESH_TOKEN_USES:
        db_token.is_valid = False
        await db.commit()
        return None

    # Update usage count and last used timestamp
    db_token.usage_count += 1
    db_token.last_used_at = datetime.datetime.now(datetime.timezone.utc)
    await db.commit()
    await db.refresh(db_token)

    return db_token


async def invalidate_refresh_token(db: AsyncSession, token: str) -> bool:
    """Invalidate a refresh token."""
    db_token = (
        (await db.execute(select(RefreshToken).where(RefreshToken.token == token)))
        .scalars()
        .first()
    )

    if db_token:
        db_token.is_valid = False
        await db.commit()
        return True
    return False


async def invalidate_user_refresh_token(db: AsyncSession, token: str) -> bool:
    """Invalidate a refresh token."""
    db_token = (
        (await db.execute(select(RefreshToken).where(RefreshToken.token == token)))
        .scalars()
        .first()
    )

    if db_token:
        db_token.is_valid = False
        await db.commit()
        return True
    return False


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """Get user by username."""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalars().first()


async def authenticate_user(
    db: AsyncSession, username: str, password: str
) -> Optional[User]:
    """Authenticate user with email and password."""
    user = await get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_new_user(
    db: AsyncSession, user_create: UserCreate, company_id: Optional[int] = None
) -> User:
    """Create new user."""

    # Create user instance
    db_user = User(
        email=user_create.email,
        hashed_password=get_password_hash(user_create.password),
        username=user_create.username,
    )

    # Add to database
    await db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    return db_user

import os
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, APIRouter
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api.api_models import User, UserCreate, UserLogin
from app.api.api_functions import get_db, hash_password, verify_password
import datetime

load_dotenv()

# Ensure a single SECRET_KEY
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secure-secret-key")
ALGORITHM = "HS256"
JWT_EXPIRE_TIME = int(os.environ.get("JWT_EXPIRE_TIME", 1800))  # 30 minutes

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
auth_router = APIRouter(prefix="/auth")


def create_access_token(sub: str, name: str):
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        seconds=JWT_EXPIRE_TIME
    )
    jwt_payload = {"sub": sub, "name": name, "exp": expire}
    return jwt.encode(jwt_payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not isinstance(username, str) or not username:
            raise credentials_exception
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        print("JWT Error:", str(e))  # Log for debugging
        raise credentials_exception
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise credentials_exception
    return user


@auth_router.post("/register")
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


@auth_router.post("/login")
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


@auth_router.post("/validate_token")
async def validate_token(current_user: User = Depends(get_current_user)):
    return {"message": "Token is valid", "username": current_user.username}

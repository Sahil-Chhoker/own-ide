from datetime import timedelta
from core.config import settings
from core.hashing import Hasher
from core.security import create_access_token
from db.session import get_client
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestFormStrict
import jwt
from schemas.token import TokenData, Token
from db.base import get_db
from schemas.user import UserInDB, UserOut
from pymongo.asynchronous.database import AsyncDatabase

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/user/login")


async def get_user(username: str):
    db = await get_db()
    query = await db.users.find_one({"username": username})
    if query:
        return UserInDB(**query)
    return False

async def authenticate_user(username: str, password: str):
    user = await get_user(username)
    print(user)
    if not user:
        return False
    if not Hasher.verify_password(password, user.hashed_password):
        return False
    return user


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncDatabase = Depends(get_db)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")

        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.InvalidTokenError:
        raise credentials_exception
    user = await get_user(username=token_data.username) # type: ignore
    if user is None:
        raise credentials_exception
    return user # type: ignore


@router.post("/user/login", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestFormStrict = Depends(), db: AsyncDatabase = Depends(get_db)
) -> Token:
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

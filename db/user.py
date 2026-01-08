from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import jwt
from core.config import settings
from schemas.token import TokenData
from db.session import get_db
from schemas.user import UserIn, UserInDB, UserOut
from core.hashing import Hasher
from pymongo.asynchronous.database import AsyncDatabase
from fastapi import HTTPException, status


async def create_new_user(user: UserIn, db: AsyncDatabase) -> UserOut:
    query = await db.users.find_one({"username": user.username})
    if query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists with this username.",
        )

    new_user = UserInDB(
        **user.model_dump(), hashed_password=Hasher.get_password_hash(user.password)
    )
    await db.users.insert_one(new_user.model_dump())
    return UserOut(**new_user.model_dump())


async def delete_user(username: str, db: AsyncDatabase) -> dict:
    result = await db.users.delete_one({"username": username})
    if result.deleted_count == 0:
        return {"error": "User not found"}
    return {"message": f"User {username} deleted successfully"}


async def get_user(username: str):
    db = await get_db()
    query = await db.users.find_one({"username": username})
    if query:
        return UserInDB(**query)
    return False


async def authenticate_user(username: str, password: str):
    user = await get_user(username)
    if not user:
        return False
    if not Hasher.verify_password(password, user.hashed_password):
        return False
    return user


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/user/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncDatabase = Depends(get_db)
) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username = payload.get("sub")

        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.InvalidTokenError:
        raise credentials_exception
    user = await get_user(username=token_data.username)  # type: ignore
    if user is None:
        raise credentials_exception
    return user  # type: ignore

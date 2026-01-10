from fastapi import APIRouter, HTTPException, Depends, status
from schemas.user import UserIn, UserOut
from db.user import create_new_user, delete_user, get_current_user
from pymongo.asynchronous.database import AsyncDatabase
from db.db_session import get_db

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserIn,
    db: AsyncDatabase = Depends(get_db),
):
    new_user = await create_new_user(user=user, db=db)
    return new_user


@router.get("/profile", response_model=UserOut)
async def get_user_profile(
    current_user: UserIn = Depends(get_current_user),
):
    return current_user


@router.delete("/", status_code=status.HTTP_200_OK)
async def delete_current_user(
    db: AsyncDatabase = Depends(get_db),
    current_user: UserIn = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    message = await delete_user(username=current_user.username, db=db)

    if message.get("error"):
        raise HTTPException(
            detail=message.get("error"),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return {
        "message": f"User deleted successfully with username {current_user.username}"
    }

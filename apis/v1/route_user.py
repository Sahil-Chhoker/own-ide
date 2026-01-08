from fastapi import APIRouter, HTTPException, Depends, status
from schemas.user import UserIn, UserOut
from apis.v1.route_login import get_current_user
from db.user import create_new_user, delete_user
from pymongo.asynchronous.database import AsyncDatabase
from db.base import get_db

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


@router.delete("/{username}", status_code=status.HTTP_200_OK)
async def delete_current_user(
    username: str,
    db: AsyncDatabase = Depends(get_db),
    current_user: UserIn = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    if username != current_user.username:
        raise HTTPException(
            detail="Only the owner can delete the user.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    message = await delete_user(username=username, db=db)

    if message.get("error"):
        raise HTTPException(
            detail=message.get("error"),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return {"message": f"User deleted successfully with id {username}"}

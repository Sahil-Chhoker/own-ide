from schemas.user import UserIn, UserInDB, UserOut
from core.hashing import Hasher
from pymongo.asynchronous.database import AsyncDatabase
from fastapi import HTTPException, status

async def create_new_user(user: UserIn, db: AsyncDatabase) -> UserOut:
    query = await db.users.find_one({"username": user.username})
    if query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="User already exists with this username."
        )
    
    new_user = UserInDB(
        **user.model_dump(), 
        hashed_password=Hasher.get_password_hash(user.password)
    )
    await db.users.insert_one(new_user.model_dump())
    return UserOut(**new_user.model_dump())


async def delete_user(username: str, db: AsyncDatabase) -> dict:
    result = await db.users.delete_one({"username": username})
    if result.deleted_count == 0:
        return {"error": "User not found"}
    return {"message": f"User {username} deleted successfully"}

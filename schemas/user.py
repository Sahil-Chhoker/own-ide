from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None

    class Config:
        orm_mode = True

class UserIn(UserBase):
    password: str = Field(..., min_length=8)


class UserOut(UserBase):
    pass


class UserInDB(UserBase):
    hashed_password: str
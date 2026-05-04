from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None


class UserIn(UserBase):
    password: str = Field(..., min_length=8)


class UserOut(UserBase):
    pass


class UserInDB(UserBase):
    """Internal auth model stored in MongoDB."""

    hashed_password: str

    # Ignore Mongo fields we don't expose (e.g. `_id`).
    model_config = ConfigDict(extra="ignore")

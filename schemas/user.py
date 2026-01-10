from typing import Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None


class UserIn(UserBase):
    password: str = Field(..., min_length=8)


class UserOut(UserBase):
    pass


class UserInDB(UserBase):
    # using an alias to map MongoDB's _id to this id field
    id: str = Field(alias="_id")
    hashed_password: str

    # This allows Pydantic to accept a dictionary where the key is "_id"
    # and map it to the attribute "id"
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    @field_validator("id", mode="before")
    @classmethod
    def convert_objectid(cls, v: Any) -> str:
        return str(v) if v else v

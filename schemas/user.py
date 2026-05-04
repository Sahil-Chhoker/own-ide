from typing import Any
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None


class UserIn(UserBase):
    password: str = Field(..., min_length=8)


class UserOut(UserBase):
    pass


class UserInDB(UserBase):
    """User as stored in MongoDB. Documents use `_id`; we expose it as `id`."""

    id: str
    hashed_password: str

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    @model_validator(mode="before")
    @classmethod
    def map_mongo_id(cls, data: Any) -> Any:
        if isinstance(data, dict) and "_id" in data and "id" not in data:
            return {**data, "id": data["_id"]}
        return data

    @field_validator("id", mode="before")
    @classmethod
    def objectid_to_str(cls, v: Any) -> str:
        if v is None:
            raise ValueError("User id is required")
        return str(v)

import re
from typing import Optional
from pydantic import (
    BaseModel,
    EmailStr,
    field_validator,
    ConfigDict
)


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    is_admin: bool = False
    department_id: Optional[int] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:

        if len(v) < 10:
            raise ValueError(
                "Password must be at least 10 characters long"
            )

        if not re.search(r"[A-Z]", v):
            raise ValueError(
                "Password must contain at least one uppercase letter"
            )

        if not re.search(r"[a-z]", v):
            raise ValueError(
                "Password must contain at least one lowercase letter"
            )

        if not re.search(r"\d", v):
            raise ValueError(
                "Password must contain at least one number"
            )

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError(
                "Password must contain at least one special character"
            )

        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    is_admin: bool
    department_id: Optional[int]

    model_config = ConfigDict(
        from_attributes=True
    )


class Token(BaseModel):
    access_token: str
    token_type: str
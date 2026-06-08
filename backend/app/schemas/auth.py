from pydantic import BaseModel, Field

from app.models import User


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class LoginSuccessResponse(BaseModel):
    success: bool


class UserSchema(BaseModel):
    username: str
    first_name: str
    last_name: str
    is_superuser: bool

    @classmethod
    def from_user(cls, user: User) -> "UserSchema":
        return cls(
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            is_superuser=user.is_superuser,
        )


class AuthedResponse(BaseModel):
    user: UserSchema
    membership: None = None


class CSRFResponse(BaseModel):
    details: str

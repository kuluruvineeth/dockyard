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


class UserExistenceResponse(BaseModel):
    exists: bool


class UserCreationRequest(BaseModel):
    username: str = Field(min_length=1, max_length=150, pattern=r"^[\w.@+-]+$")
    password: str = Field(min_length=8)


class UserCreatedResponse(BaseModel):
    detail: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=1)


class ChangePasswordResponse(BaseModel):
    success: bool


class UpdateProfileRequest(BaseModel):
    username: str | None = Field(
        default=None, min_length=1, max_length=150, pattern=r"^[\w.@+-]+$"
    )
    first_name: str | None = None
    last_name: str | None = None

import bcrypt
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.models.base import Base, TimestampedModel


class User(Base, TimestampedModel):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(150), default="")
    last_name: Mapped[str] = mapped_column(String(150), default="")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def set_password(self, raw_password: str) -> None:
        salt = bcrypt.gensalt(rounds=settings.password_hash_rounds)
        self.password = bcrypt.hashpw(raw_password.encode(), salt).decode()

    def check_password(self, raw_password: str) -> bool:
        try:
            return bcrypt.checkpw(raw_password.encode(), self.password.encode())
        except (ValueError, AttributeError):
            return False

import base64
import hashlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampedModel, generate_id


class SSHKey(Base, TimestampedModel):
    __tablename__ = "ssh_key"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate_id("ssh_")
    )
    user: Mapped[str] = mapped_column(String(255))
    public_key: Mapped[str] = mapped_column(Text)
    private_key: Mapped[str] = mapped_column(Text)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    fingerprint: Mapped[str | None] = mapped_column(String, nullable=True)

    @classmethod
    def create_key_pair(cls) -> tuple[str, str]:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        private_key_str = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        public_key_str = (
            private_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.OpenSSH,
                format=serialization.PublicFormat.OpenSSH,
            )
            .decode()
        )
        return (public_key_str, private_key_str)

    @classmethod
    def generate_fingerprint(cls, public_key: str) -> str:
        # OpenSSH SHA256 fingerprint: SHA256 of the decoded base64 key blob
        key_blob = public_key.strip().split()[1]
        blob = base64.b64decode(key_blob)
        digest = hashlib.sha256(blob).digest()
        fingerprint = base64.b64encode(digest).rstrip(b"=").decode("ascii")
        return f"SHA256:{fingerprint}"

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

PRODUCTION_ENV = "PRODUCTION"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = Field(
        default="dky-insecure-^@$8fc&u2j)4@k+p+bg0ei8sm+@+pwq)hstk$$a*0*7#k54kybx",
        alias="DOCKYARD_SECRET_KEY",
    )
    environment: str = Field(default="DEVELOPMENT", alias="ENVIRONMENT")
    testing: bool = Field(default=False, alias="TESTING")

    redis_url: str = Field(default="redis://127.0.0.1:6381/0", alias="REDIS_URL")

    root_domain: str = Field(default="127-0-0-1.sslip.io", alias="ROOT_DOMAIN")
    app_domain: str = Field(default="127-0-0-1.sslip.io", alias="DOCKYARD_APP_DOMAIN")
    internal_domain: str = Field(
        default="dockyard.internal", alias="DOCKYARD_INTERNAL_DOMAIN"
    )
    caddy_proxy_admin_host: str = Field(
        default="http://127.0.0.1:2019", alias="CADDY_PROXY_ADMIN_HOST"
    )

    db_name: str = Field(default="dockyard", alias="DB_NAME")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="password", alias="DB_PASSWORD")
    db_host: str = Field(default="127.0.0.1", alias="DB_HOST")
    db_port: str = Field(default="5434", alias="DB_PORT")

    session_expire_threshold: int = 2
    session_extend_period: int = 7

    image_version: str = Field(default="canary", alias="IMAGE_VERSION")
    commit_sha: str | None = Field(default=None, alias="COMMIT_SHA")
    loki_host: str = Field(default="http://127.0.0.1:3100", alias="LOKI_HOST")

    temporalio_server_url: str = Field(
        default="127.0.0.1:7233", alias="TEMPORALIO_SERVER_URL"
    )
    temporalio_namespace: str = Field(default="default", alias="TEMPORALIO_NAMESPACE")
    main_task_queue: str = "main-task-queue"
    worker_task_queue: str | None = Field(
        default=None, alias="TEMPORALIO_WORKER_TASK_QUEUE"
    )

    @computed_field
    @property
    def debug(self) -> bool:
        return self.environment != PRODUCTION_ENV

    @computed_field
    @property
    def temporalio_task_queue(self) -> str:
        return self.worker_task_queue or self.main_task_queue

    @computed_field
    @property
    def password_hash_rounds(self) -> int:
        # bcrypt is meant to be slow. Under test that cost buys nothing and is
        # paid on every fixture, so drop to the minimum the algorithm allows.
        return 4 if self.testing else 12

    @computed_field
    @property
    def anon_throttle_rate(self) -> str:
        if self.testing:
            return "5/minute"
        return "60/minute" if self.debug else "5/minute"

    @computed_field
    @property
    def database_url(self) -> str:
        if self.testing:
            return "sqlite+aiosqlite:///./dockyard_test.sqlite3"
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

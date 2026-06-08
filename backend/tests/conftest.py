import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import db as db_module
from app import session as session_module
from app import throttling as throttling_module
from app.main import app
from app.models import Base, User

TEST_DATABASE_URL = "sqlite+aiosqlite:///./dockyard_test.sqlite3"


@pytest.fixture(autouse=True)
def _clear_sessions():
    session_module.MemorySessionStore._store.clear()
    throttling_module._history.clear()
    yield
    session_module.MemorySessionStore._store.clear()
    throttling_module._history.clear()


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def session(session_factory):
    async with session_factory() as s:
        yield s


@pytest_asyncio.fixture
async def client(session_factory):
    async def override_get_db():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[db_module.get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user(session):
    u = User(username="kuluruvineeth", is_superuser=True, is_active=True)
    u.set_password("password")
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return u


@pytest_asyncio.fixture
async def auth_client(client, user):
    response = await client.post(
        "/api/auth/login",
        json={"username": "kuluruvineeth", "password": "password"},
    )
    assert response.status_code == 201
    return client

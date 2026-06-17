import sys, os

# Make sure backend root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from config import settings
import database
from database import get_db

# Register every model on the shared Base before create_all.
from auth.models import Base
import auth.models  # noqa: F401  (User)
import chat.models  # noqa: F401  (Workspace, Chat, Message, ChatSummary)

from main import app

# Tests run against a DEDICATED database (ai_chatbot_test), never the dev DB.
# Using the dev DB causes DROP TABLE in setup/teardown to block forever on locks
# held by the running backend. NullPool opens/closes a fresh connection each time,
# avoiding the classic async-SQLAlchemy cross-event-loop pool deadlock.
TEST_DB_NAME = "ai_chatbot_test"
TEST_DATABASE_URL = settings.database_url.rsplit("/", 1)[0] + "/" + TEST_DB_NAME


def _ensure_test_db_exists():
    """Create the test database if it isn't there yet, so `pytest` works on a
    fresh setup without any manual psql step."""
    import asyncio
    import asyncpg
    from urllib.parse import urlparse

    dsn = settings.database_url.replace("+asyncpg", "")
    p = urlparse(dsn)

    async def _create():
        conn = await asyncpg.connect(
            host=p.hostname, port=p.port, user=p.username,
            password=p.password, database=p.path.lstrip("/"),
        )
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME
            )
            if not exists:
                await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
        finally:
            await conn.close()

    asyncio.run(_create())


_ensure_test_db_exists()

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

# Point both the dependency and any direct async_session_maker users
# (e.g. chat/summarizer.py) at the test sessionmaker/engine.
database.async_session_maker = TestSessionLocal
database.engine = test_engine


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def init_db():
    """Fresh schema for every test — full isolation."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def chat_id():
    """Create a user -> workspace -> chat and return the chat id (string).

    The /api/chat/stream endpoint now requires a real chat to persist messages
    against, so stream tests need a seeded chat.
    """
    from auth.models import User
    from chat.models import Workspace, Chat

    async with TestSessionLocal() as s:
        user = User(email="streamer@test.com", password="x")
        s.add(user)
        await s.commit()
        await s.refresh(user)

        ws = Workspace(owner_id=user.id, name="Stream WS")
        s.add(ws)
        await s.commit()
        await s.refresh(ws)

        chat = Chat(workspace_id=ws.id, user_id=user.id, title="Stream Chat")
        s.add(chat)
        await s.commit()
        await s.refresh(chat)
        return str(chat.id)


@pytest.fixture
def transport():
    return ASGITransport(app=app)


@pytest.fixture
async def client(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

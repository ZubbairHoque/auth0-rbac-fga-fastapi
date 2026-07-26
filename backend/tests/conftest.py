# pyrefly: ignore [missing-import]
from unittest.mock import MagicMock
from unittest.mock import patch
import time
from httpx import ASGITransport, AsyncClient
import pytest
from sqlalchemy import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.database import Base  # Import your SQLAlchemy declarative Base
from app.main import app
import jwt

# Use an in-memory SQLite database for fast testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
async def db_engine():
    """Creates a single database engine for the entire test session."""
    engine = create_async_engine(
        TEST_DATABASE_URL, 
        poolclass=StaticPool, 
        connect_args={"check_same_thread": False}
        )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """
    Provides a modern transactional database session for a single test function.
    """

    # Create a sessionmaker bound directly to the engine
    async_session = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
        )

     # Establish a connection to manage the outer transaction
    async with async_session() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())

        yield session

        await session.rollback()

        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio", {"use_selector": True}


@pytest.fixture
@patch("app.utils.security.jwt.encode")
def test_token() -> str:
    mock_signing_key=MagicMock()
    mock_signing_key.private_key="fakekey"
    payload = {
        "aud": "http://test.audience.com",
        "sub": "user123",
        "iss": "http://test.issuer.com",
        "exp": time.time() + 600,
    }
    return jwt.encode(payload, mock_signing_key.private_key, algorithm="RS256")



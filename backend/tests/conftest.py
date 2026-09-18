import os
import shutil
import tempfile
from collections.abc import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# ---------------------------------------------------------------------------
# Hermetic test guarantee: automated tests MUST NOT make live network calls.
# Force local development providers BEFORE importing app.main so every
# API/service test uses the deterministic grounded synthesizer and the local
# embedding provider, regardless of the developer's local .env selecting
# OpenRouter/Gemini. Real-provider connectivity is covered separately by the
# opt-in live integration test (tests/test_live_integration.py, marker "live").
# ---------------------------------------------------------------------------
settings.LLM_PROVIDER = "development"
settings.EMBEDDING_PROVIDER = "development"
settings.VISION_PROVIDER = "development"
settings.ALLOW_EXTERNAL_PROVIDERS = False

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# Create a temporary directory for test storage
TEST_TEMP_DIR = tempfile.mkdtemp()
TEST_DB_PATH = os.path.join(TEST_TEMP_DIR, "test_scholaredge.db")
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    # Update settings to point to temp dir
    settings.DATA_DIR = type(settings.DATA_DIR)(TEST_TEMP_DIR)
    settings.UPLOAD_DIR = type(settings.UPLOAD_DIR)(os.path.join(TEST_TEMP_DIR, "uploads"))
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield
    # Cleanup after all tests
    shutil.rmtree(TEST_TEMP_DIR, ignore_errors=True)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

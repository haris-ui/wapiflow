import asyncio
import sys
import uuid
from typing import AsyncGenerator, Dict, Tuple
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# ---------------------------------------------------------------------------
# Test-environment shim: boto3 (Cloudflare R2 SDK) is not required to run the
# test suite. StorageService gates every real S3/R2 call behind
# StorageService.is_r2_configured(), which returns False without credentials,
# so the mock below is never exercised for actual I/O in tests. It only
# allows the module to import in environments where boto3 isn't installed.
# ---------------------------------------------------------------------------
if "boto3" not in sys.modules:
    _boto3_mock = MagicMock()
    _boto3_mock.client = MagicMock(return_value=MagicMock())
    sys.modules["boto3"] = _boto3_mock
    sys.modules["botocore"] = MagicMock()
    sys.modules["botocore.config"] = MagicMock()
    sys.modules["botocore.exceptions"] = MagicMock()

from app.database import get_db
from app.models.base import Base
from app.models.business import Business, BusinessMember, BusinessSettings, Subscription
from app.models.profile import Profile
from app.services.auth_service import create_jwt_token
from main import app

# In-memory Async SQLite for isolated and blazing-fast test runs
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    """Create all database tables before running the test suite."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session fixture for direct test assertions."""
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture(autouse=True)
async def override_db_dependency():
    """Override FastAPI get_db dependency to point to the test database session."""
    async def _test_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestingSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = _test_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client configured with ASGI transport against the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def create_user() -> callable:
    """Factory fixture to create users and generate valid auth headers."""
    async def _create(email: str, full_name: str = "Test User") -> Tuple[uuid.UUID, Dict[str, str]]:
        user_id = uuid.uuid4()
        async with TestingSessionLocal() as session:
            profile = Profile(
                id=user_id,
                email=email.lower().strip(),
                full_name=full_name,
                is_active=True,
            )
            session.add(profile)
            await session.commit()

        token = create_jwt_token(user_id=user_id, email=email)
        headers = {"Authorization": f"Bearer {token}"}
        return user_id, headers

    return _create


@pytest_asyncio.fixture
async def create_business() -> callable:
    """Factory fixture to seed a business tenant with settings and owner membership."""
    async def _create(user_id: uuid.UUID, name: str, slug: str) -> uuid.UUID:
        business_id = uuid.uuid4()
        async with TestingSessionLocal() as session:
            business = Business(
                id=business_id,
                name=name,
                slug=slug,
                currency="USD",
                timezone="UTC",
                is_active=True,
            )
            session.add(business)

            membership = BusinessMember(
                id=uuid.uuid4(),
                business_id=business_id,
                user_id=user_id,
                role="owner",
                is_active=True,
            )
            session.add(membership)

            settings = BusinessSettings(
                id=uuid.uuid4(),
                business_id=business_id,
                auto_decrement_stock=True,
                order_prefix="WF-",
            )
            session.add(settings)

            sub = Subscription(
                id=uuid.uuid4(),
                business_id=business_id,
                plan_tier="pro",
                status="active",
            )
            session.add(sub)

            await session.commit()

        return business_id

    return _create


class _TestBusiness:
    def __init__(self, bid: uuid.UUID):
        self.id = bid


@pytest_asyncio.fixture
async def test_user_and_business(create_user, create_business):
    """Convenience fixture creating a test user and an owned test business."""
    user_id, headers = await create_user(f"tenant_{uuid.uuid4().hex[:8]}@example.com")
    biz_id = await create_business(user_id, "Test Business", f"test-biz-{uuid.uuid4().hex[:6]}")
    return user_id, headers, _TestBusiness(biz_id)


@pytest_asyncio.fixture
async def test_business(test_user_and_business):
    """Convenience fixture returning a business with .id."""
    _, _, biz = test_user_and_business
    return biz


@pytest_asyncio.fixture
async def auth_headers(test_user_and_business):
    """Convenience fixture returning auth headers for the test business owner."""
    _, headers, _ = test_user_and_business
    return headers


@pytest_asyncio.fixture
def test_user_factory(create_user):
    """Factory fixture to create users and return a simple object with id."""
    async def _make(email: str):
        class _User:
            def __init__(self, uid: uuid.UUID):
                self.id = uid

        uid, _ = await create_user(email)
        return _User(uid)

    return _make


@pytest_asyncio.fixture
def test_business_factory(create_business):
    """Factory fixture to create business and return object with id."""
    async def _make(owner_user_id: uuid.UUID, name: str):
        slug = f"slug-{uuid.uuid4().hex[:8]}"
        bid = await create_business(owner_user_id, name, slug)
        return _TestBusiness(bid)

    return _make


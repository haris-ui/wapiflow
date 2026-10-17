import asyncio
import uuid
from typing import AsyncGenerator, Dict, Tuple
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

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

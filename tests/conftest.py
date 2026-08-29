"""Pytest configuration and fixtures using Faker for synthetic test data generation."""

import os
from typing import AsyncGenerator
from cryptography.fernet import Fernet

# Set dynamic runtime Fernet key for pytest execution if not present in env
if "ENCRYPTION_KEY" not in os.environ:
    os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()

import pytest
import pytest_asyncio
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from mcp_digitalinvoice.models.db import Base
from mcp_digitalinvoice.config import settings

fake = Faker()

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for async test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_engine():
    """Create an in-memory SQLite async engine for isolated test runs."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated async database session for a test."""
    session_factory = async_sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


class FakeLock:
    def __init__(self, key: str):
        self.key = key
        self.locked = False

    async def acquire(self, blocking_timeout: float = 5):
        self.locked = True
        return True

    async def release(self):
        self.locked = False


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str):
        self.store[key] = value

    async def setex(self, key: str, seconds: int, value: str):
        self.store[key] = value

    async def delete(self, key: str):
        self.store.pop(key, None)

    def lock(self, name: str, timeout: float = 30):
        return FakeLock(name)

    async def aclose(self):
        pass


@pytest.fixture
def fake_redis():
    """In-memory fake Redis for test isolation."""
    return FakeRedis()


@pytest.fixture
def synthetic_tenant_data():
    """Generate dynamic synthetic tenant data using Faker (Zero hardcoded values)."""
    return {
        "name": fake.company(),
        "email": fake.email(),
        "password": fake.password(length=12),
        "ntn": fake.bothify(text="#######-#"),
        "province": fake.state(),
        "address": fake.address().replace("\n", ", "),
    }


@pytest.fixture
def synthetic_buyer_data():
    """Generate dynamic synthetic buyer identity using Faker."""
    return {
        "businessName": fake.company(),
        "ntnCnic": fake.bothify(text="#############"),
        "province": fake.state(),
        "address": fake.address().replace("\n", ", "),
        "registrationType": "Registered",
    }


@pytest.fixture
def synthetic_item_data():
    """Generate dynamic synthetic invoice line item using Faker."""
    return {
        "hsCode": fake.bothify(text="####.##.##"),
        "description": fake.catch_phrase(),
        "quantity": fake.random_int(min=1, max=100),
        "saleType": "Taxable Goods",
        "uom": "PCS",
        "rate": f"{fake.random_int(min=5, max=25)}%",
    }

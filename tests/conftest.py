"""Pytest configuration and fixtures."""
import pytest
import asyncio
from src.db.connection import init_db, async_session
from src.db.models import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_db():
    """Setup test database."""
    await init_db()
    yield
    # Cleanup after tests
    async with async_session() as db:
        await db.execute("DELETE FROM responses")
        await db.execute("DELETE FROM emails")
        await db.execute("DELETE FROM campaigns")
        await db.execute("DELETE FROM leads")
        await db.execute("DELETE FROM users")
        await db.commit()


@pytest.fixture
def sample_lead():
    """Sample lead data."""
    return {
        "first_name": "John",
        "last_name": "Smith",
        "email": "john@example.com",
        "company": "Example Corp",
        "title": "Real Estate Agent",
        "phone": "555-123-4567",
        "location": "Austin, TX"
    }


@pytest.fixture
def sample_user_data():
    """Sample user registration data."""
    return {
        "email": "test@example.com",
        "name": "Test User",
        "password": "testpassword123"
    }
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
import sys, os

# Make sure backend root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app


@pytest.fixture
def transport():
    return ASGITransport(app=app)


@pytest.fixture
async def client(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

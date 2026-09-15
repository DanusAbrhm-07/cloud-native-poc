"""
Test suite for the Cloud-Native PoC API
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, init_db, init_redis, close_db, close_redis


# ==================== Fixtures ====================
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client():
    """Create test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def mock_db():
    """Mock database connection."""
    with patch('main.db_pool') as mock_pool:
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        yield mock_conn


@pytest.fixture
async def mock_redis():
    """Mock Redis client."""
    with patch('main.redis_client') as mock_redis:
        yield mock_redis


# ==================== Health Tests ====================
class TestHealth:
    """Health endpoint tests."""

    async def test_health_healthy(self, client, mock_db, mock_redis):
        """Test health endpoint when all dependencies are healthy."""
        mock_db.fetchval.return_value = 1
        mock_redis.ping.return_value = True

        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["dependencies"]["database"] == "healthy"
        assert data["dependencies"]["redis"] == "healthy"
        assert "uptime_seconds" in data

    async def test_health_degraded_db(self, client, mock_db, mock_redis):
        """Test health endpoint when database is unhealthy."""
        mock_db.fetchval.side_effect = Exception("Connection failed")
        mock_redis.ping.return_value = True

        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["dependencies"]["database"] == "unhealthy"

    async def test_health_degraded_redis(self, client, mock_db, mock_redis):
        """Test health endpoint when Redis is unhealthy."""
        mock_db.fetchval.return_value = 1
        mock_redis.ping.side_effect = Exception("Connection failed")

        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["dependencies"]["redis"] == "unhealthy"


# ==================== Items CRUD Tests ====================
class TestItems:
    """Items CRUD operation tests."""

    async def test_create_item(self, client, mock_db, mock_redis):
        """Test creating a new item."""
        mock_row = {
            "id": 1,
            "name": "Test Item",
            "description": "Test Description",
            "quantity": 10,
            "price": 29.99,
            "created_at": "2024-01-01T00:00:00"
        }
        mock_db.fetchrow.return_value = mock_row
        mock_redis.delete.return_value = 1

        response = await client.post("/items", json={
            "name": "Test Item",
            "description": "Test Description",
            "quantity": 10,
            "price": 29.99
        })
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Test Item"
        assert data["price"] == 29.99

    async def test_create_item_validation(self, client):
        """Test item creation validation."""
        # Test empty name
        response = await client.post("/items", json={
            "name": "",
            "quantity": 10,
            "price": 29.99
        })
        assert response.status_code == 422

        # Test negative quantity
        response = await client.post("/items", json={
            "name": "Test",
            "quantity": -1,
            "price": 29.99
        })
        assert response.status_code == 422

        # Test negative price
        response = await client.post("/items", json={
            "name": "Test",
            "quantity": 10,
            "price": -1.0
        })
        assert response.status_code == 422

    async def test_list_items_empty(self, client, mock_db, mock_redis):
        """Test listing items when empty."""
        mock_redis.get.return_value = None
        mock_db.fetch.return_value = []
        mock_redis.setex.return_value = True

        response = await client.get("/items")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_items_with_cache(self, client, mock_db, mock_redis):
        """Test listing items with cache hit."""
        cached_items = [{
            "id": 1,
            "name": "Cached Item",
            "description": "Cached",
            "quantity": 5,
            "price": 19.99,
            "created_at": "2024-01-01T00:00:00"
        }]
        import json
        mock_redis.get.return_value = json.dumps(cached_items)

        response = await client.get("/items")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Cached Item"

    async def test_get_item_found(self, client, mock_db, mock_redis):
        """Test getting a single item."""
        mock_row = {
            "id": 1,
            "name": "Test Item",
            "description": "Test Description",
            "quantity": 10,
            "price": 29.99,
            "created_at": "2024-01-01T00:00:00"
        }
        mock_redis.get.return_value = None
        mock_db.fetchrow.return_value = mock_row
        mock_redis.setex.return_value = True

        response = await client.get("/items/1")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Test Item"

    async def test_get_item_not_found(self, client, mock_db, mock_redis):
        """Test getting non-existent item."""
        mock_redis.get.return_value = None
        mock_db.fetchrow.return_value = None

        response = await client.get("/items/999")
        assert response.status_code == 404

    async def test_update_item(self, client, mock_db, mock_redis):
        """Test updating an item."""
        mock_row = {
            "id": 1,
            "name": "Updated Item",
            "description": "Updated Description",
            "quantity": 20,
            "price": 39.99,
            "created_at": "2024-01-01T00:00:00"
        }
        mock_db.fetchrow.return_value = mock_row
        mock_redis.delete.return_value = 1

        response = await client.patch("/items/1", json={
            "name": "Updated Item",
            "quantity": 20
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Item"
        assert data["quantity"] == 20

    async def test_update_item_not_found(self, client, mock_db, mock_redis):
        """Test updating non-existent item."""
        mock_db.fetchrow.return_value = None

        response = await client.patch("/items/999", json={"name": "Updated"})
        assert response.status_code == 404

    async def test_delete_item(self, client, mock_db, mock_redis):
        """Test deleting an item."""
        mock_db.execute.return_value = "DELETE 1"
        mock_redis.delete.return_value = 1

        response = await client.delete("/items/1")
        assert response.status_code == 204

    async def test_delete_item_not_found(self, client, mock_db, mock_redis):
        """Test deleting non-existent item."""
        mock_db.execute.return_value = "DELETE 0"

        response = await client.delete("/items/999")
        assert response.status_code == 404


# ==================== Metrics Tests ====================
class TestMetrics:
    """Prometheus metrics tests."""

    async def test_metrics_endpoint(self, client):
        """Test metrics endpoint returns Prometheus format."""
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        assert "http_requests_total" in response.text


# ==================== Root Tests ====================
class TestRoot:
    """Root endpoint tests."""

    async def test_root(self, client):
        """Test root endpoint."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Cloud-Native PoC API"
        assert data["version"] == "1.0.0"
        assert "docs" in data
        assert "health" in data
        assert "metrics" in data


# ==================== Integration Tests ====================
class TestIntegration:
    """Integration tests with real services (require running services)."""

    @pytest.mark.integration
    async def test_full_crud_cycle(self, client):
        """Test full CRUD cycle with real database."""
        # This test requires actual services running
        # Run with: pytest -m integration
        pass


# ==================== Performance Tests ====================
class TestPerformance:
    """Basic performance tests."""

    @pytest.mark.performance
    async def test_response_time(self, client, mock_db, mock_redis):
        """Test response time is acceptable."""
        import time
        mock_db.fetchval.return_value = 1
        mock_redis.ping.return_value = True

        start = time.time()
        response = await client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.5  # Should respond within 500ms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
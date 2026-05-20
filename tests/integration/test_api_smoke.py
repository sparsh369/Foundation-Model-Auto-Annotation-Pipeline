"""API smoke tests that need no database (app wiring, OpenAPI, liveness, authz)."""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_liveness(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_openapi_served(client):
    r = await client.get("/api/v1/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    assert spec["info"]["title"]
    # core routes are registered
    assert "/api/v1/auth/login" in spec["paths"]
    assert "/api/v1/jobs" in spec["paths"]
    assert "/api/v1/reviews/queue" in spec["paths"]


async def test_protected_route_requires_auth(client):
    r = await client.get("/api/v1/datasets")
    assert r.status_code == 401


async def test_metrics_endpoint(client):
    r = await client.get("/metrics")
    assert r.status_code == 200
    assert b"http_requests_total" in r.content

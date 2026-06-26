"""
Phase 8 tests — Evaluation Dashboard

Covers:
  1. GET /api/admin/evaluations — returns aggregated analytics data.
  2. Multi-tenancy — ensure one workspace cannot see another's logs.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _register_and_workspace(client: AsyncClient, email: str):
    """Register a user, login, and return (api_key, workspace_id, auth_headers)."""
    await client.post("/api/auth/register", json={"email": email, "password": "TestPass123!"})
    r = await client.post("/api/auth/login", data={"username": email, "password": "TestPass123!"})
    token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}

    from tests.conftest import TestSessionLocal
    from auth.models import User
    from chat.models import Workspace
    async with TestSessionLocal() as s:
        user = (await s.execute(select(User).filter(User.email == email))).scalar_one()
        ws = (await s.execute(select(Workspace).filter(Workspace.owner_id == user.id))).scalar_one()
        api_key = ws.api_key
        ws_id = str(ws.id)

    return api_key, ws_id, auth


async def _seed_eval_logs(ws_id: str, count: int, feedback: str = None, chunks: list = None, latency: int = 100):
    from tests.conftest import TestSessionLocal
    from chat.models import EvalLog
    async with TestSessionLocal() as s:
        for i in range(count):
            log = EvalLog(
                workspace_id=ws_id,
                question=f"Question {i}",
                answer=f"Answer {i}",
                model_name="test-model",
                retrieved_chunks=chunks or [],
                latency_ms=latency,
                feedback=feedback
            )
            s.add(log)
        await s.commit()

# ---------------------------------------------------------------------------
# Test 1: Dashboard analytics aggregation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_aggregations(client: AsyncClient):
    _, ws_id, auth = await _register_and_workspace(client, "admin_dashboard@test.com")

    # Seed data
    chunks = [{"filename": "doc1.pdf", "page": 1}, {"filename": "doc2.pdf"}]
    
    await _seed_eval_logs(ws_id, 3, feedback="up", chunks=chunks, latency=200)
    await _seed_eval_logs(ws_id, 1, feedback="down", chunks=[], latency=400) # empty chunks = No Info gap

    r = await client.get("/api/admin/evaluations", headers=auth)
    assert r.status_code == 200
    data = r.json()

    metrics = data["metrics"]
    assert metrics["total_queries"] == 4
    assert metrics["avg_latency_ms"] == 250.0 # (3*200 + 400)/4
    assert metrics["up_votes"] == 3
    assert metrics["down_votes"] == 1
    assert metrics["positive_ratio"] == 75.0

    assert len(data["recent_feedback"]) == 4
    assert len(data["slow_queries"]) == 4
    assert data["slow_queries"][0]["latency_ms"] == 400 # Descending order
    
    assert len(data["coverage_gaps"]) == 1
    
    top_chunks = data["top_chunks"]
    assert len(top_chunks) == 2
    assert top_chunks[0]["count"] == 3 # doc1 and doc2 both appear 3 times

# ---------------------------------------------------------------------------
# Test 2: Multi-tenancy isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_multitenancy(client: AsyncClient):
    _, ws_a_id, auth_a = await _register_and_workspace(client, "ws_a@test.com")
    _, ws_b_id, auth_b = await _register_and_workspace(client, "ws_b@test.com")

    # Seed 5 logs for A
    await _seed_eval_logs(ws_a_id, 5, latency=100)
    
    # Seed 2 logs for B
    await _seed_eval_logs(ws_b_id, 2, latency=100)

    r_a = await client.get("/api/admin/evaluations", headers=auth_a)
    assert r_a.json()["metrics"]["total_queries"] == 5

    r_b = await client.get("/api/admin/evaluations", headers=auth_b)
    assert r_b.json()["metrics"]["total_queries"] == 2

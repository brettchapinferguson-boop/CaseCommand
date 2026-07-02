"""Tests for the autonomous paralegal worker."""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

import database as db
import worker
import claude_client


@pytest.fixture
def fresh_db(tmp_path):
    db.DB_PATH = str(tmp_path / "worker_test.db")
    asyncio.run(db.init_db())
    yield


def test_sweep_creates_tasks_for_near_deadlines(fresh_db):
    # Seed deadlines: d1 (9 days), d3 (3 days) are within 14 days
    created = asyncio.run(worker.sweep_deadlines())
    assert created >= 2
    tasks = asyncio.run(db.list_tasks(status="open"))
    titles = [t["title"] for t in tasks]
    assert any("Motion to compel" in t for t in titles)
    # ≤7 days should be urgent
    urgent = [t for t in tasks if t["priority"] == "urgent"]
    assert len(urgent) >= 1


def test_sweep_is_idempotent(fresh_db):
    first = asyncio.run(worker.sweep_deadlines())
    second = asyncio.run(worker.sweep_deadlines())
    assert first >= 2
    assert second == 0  # no duplicates


def test_cycle_without_api_key_still_sweeps(fresh_db):
    original = claude_client.API_KEY
    claude_client.API_KEY = ""
    try:
        result = asyncio.run(worker.run_cycle(kind="test_cycle"))
    finally:
        claude_client.API_KEY = original
    assert result["status"] == "partial"
    assert result["actions"] >= 2
    runs = asyncio.run(db.list_agent_runs())
    assert runs[0]["kind"] == "test_cycle"
    assert runs[0]["status"] == "partial"


def test_cycle_with_agent_records_run(fresh_db):
    agent_result = {
        "success": True,
        "text": "Cycle complete: drafted M&C letter, created 2 tasks.",
        "actions": ["save_document(doc_type=mc_letter)", "create_task(title=x)"],
        "usage": {"input_tokens": 5000, "output_tokens": 1200},
        "error": None,
    }
    with patch("agent.run_agent", new_callable=AsyncMock, return_value=agent_result), \
         patch("agent.build_paralegal_prompt", new_callable=AsyncMock, return_value="system"):
        result = asyncio.run(worker.run_cycle(kind="test_cycle"))
    assert result["status"] == "completed"
    assert "drafted M&C letter" in result["summary"]
    runs = asyncio.run(db.list_agent_runs())
    assert runs[0]["status"] == "completed"
    assert runs[0]["input_tokens"] == 5000


def test_cycle_agent_error_recorded(fresh_db):
    agent_result = {
        "success": False, "text": "", "actions": [],
        "usage": {"input_tokens": 0, "output_tokens": 0},
        "error": "AI service timeout",
    }
    with patch("agent.run_agent", new_callable=AsyncMock, return_value=agent_result), \
         patch("agent.build_paralegal_prompt", new_callable=AsyncMock, return_value="system"):
        result = asyncio.run(worker.run_cycle(kind="test_cycle"))
    assert result["status"] == "error"
    runs = asyncio.run(db.list_agent_runs())
    assert runs[0]["status"] == "error"

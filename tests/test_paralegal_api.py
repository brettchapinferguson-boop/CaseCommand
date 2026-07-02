"""Tests for tasks, documents/review queue, audit, and agent endpoints."""
import asyncio
from unittest.mock import AsyncMock, patch

import database as db


# ── Tasks ─────────────────────────────────────────

def test_create_and_list_tasks(client):
    resp = client.post("/api/tasks", json={
        "title": "Call expert re accident reconstruction",
        "case_id": "c1",
        "priority": "high",
    })
    assert resp.status_code == 201
    task = resp.json()
    assert task["created_by"] == "human"

    resp = client.get("/api/tasks?status=open")
    assert any(t["id"] == task["id"] for t in resp.json()["tasks"])


def test_task_priority_ordering(client):
    client.post("/api/tasks", json={"title": "low thing", "priority": "low"})
    client.post("/api/tasks", json={"title": "urgent thing", "priority": "urgent"})
    tasks = client.get("/api/tasks?status=open").json()["tasks"]
    priorities = [t["priority"] for t in tasks]
    assert priorities.index("urgent") < priorities.index("low")


def test_update_task_status(client):
    task = client.post("/api/tasks", json={"title": "Temp task"}).json()
    resp = client.patch(f"/api/tasks/{task['id']}", json={"status": "done"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"
    assert resp.json()["completed_at"] is not None


def test_update_task_not_found(client):
    resp = client.patch("/api/tasks/zzz", json={"status": "done"})
    assert resp.status_code == 404


def test_task_validation(client):
    resp = client.post("/api/tasks", json={"title": "x", "priority": "extreme"})
    assert resp.status_code == 422


# ── Documents & review queue ──────────────────────

def _seed_document(content="Draft letter per CCP §2016.040...", doc_type="mc_letter"):
    return asyncio.run(db.create_document({
        "id": "doc-test1",
        "case_id": "c1",
        "doc_type": doc_type,
        "title": "M&C Letter — Smith Trucking",
        "content": content,
        "created_by": "agent:test",
    }))


def test_list_documents_hides_full_content(client):
    _seed_document()
    resp = client.get("/api/documents")
    assert resp.status_code == 200
    doc = resp.json()["documents"][0]
    assert "preview" in doc
    assert "content" not in doc


def test_get_document_full(client):
    _seed_document()
    resp = client.get("/api/documents/doc-test1")
    assert resp.status_code == 200
    assert "CCP §2016.040" in resp.json()["content"]


def test_approve_document(client):
    _seed_document()
    resp = client.post("/api/documents/doc-test1/review",
                       json={"action": "approve", "note": "Reviewed, citations verified"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert resp.json()["reviewed_at"] is not None

    # Review action is audit-logged (supervision record)
    audit = client.get("/api/audit").json()["audit"]
    assert any(a["action"] == "approve_document" for a in audit)


def test_reject_document(client):
    _seed_document()
    resp = client.post("/api/documents/doc-test1/review",
                       json={"action": "reject", "note": "Wrong tone, redraft"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_review_invalid_action(client):
    _seed_document()
    resp = client.post("/api/documents/doc-test1/review", json={"action": "send"})
    assert resp.status_code == 422  # 'send' is not an allowed action — by design


def test_review_queue(client):
    _seed_document()
    client.post("/api/tasks", json={"title": "Urgent filing prep", "priority": "urgent"})
    resp = client.get("/api/review/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert data["counts"]["pending_documents"] == 1
    assert data["counts"]["urgent_tasks"] >= 1
    assert data["counts"]["deadlines_14_days"] >= 1  # seeded deadlines
    assert "content" not in data["pending_documents"][0]


def test_approved_document_leaves_queue(client):
    _seed_document()
    client.post("/api/documents/doc-test1/review", json={"action": "approve"})
    resp = client.get("/api/review/queue")
    assert resp.json()["counts"]["pending_documents"] == 0


# ── Audit ─────────────────────────────────────────

def test_audit_endpoint(client):
    client.post("/api/tasks", json={"title": "Audit me"})
    resp = client.get("/api/audit")
    assert resp.status_code == 200
    assert any(a["action"] == "create_task" for a in resp.json()["audit"])


# ── Agent endpoints ───────────────────────────────

def test_agent_draft(client, mock_agent_success):
    resp = client.post("/api/agent/draft", json={
        "case_id": "c1",
        "doc_type": "mc_letter",
        "instructions": "M&C re deficient responses to RFP set one",
    })
    assert resp.status_code == 200
    assert "actions" in resp.json()
    # Drafting instruction reached the agent
    prompt_arg = mock_agent_success.call_args[0][1][0]["content"]
    assert "deficient responses" in prompt_arg


def test_agent_draft_case_not_found(client, mock_agent_success):
    resp = client.post("/api/agent/draft", json={
        "case_id": "nope", "doc_type": "memo", "instructions": "x",
    })
    assert resp.status_code == 404


def test_agent_cycle_endpoint(client):
    cycle_result = {"run_id": "r1", "status": "completed",
                    "summary": "All quiet", "actions": 2, "tool_calls": []}
    with patch("worker.run_cycle", new_callable=AsyncMock, return_value=cycle_result):
        resp = client.post("/api/agent/cycle")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


def test_agent_runs_endpoint(client):
    asyncio.run(db.start_agent_run("run-x", "test"))
    asyncio.run(db.finish_agent_run("run-x", "completed", "did things", actions=3))
    resp = client.get("/api/agent/runs")
    assert resp.status_code == 200
    runs = resp.json()["runs"]
    assert any(r["id"] == "run-x" for r in runs)

"""Tests for the agent tool executor (direct, no HTTP)."""
import asyncio
import json

import pytest

import database as db
import tools


@pytest.fixture
def fresh_db(tmp_path):
    db.DB_PATH = str(tmp_path / "tools_test.db")
    asyncio.run(db.init_db())
    yield


def run(coro):
    return asyncio.run(coro)


def test_list_cases(fresh_db):
    out = json.loads(run(tools.execute_tool("list_cases", {})))
    assert len(out["cases"]) == 3


def test_get_case(fresh_db):
    out = json.loads(run(tools.execute_tool("get_case", {"case_id": "c1"})))
    assert out["name"] == "Rodriguez v. Smith Trucking"


def test_get_case_not_found(fresh_db):
    out = json.loads(run(tools.execute_tool("get_case", {"case_id": "zzz"})))
    assert "error" in out


def test_update_case_audited(fresh_db):
    out = json.loads(run(tools.execute_tool(
        "update_case", {"case_id": "c1", "updates": {"phase": 5}}, actor="agent:test"
    )))
    assert out["phase"] == 5
    audit = run(db.list_audit())
    assert any(a["action"] == "update_case" and a["actor"] == "agent:test" for a in audit)


def test_compute_deadlines_tool(fresh_db):
    out = json.loads(run(tools.execute_tool("compute_deadlines", {
        "trigger_event": "discovery_propounded",
        "event_date": "2026-07-01",
        "service_method": "mail",
    })))
    assert out["deadlines"][0]["due_date"] == "2026-08-05"
    assert "warning" in out


def test_add_and_list_deadline(fresh_db):
    out = json.loads(run(tools.execute_tool("add_deadline", {
        "case_id": "c1", "title": "Test deadline",
        "due_date": "2026-08-01", "rule": "CCP §test",
    })))
    assert out["due_date"] == "2026-08-01"
    listed = json.loads(run(tools.execute_tool("list_deadlines", {})))
    assert any(d["title"] == "Test deadline" for d in listed["deadlines"])


def test_add_deadline_bad_date(fresh_db):
    out = json.loads(run(tools.execute_tool("add_deadline", {
        "case_id": "c1", "title": "Bad", "due_date": "tomorrow",
    })))
    assert "error" in out


def test_create_and_complete_task(fresh_db):
    out = json.loads(run(tools.execute_tool("create_task", {
        "title": "Draft M&C letter", "case_id": "c1", "priority": "urgent",
    })))
    assert out["status"] == "open"
    done = json.loads(run(tools.execute_tool("update_task", {
        "task_id": out["id"], "status": "done",
    })))
    assert done["status"] == "done"


def test_save_document_goes_to_review(fresh_db):
    out = json.loads(run(tools.execute_tool("save_document", {
        "case_id": "c1", "doc_type": "memo",
        "title": "Strategy memo", "content": "Plain memo, no citations here.",
    })))
    assert out["status"] == "pending_review"
    doc = run(db.get_document(out["document_id"]))
    assert doc["status"] == "pending_review"


def test_save_document_with_citations_creates_verification_task(fresh_db):
    out = json.loads(run(tools.execute_tool("save_document", {
        "case_id": "c1", "doc_type": "motion",
        "title": "Motion to Compel",
        "content": "Per CCP §2030.300 and Korea Data Systems v. Superior Court...",
    })))
    assert out["status"] == "pending_review"
    task_list = run(db.list_tasks(status="open"))
    assert any("Verify all citations" in t["title"] for t in task_list)


def test_digest_skips_citation_check(fresh_db):
    json.loads(run(tools.execute_tool("save_document", {
        "doc_type": "digest", "title": "Daily digest",
        "content": "Deadline under CCP §2030.300 approaching.",
    })))
    task_list = run(db.list_tasks(status="open"))
    assert not any("Verify all citations" in t["title"] for t in task_list)


def test_log_note(fresh_db):
    out = json.loads(run(tools.execute_tool(
        "log_note", {"note": "Client called re settlement posture", "case_id": "c1"}
    )))
    assert out["logged"] is True
    audit = run(db.list_audit())
    assert any("settlement posture" in a["detail"] for a in audit)


def test_unknown_tool_returns_error(fresh_db):
    out = json.loads(run(tools.execute_tool("send_email", {"to": "x"})))
    assert "error" in out


def test_no_external_communication_tools_exist():
    """Architecture guarantee: the toolbox contains nothing that can reach
    outside the practice (no email, filing, or external HTTP tools)."""
    names = {t["name"] for t in tools.TOOL_DEFINITIONS}
    forbidden = {"send_email", "file_document", "serve_document", "http_request",
                 "send_message", "efile"}
    assert not (names & forbidden)

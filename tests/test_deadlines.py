"""Tests for the deadline engine endpoints."""
from datetime import date, timedelta


def test_deadlines_seeded(client):
    resp = client.get("/api/deadlines")
    assert resp.status_code == 200
    dls = resp.json()["deadlines"]
    assert len(dls) == 3  # seeded demo deadlines
    for d in dls:
        assert "due_date" in d
        assert "title" in d
        assert "rule" in d
        assert "case" in d  # joined case name
        assert "case_id" in d


def test_deadlines_sorted_by_date(client):
    resp = client.get("/api/deadlines")
    dls = resp.json()["deadlines"]
    dates = [d["due_date"] for d in dls]
    assert dates == sorted(dates)


def test_deadlines_within_days_filter(client):
    resp = client.get("/api/deadlines?within_days=5")
    dls = resp.json()["deadlines"]
    cutoff = (date.today() + timedelta(days=5)).isoformat()
    assert all(d["due_date"] <= cutoff for d in dls)
    # Only the 3-day seed deadline should be inside 5 days
    assert len(dls) == 1


def test_create_deadline(client):
    due = (date.today() + timedelta(days=20)).isoformat()
    resp = client.post("/api/deadlines", json={
        "case_id": "c1",
        "title": "Serve supplemental responses",
        "due_date": due,
        "rule": "CCP §2030.290",
    })
    assert resp.status_code == 201
    assert resp.json()["due_date"] == due

    resp = client.get("/api/deadlines")
    assert len(resp.json()["deadlines"]) == 4


def test_compute_deadlines_endpoint(client):
    resp = client.post("/api/deadlines/compute", json={
        "trigger_event": "discovery_responses_received",
        "event_date": "2026-07-01",
        "service_method": "mail",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["deadlines"]) == 1
    dl = data["deadlines"][0]
    assert "2030.300" in dl["rule"]
    # 45 days + 5 mail = 50 days from 2026-07-01 → 2026-08-20 (Thursday)
    assert dl["due_date"] == "2026-08-20"
    assert "warning" in data


def test_compute_deadlines_unknown_trigger(client):
    resp = client.post("/api/deadlines/compute", json={
        "trigger_event": "not_a_real_event",
        "event_date": "2026-07-01",
    })
    assert resp.status_code == 400


def test_compute_deadlines_bad_date(client):
    resp = client.post("/api/deadlines/compute", json={
        "trigger_event": "incident",
        "event_date": "not-a-date",
    })
    assert resp.status_code == 400

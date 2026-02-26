"""Tests for deadline endpoints."""


def test_deadlines(client):
    resp = client.get("/api/deadlines")
    assert resp.status_code == 200
    data = resp.json()
    assert "deadlines" in data
    assert len(data["deadlines"]) == 3


def test_deadlines_sorted_urgent_first(client):
    resp = client.get("/api/deadlines")
    deadlines = resp.json()["deadlines"]
    # Urgent deadlines should come first
    urgent_indices = [i for i, d in enumerate(deadlines) if d.get("urgent")]
    non_urgent_indices = [i for i, d in enumerate(deadlines) if not d.get("urgent")]
    if urgent_indices and non_urgent_indices:
        assert max(urgent_indices) < min(non_urgent_indices)


def test_deadline_structure(client):
    resp = client.get("/api/deadlines")
    dl = resp.json()["deadlines"][0]
    assert "case" in dl
    assert "case_id" in dl
    assert "date" in dl
    assert "text" in dl
    assert "urgent" in dl

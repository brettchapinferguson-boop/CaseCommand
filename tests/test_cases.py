"""Tests for case management endpoints."""


def test_list_cases(client):
    resp = client.get("/api/cases")
    assert resp.status_code == 200
    data = resp.json()
    assert "cases" in data
    assert len(data["cases"]) == 3


def test_list_cases_structure(client):
    resp = client.get("/api/cases")
    case = resp.json()["cases"][0]
    assert "id" in case
    assert "name" in case
    assert "type" in case
    assert "client" in case
    assert "opposing" in case
    assert "phase" in case
    assert "specials" in case
    assert "valuation" in case


def test_get_case_by_id(client):
    resp = client.get("/api/cases/c1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "c1"
    assert data["name"] == "Rodriguez v. Smith Trucking"
    assert data["type"] == "Personal Injury"


def test_get_case_c2(client):
    resp = client.get("/api/cases/c2")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Chen v. Pacific Properties"


def test_get_case_c3(client):
    resp = client.get("/api/cases/c3")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Williams v. TechStart"


def test_get_case_not_found(client):
    resp = client.get("/api/cases/nonexistent")
    assert resp.status_code == 404


def test_case_valuation_structure(client):
    resp = client.get("/api/cases/c1")
    val = resp.json()["valuation"]
    assert "lo" in val
    assert "mid" in val
    assert "hi" in val
    assert val["lo"] < val["mid"] < val["hi"]


def test_case_modules(client):
    resp = client.get("/api/cases/c1")
    modules = resp.json()["modules"]
    assert "pleadings" in modules
    assert "discovery" in modules
    for mod in modules.values():
        assert "status" in mod
        assert "label" in mod
        assert "detail" in mod


# ── CRUD tests ────────────────────────────────────

def test_create_case(client):
    resp = client.post("/api/cases", json={
        "name": "Test v. Defendant",
        "type": "Personal Injury",
        "client": "Test Client",
        "opposing": "Test Defendant",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test v. Defendant"
    assert data["id"]  # auto-generated
    assert data["phase"] == 0
    assert data["specials"] == 0


def test_create_case_with_all_fields(client):
    resp = client.post("/api/cases", json={
        "name": "Full v. Case",
        "number": "25STCV99999",
        "type": "Employment",
        "client": "Jane Doe",
        "opposing": "Corp Inc",
        "phase": 3,
        "specials": 50000,
        "valuation": {"lo": 100, "mid": 200, "hi": 300},
        "deadline": {"date": "Apr 15", "text": "File motion", "urgent": True},
        "modules": {"pleadings": {"status": "active", "label": "Drafting", "detail": "In progress"}},
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["number"] == "25STCV99999"
    assert data["specials"] == 50000
    assert data["valuation"]["mid"] == 200
    assert data["deadline"]["urgent"] is True


def test_create_case_validation(client):
    # Missing required fields
    resp = client.post("/api/cases", json={"name": "Test"})
    assert resp.status_code == 422


def test_update_case(client):
    resp = client.put("/api/cases/c1", json={
        "specials": 100000,
        "phase": 4,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["specials"] == 100000
    assert data["phase"] == 4
    assert data["name"] == "Rodriguez v. Smith Trucking"  # unchanged


def test_update_case_not_found(client):
    resp = client.put("/api/cases/nonexistent", json={"specials": 999})
    assert resp.status_code == 404


def test_update_case_empty(client):
    resp = client.put("/api/cases/c1", json={})
    assert resp.status_code == 400


def test_delete_case(client):
    # Create one first
    create_resp = client.post("/api/cases", json={
        "name": "Delete Me v. Test",
        "type": "Test",
        "client": "Test",
        "opposing": "Test",
    })
    case_id = create_resp.json()["id"]

    resp = client.delete(f"/api/cases/{case_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    # Verify deleted
    resp = client.get(f"/api/cases/{case_id}")
    assert resp.status_code == 404


def test_delete_case_not_found(client):
    resp = client.delete("/api/cases/nonexistent")
    assert resp.status_code == 404

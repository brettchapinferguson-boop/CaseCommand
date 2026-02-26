"""Tests for database layer via API endpoints.

Database operations are tested through the HTTP API since aiosqlite
creates separate in-memory databases per connection. The TestClient
lifespan handler initializes and seeds the database properly.
"""


def test_seeded_cases_exist(client):
    """Database is seeded with 3 demo cases on init."""
    resp = client.get("/api/cases")
    assert resp.status_code == 200
    cases = resp.json()["cases"]
    assert len(cases) >= 3
    names = [c["name"] for c in cases]
    assert "Rodriguez v. Smith Trucking" in names
    assert "Chen v. Pacific Properties" in names
    assert "Williams v. TechStart" in names


def test_case_data_integrity(client):
    """Seeded case data is correctly stored and retrieved."""
    resp = client.get("/api/cases/c1")
    assert resp.status_code == 200
    case = resp.json()
    assert case["number"] == "24STCV12345"
    assert case["specials"] == 88000
    assert case["valuation"]["mid"] == 275
    assert case["deadline"]["urgent"] is True
    assert case["modules"]["pleadings"]["status"] == "complete"


def test_case_null_number(client):
    """Case with null number is stored correctly."""
    resp = client.get("/api/cases/c3")
    assert resp.status_code == 200
    assert resp.json()["number"] is None


def test_create_persists(client):
    """Created case can be retrieved."""
    create_resp = client.post("/api/cases", json={
        "name": "Persist v. Test",
        "type": "Test",
        "client": "Client",
        "opposing": "Opposing",
        "specials": 12345,
    })
    assert create_resp.status_code == 201
    case_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/cases/{case_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["specials"] == 12345


def test_update_persists(client):
    """Updated case data is persisted."""
    client.put("/api/cases/c2", json={"specials": 99999})
    resp = client.get("/api/cases/c2")
    assert resp.json()["specials"] == 99999


def test_delete_persists(client):
    """Deleted case is actually removed."""
    create_resp = client.post("/api/cases", json={
        "name": "Delete v. Persist",
        "type": "Test",
        "client": "Client",
        "opposing": "Opposing",
    })
    case_id = create_resp.json()["id"]

    client.delete(f"/api/cases/{case_id}")
    resp = client.get(f"/api/cases/{case_id}")
    assert resp.status_code == 404


def test_health_reports_case_count(client):
    """Health endpoint reports correct case count from DB."""
    resp = client.get("/api/health")
    assert resp.json()["cases"] >= 3

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

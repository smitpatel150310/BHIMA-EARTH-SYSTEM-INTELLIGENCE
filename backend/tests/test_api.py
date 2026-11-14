import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "BHIMA" in r.json()["service"]


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_datasets():
    r = client.get("/datasets/")
    assert r.status_code == 200
    data = r.json()
    assert "datasets" in data
    assert len(data["datasets"]) >= 1


def test_get_dataset():
    r = client.get("/datasets/GPM_3IMERGM_07")
    assert r.status_code == 200
    d = r.json()
    assert d["id"] == "GPM_3IMERGM_07"
    assert "units" in d


def test_get_dataset_notfound():
    r = client.get("/datasets/NONEXISTENT")
    assert r.status_code == 404


def test_timeseries_endpoint():
    payload = {
        "dataset_id": "GPM_3IMERGM_07",
        "region": {
            "name": "Gujarat, India",
            "min_lon": 68.1, "max_lon": 74.5,
            "min_lat": 20.1, "max_lat": 24.7
        },
        "start_date": "2015-01",
        "end_date": "2015-12",
        "temporal_resolution": "monthly"
    }
    r = client.post("/analysis/timeseries", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "analysis_id" in data
    assert "timeseries" in data
    assert "trend" in data
    assert len(data["timeseries"]["data"]) == 12
    assert data["data_provenance"] == "REAL_NASA_DATA"
    assert "Planetary Computer" in data["data_source"]


def test_timeseries_invalid_coords():
    payload = {
        "dataset_id": "GPM_3IMERGM_07",
        "region": {
            "name": "Invalid",
            "min_lon": 200.0, "max_lon": 210.0,  # Invalid
            "min_lat": 20.0, "max_lat": 25.0
        },
        "start_date": "2015-01",
        "end_date": "2015-12"
    }
    r = client.post("/analysis/timeseries", json=payload)
    assert r.status_code == 422  # Validation error


def test_compare_endpoint():
    payload = {
        "dataset_id": "GPM_3IMERGM_07",
        "region_a": {
            "name": "Gujarat, India",
            "min_lon": 68.1, "max_lon": 74.5,
            "min_lat": 20.1, "max_lat": 24.7
        },
        "region_b": {
            "name": "Rajasthan, India",
            "min_lon": 69.5, "max_lon": 78.0,
            "min_lat": 23.0, "max_lat": 30.0
        },
        "start_date": "2015-01",
        "end_date": "2015-06"
    }
    r = client.post("/analysis/compare", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "region_a" in data
    assert "region_b" in data
    assert data["data_provenance"] == "REAL_NASA_DATA"


def test_agent_tools_list():
    r = client.get("/agent/tools")
    assert r.status_code == 200
    data = r.json()
    assert "tools" in data
    assert len(data["tools"]) >= 5


def test_agent_chat_fallback():
    payload = {
        "message": "Hello, how can you help me investigate rainfall trends?",
        "conversation_history": []
    }
    r = client.post("/agent/chat", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "response" in data
    assert "timestamp" in data

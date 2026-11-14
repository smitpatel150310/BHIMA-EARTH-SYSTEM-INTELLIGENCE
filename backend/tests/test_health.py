import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "timestamp" in data
    assert "version" in data
    assert "service" in data


def test_healthz_alias_for_kubernetes_and_cloudrun():
    r = client.get("/healthz")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_readiness_probe():
    r = client.get("/readiness")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("ready", "initializing")
    assert "persistent_store_ready" in data
    assert "timestamp" in data


def test_root_service_info():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "BHIMA" in data["service"]
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"

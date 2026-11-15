import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.cache_reader import cache_reading_service

client = TestClient(app)

# The 9 canonical target regions verified in cache
TARGET_REGIONS = [
    {
        "name": "Gujarat, India",
        "min_lon": 68.1, "max_lon": 74.5, "min_lat": 20.1, "max_lat": 24.7,
        "expected_months": 72
    },
    {
        "name": "Amazon Basin",
        "min_lon": -73.0, "max_lon": -50.0, "min_lat": -15.0, "max_lat": 5.0,
        "expected_months": 72
    },
    {
        "name": "Sahel (West Africa)",
        "min_lon": -15.0, "max_lon": 40.0, "min_lat": 10.0, "max_lat": 20.0,
        "expected_months": 72
    },
    {
        "name": "California, USA",
        "min_lon": -124.5, "max_lon": -114.1, "min_lat": 32.5, "max_lat": 42.0,
        "expected_months": 72
    },
    {
        "name": "Murray-Darling Basin",
        "min_lon": 138.0, "max_lon": 149.0, "min_lat": -37.0, "max_lat": -24.0,
        "expected_months": 72
    },
    {
        "name": "Monsoon Asia",
        "min_lon": 60.0, "max_lon": 110.0, "min_lat": 10.0, "max_lat": 35.0,
        "expected_months": 72
    },
    {
        "name": "Sahara Desert",
        "min_lon": -5.0, "max_lon": 35.0, "min_lat": 20.0, "max_lat": 30.0,
        "expected_months": 72
    },
    {
        "name": "Great Plains, USA",
        "min_lon": -104.0, "max_lon": -96.0, "min_lat": 32.0, "max_lat": 48.0,
        "expected_months": 72
    },
    {
        "name": "Central Gujarat (Vadodara)",
        "min_lon": 73.1, "max_lon": 73.3, "min_lat": 22.1, "max_lat": 22.5,
        "expected_months": 72
    },
]


@pytest.mark.parametrize("reg", TARGET_REGIONS)
def test_each_target_region_loads_72_months(reg):
    """Verify that every target region reads its full 72-month cache with real data."""
    payload = {
        "dataset_id": "GPM_3IMERGM_07",
        "region": {
            "name": reg["name"],
            "min_lon": reg["min_lon"],
            "max_lon": reg["max_lon"],
            "min_lat": reg["min_lat"],
            "max_lat": reg["max_lat"]
        },
        "start_date": "2015-01",
        "end_date": "2020-12",
        "temporal_resolution": "monthly"
    }

    resp = client.post("/analysis/timeseries", json=payload)
    assert resp.status_code == 200, f"Failed for {reg['name']}: {resp.text}"

    data = resp.json()
    assert "analysis_id" in data
    assert "timeseries" in data
    assert "trend" in data
    assert "statistics" in data

    ts = data["timeseries"]
    assert len(ts["data"]) == reg["expected_months"], f"{reg['name']} expected {reg['expected_months']}, got {len(ts['data'])}"
    assert data["data_provenance"] == "REAL_NASA_DATA"
    assert "Local" in data["data_source"] or "Planetary Computer" in data["data_source"]

    # Trend stats
    trend = data["trend"]
    assert "slope" in trend
    assert "p_value" in trend
    assert trend["trend_direction"] in ("increasing", "decreasing", "no_trend")


def test_date_filtering_on_cached_region():
    """Verify that selecting a sub-range (e.g. 2016-01 to 2018-12) correctly yields 36 months."""
    payload = {
        "dataset_id": "GPM_3IMERGM_07",
        "region": {
            "name": "Gujarat, India",
            "min_lon": 68.1, "max_lon": 74.5, "min_lat": 20.1, "max_lat": 24.7
        },
        "start_date": "2016-01",
        "end_date": "2018-12",
        "temporal_resolution": "monthly"
    }

    resp = client.post("/analysis/timeseries", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["timeseries"]["data"]) == 36
    assert data["timeseries"]["data"][0]["date"] == "2016-01"
    assert data["timeseries"]["data"][-1]["date"] == "2018-12"


def test_region_comparison_cached():
    """Verify that comparing two regions reads both independently from local cache."""
    payload = {
        "dataset_id": "GPM_3IMERGM_07",
        "region_a": {
            "name": "Amazon Basin",
            "min_lon": -73.0, "max_lon": -50.0, "min_lat": -15.0, "max_lat": 5.0
        },
        "region_b": {
            "name": "Sahel (West Africa)",
            "min_lon": -15.0, "max_lon": 40.0, "min_lat": 10.0, "max_lat": 20.0
        },
        "start_date": "2015-01",
        "end_date": "2020-12"
    }

    resp = client.post("/analysis/compare", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert "region_a" in data
    assert "region_b" in data
    assert len(data["region_a"]["timeseries"]["data"]) == 72
    assert len(data["region_b"]["timeseries"]["data"]) == 72
    assert data["region_a"]["timeseries"]["region"] == "Amazon Basin"
    assert data["region_b"]["timeseries"]["region"] == "Sahel (West Africa)"


def test_missing_cache_produces_clear_error():
    """Verify that an uncached custom coordinate returns a clear 404 message."""
    payload = {
        "dataset_id": "GPM_3IMERGM_07",
        "region": {
            "name": "Uncached Remote Island",
            "min_lon": -170.0, "max_lon": -169.0, "min_lat": -80.0, "max_lat": -79.0
        },
        "start_date": "2015-01",
        "end_date": "2020-12"
    }

    resp = client.post("/analysis/timeseries", json=payload)
    assert resp.status_code == 404
    assert "No pre-collected observation records found" in resp.json()["detail"]

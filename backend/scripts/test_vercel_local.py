import os
import sys
import time

def test_vercel_entry_points():
    print("=" * 70)
    print("VERCEL LOCAL INTEGRATION TEST SUITE")
    print("=" * 70)

    # 1. Test backend/api/index.py import
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, backend_dir)
    os.environ["VERCEL"] = "1"
    os.environ["ENVIRONMENT"] = "production"

    print("\n[Step 1] Testing backend/api/index.py import...")
    import importlib.util
    spec = importlib.util.spec_from_file_location("vercel_backend_index", os.path.join(backend_dir, "api", "index.py"))
    backend_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend_module)
    app = backend_module.app
    print(f"  -> Successfully imported FastAPI app '{app.title}' v{app.version}")

    # 2. Test root api/index.py import
    print("\n[Step 2] Testing root api/index.py import...")
    root_dir = os.path.abspath(os.path.join(backend_dir, ".."))
    spec_root = importlib.util.spec_from_file_location("vercel_root_index", os.path.join(root_dir, "api", "index.py"))
    root_module = importlib.util.module_from_spec(spec_root)
    spec_root.loader.exec_module(root_module)
    print(f"  -> Successfully imported root entry point '{root_module.app.title}'")

    # 3. Test HTTP routes via TestClient with VERCEL=1
    print("\n[Step 3] Testing API endpoints via FastAPI TestClient (VERCEL=1)...")
    from fastapi.testclient import TestClient
    client = TestClient(app)

    # Root
    r_root = client.get("/")
    assert r_root.status_code == 200, f"Root failed: {r_root.status_code}"
    print(f"  [PASS] GET / -> {r_root.json().get('service')}")

    # Health
    r_health = client.get("/health")
    assert r_health.status_code == 200, f"Health failed: {r_health.status_code}"
    print(f"  [PASS] GET /health -> status: {r_health.json().get('status')}")

    # Readiness
    r_ready = client.get("/readiness")
    assert r_ready.status_code == 200, f"Readiness failed: {r_ready.status_code}"
    print(f"  [PASS] GET /readiness -> status: {r_ready.json().get('status')}, store_ready: {r_ready.json().get('persistent_store_ready')}")

    # Datasets
    r_ds = client.get("/datasets/")
    assert r_ds.status_code == 200
    datasets = r_ds.json().get("datasets", [])
    print(f"  [PASS] GET /datasets/ -> {len(datasets)} datasets registered")

    # Datasets coverage
    r_cov = client.get("/datasets/coverage", params={"dataset_id": "GPM_3IMERGM_07"})
    assert r_cov.status_code == 200
    print(f"  [PASS] GET /datasets/coverage?dataset_id=GPM_3IMERGM_07 -> coverage metadata returned")

    # Cache status
    r_cache = client.get("/analysis/cache/status", params={
        "dataset_id": "GPM_3IMERGM_07",
        "min_lon": 73.10, "max_lon": 73.30,
        "min_lat": 22.10, "max_lat": 22.50,
        "start_date": "2015-01", "end_date": "2020-12"
    })
    assert r_cache.status_code == 200
    cache_data = r_cache.json()
    print(f"  [PASS] GET /analysis/cache/status -> cached_months: {cache_data.get('cached_months')}/72, status: {cache_data.get('cache_status')}")

    # Timeseries (Gujarat Preprocessed Region)
    t0 = time.perf_counter()
    r_ts = client.post("/analysis/timeseries", json={
        "dataset_id": "GPM_3IMERGM_07",
        "region": {
            "name": "Gujarat, India",
            "min_lon": 73.10, "max_lon": 73.30,
            "min_lat": 22.10, "max_lat": 22.50
        },
        "start_date": "2015-01",
        "end_date": "2020-12",
        "temporal_resolution": "monthly"
    })
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert r_ts.status_code == 200, f"Timeseries failed: {r_ts.text}"
    ts_data = r_ts.json()
    n_pts = len(ts_data.get("timeseries", {}).get("data", []))
    print(f"  [PASS] POST /analysis/timeseries -> {n_pts} observations returned in {elapsed_ms:.1f}ms")
    print(f"         Provenance: {ts_data.get('data_provenance')}, Source: {ts_data.get('data_source')}")
    print(f"         Trend: direction={ts_data.get('trend', {}).get('trend_direction')}, p={ts_data.get('trend', {}).get('p_value'):.4f}")

    # Compare
    r_cmp = client.post("/analysis/compare", json={
        "dataset_id": "GPM_3IMERGM_07",
        "region_a": {
            "name": "Gujarat, India",
            "min_lon": 73.10, "max_lon": 73.30,
            "min_lat": 22.10, "max_lat": 22.50
        },
        "region_b": {
            "name": "California, USA",
            "min_lon": -124.50, "max_lon": -114.10,
            "min_lat": 32.50, "max_lat": 42.00
        },
        "start_date": "2015-01",
        "end_date": "2020-12"
    })
    assert r_cmp.status_code == 200, f"Compare failed: {r_cmp.text}"
    cmp_data = r_cmp.json()
    print(f"  [PASS] POST /analysis/compare -> compared Region A ({len(cmp_data['region_a']['timeseries']['data'])} obs) & Region B ({len(cmp_data['region_b']['timeseries']['data'])} obs)")

    # Cache summary
    r_sum = client.get("/analysis/cache/summary")
    assert r_sum.status_code == 200
    print(f"  [PASS] GET /analysis/cache/summary -> {r_sum.json().get('cached_series_count')} series registered")

    print("\n" + "=" * 70)
    print("ALL VERCEL LOCAL INTEGRATION TESTS PASSED (100% SUCCESS)!")
    print("=" * 70)

if __name__ == "__main__":
    test_vercel_entry_points()

import time
import requests

BASE_URL = "http://127.0.0.1:8000"

def test_cache_endpoints():
    print("Testing GET /analysis/cache/summary...")
    try:
        t0 = time.perf_counter()
        resp = requests.get(f"{BASE_URL}/analysis/cache/summary", timeout=10)
        dur = (time.perf_counter() - t0) * 1000
        print(f"Summary status: {resp.status_code} in {dur:.2f}ms")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Total SQLite records: {data.get('total_records')}")
            print(f"Total Cached series: {data.get('cached_series_count')}")
    except Exception as e:
        print(f"Failed to connect to backend on port 8000: {e}")

    regions = [
        {"name": "Gujarat (Explorer Box)", "min_lon": 73.10, "max_lon": 73.30, "min_lat": 22.10, "max_lat": 22.50},
        {"name": "Gujarat Full State", "min_lon": 68.10, "max_lon": 74.50, "min_lat": 20.10, "max_lat": 24.70},
        {"name": "California, USA", "min_lon": -124.50, "max_lon": -114.10, "min_lat": 32.50, "max_lat": 42.00},
        {"name": "Amazon Basin", "min_lon": -73.0, "max_lon": -50.0, "min_lat": -15.0, "max_lat": 5.0},
        {"name": "Sahel (West Africa)", "min_lon": -15.0, "max_lon": 40.0, "min_lat": 10.0, "max_lat": 20.0},
    ]

    for reg in regions:
        try:
            t0 = time.perf_counter()
            q = f"dataset_id=GPM_3IMERGM_07&min_lon={reg['min_lon']}&max_lon={reg['max_lon']}&min_lat={reg['min_lat']}&max_lat={reg['max_lat']}&start_date=2015-01&end_date=2020-12"
            resp = requests.get(f"{BASE_URL}/analysis/cache/status?{q}", timeout=5)
            dur = (time.perf_counter() - t0) * 1000
            if resp.status_code == 200:
                d = resp.json()
                print(f"{reg['name']:<24} | Status: {d.get('cache_status')} | Cached: {d.get('cached_months')}/{d.get('total_months')} | API latency: {dur:.2f}ms | Provenance: {d.get('data_provenance')}")
            else:
                print(f"{reg['name']:<24} | Error {resp.status_code}")
        except Exception as e:
            print(f"{reg['name']:<24} | Failed: {e}")

if __name__ == "__main__":
    test_cache_endpoints()

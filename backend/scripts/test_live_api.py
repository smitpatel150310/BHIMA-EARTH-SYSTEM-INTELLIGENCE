import httpx
import json
import time

base_url = "http://127.0.0.1:8000"

print("--- 1. Testing GET /health ---")
r = httpx.get(f"{base_url}/health", timeout=5)
print(f"Status: {r.status_code}, Response: {r.json()}")
assert r.status_code == 200

print("\n--- 2. Testing GET /datasets/ ---")
r = httpx.get(f"{base_url}/datasets/", timeout=5)
print(f"Status: {r.status_code}, Total datasets: {len(r.json().get('datasets', []))}")
assert r.status_code == 200

print("\n--- 3. Testing POST /analysis/timeseries (Exact Earth Explorer Gujarat Request) ---")
payload = {
    "dataset_id": "GPM_3IMERGM_07",
    "region": {
        "name": "Gujarat, India",
        "min_lon": 73.10, "max_lon": 73.30,
        "min_lat": 22.10, "max_lat": 22.50
    },
    "start_date": "2015-01",
    "end_date": "2020-12",
    "temporal_resolution": "monthly"
}

t0 = time.time()
# Test with async_mode=true (how frontend calls it)
r = httpx.post(f"{base_url}/analysis/timeseries?async_mode=true", json=payload, timeout=10)
dur_ms = (time.time() - t0) * 1000
print(f"Request completed in {dur_ms:.2f} ms with HTTP {r.status_code}")
data = r.json()

if "job_id" in data:
    print(f"Received Job ID: {data['job_id']}. Polling job status...")
    job_id = data["job_id"]
    for i in range(10):
        poll = httpx.get(f"{base_url}/analysis/jobs/{job_id}", timeout=5).json()
        print(f"Poll {i}: status={poll.get('status')}, progress={poll.get('progress_pct')}%")
        if poll.get("status") in ("completed", "failed"):
            data = poll.get("result", {})
            break
        time.sleep(1)

print("\n--- TIMESERIES RESPONSE VERIFICATION ---")
print(f"Analysis ID: {data.get('analysis_id')}")
print(f"Cache Status: {data.get('cache_status')} (Hit: {data.get('cache_hit')})")
print(f"Lookup Duration: {data.get('lookup_duration_ms')} ms")
print(f"Provenance: {data.get('data_provenance')}")
print(f"Data Source: {data.get('data_source')}")
pts = data.get("timeseries", {}).get("data", [])
print(f"Total Observations: {len(pts)} months")
if pts:
    print(f"First observation: {pts[0]}")
    print(f"Sample wet season (2017-07): {[p for p in pts if p['date'] == '2017-07']}")
    print(f"Sample wet season (2018-07): {[p for p in pts if p['date'] == '2018-07']}")
    print(f"Sample wet season (2019-09): {[p for p in pts if p['date'] == '2019-09']}")
    print(f"Last observation: {pts[-1]}")
print(f"Statistics: {data.get('statistics')}")
print(f"Trend: {data.get('trend')}")

assert len(pts) == 72, f"Expected 72 observations, got {len(pts)}"
assert data.get("data_provenance") == "REAL_NASA_DATA"
assert dur_ms < 500, f"Cache retrieval took too long: {dur_ms:.2f} ms"

print("\n--- 4. Testing Repeated Request (FastAPI Stability & Persistence) ---")
for attempt in range(1, 4):
    t_start = time.time()
    r = httpx.post(f"{base_url}/analysis/timeseries?async_mode=true", json=payload, timeout=10)
    dur = (time.time() - t_start) * 1000
    assert r.status_code == 200
    print(f"Attempt {attempt}: HTTP {r.status_code} in {dur:.2f} ms (Cache Status: {r.json().get('cache_status')})")

print("\n--- ALL LIVE API TESTS COMPLETED SUCCESSFULLY! ---")

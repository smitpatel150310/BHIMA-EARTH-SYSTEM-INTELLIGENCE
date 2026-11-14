import os
import sys
import time
from typing import Dict, Any

# Ensure backend root is on path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, backend_dir)

os.environ["VERCEL"] = "1"
os.environ["ENVIRONMENT"] = "production"

from fastapi.testclient import TestClient
from app.main import app

REGIONS = [
    {
        "name": "Gujarat (Explorer Box)",
        "min_lon": 73.10, "min_lat": 22.10, "max_lon": 73.30, "max_lat": 22.50,
    },
    {
        "name": "Gujarat Full State",
        "min_lon": 68.10, "min_lat": 20.10, "max_lon": 74.50, "max_lat": 24.70,
    },
    {
        "name": "Amazon Basin",
        "min_lon": -73.00, "min_lat": -15.00, "max_lon": -50.00, "max_lat": 5.00,
    },
    {
        "name": "Sahel (West Africa)",
        "min_lon": -15.00, "min_lat": 10.00, "max_lon": 40.00, "max_lat": 20.00,
    },
    {
        "name": "California, USA",
        "min_lon": -124.50, "min_lat": 32.50, "max_lon": -114.10, "max_lat": 42.00,
    },
    {
        "name": "Murray-Darling Basin",
        "min_lon": 138.00, "min_lat": -37.00, "max_lon": 149.00, "max_lat": -24.00,
    },
    {
        "name": "Monsoon Asia",
        "min_lon": 60.00, "min_lat": 10.00, "max_lon": 110.00, "max_lat": 35.00,
    },
    {
        "name": "Sahara Desert",
        "min_lon": -5.00, "min_lat": 20.00, "max_lon": 35.00, "max_lat": 30.00,
    },
    {
        "name": "Great Plains, USA",
        "min_lon": -104.00, "min_lat": 32.00, "max_lon": -96.00, "max_lat": 48.00,
    },
]


def verify_all_regions():
    print("=" * 80)
    print("BHIMA — NINE REGIONAL SCIENTIFIC DATA EXTRACTION & TREND VERIFICATION")
    print("Testing under simulated Vercel Serverless environment (VERCEL=1)")
    print("=" * 80)

    client = TestClient(app)
    results = []

    for idx, reg in enumerate(REGIONS, start=1):
        payload = {
            "dataset_id": "GPM_3IMERGM_07",
            "region": reg,
            "start_date": "2015-01",
            "end_date": "2020-12",
            "temporal_resolution": "monthly",
        }

        t0 = time.perf_counter()
        resp = client.post("/analysis/timeseries", json=payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        if resp.status_code != 200:
            print(f"[{idx}/9] FAILED: {reg['name']} -> HTTP {resp.status_code}: {resp.text[:100]}")
            results.append({"region": reg["name"], "success": False, "error": resp.text})
            continue

        data = resp.json()
        ts = data.get("timeseries", {})
        data_pts = ts.get("data", [])
        n_obs = len(data_pts)
        valid_obs = sum(1 for d in data_pts if d.get("value") is not None)
        trend = data.get("trend", {})
        provenance = data.get("data_provenance")
        data_src = data.get("data_source")

        # Basic assertions
        assert n_obs == 72, f"Expected 72 observations, got {n_obs}"
        assert provenance == "REAL_NASA_DATA", f"Expected REAL_NASA_DATA, got {provenance}"
        assert valid_obs >= 30, f"Expected valid observations >= 30, got {valid_obs}"
        assert "p_value" in trend or "trend_direction" in trend, f"Trend missing in {reg['name']}"

        mean_val = data.get("statistics", {}).get("mean", 0.0)

        print(f"[{idx}/9] SUCCESS: {reg['name']:<25} | {valid_obs}/{n_obs} valid months | Mean: {mean_val:6.2f} mm/mo | Latency: {elapsed_ms:5.1f}ms")
        print(f"       Provenance: {provenance} | Trend: {trend.get('trend_direction')} (p={trend.get('p_value'):.4f}, slope={trend.get('slope'):.3f})")

        results.append({
            "region": reg["name"],
            "success": True,
            "observations": n_obs,
            "valid_observations": valid_obs,
            "mean_precipitation_mm": round(mean_val, 2),
            "trend_direction": trend.get("trend_direction"),
            "p_value": trend.get("p_value"),
            "latency_ms": round(elapsed_ms, 1),
            "provenance": provenance,
        })

    print("=" * 80)
    all_passed = all(r["success"] for r in results)
    if all_passed:
        print(f"ALL 9 REGIONS VERIFIED SUCCESSFULLY! (9/9 PASS - 100% REAL SATELLITE DATA)")
    else:
        print(f"SOME REGIONS FAILED!")
    print("=" * 80)
    return all_passed


if __name__ == "__main__":
    success = verify_all_regions()
    if not success:
        sys.exit(1)

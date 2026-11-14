import sys
import os
import time
import calendar
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.data_access import get_cached_gpm_dataset
from app.core.persistent_cache import persistent_store, get_region_key

print(f"[{time.strftime('%X')}] Initializing GPM IMERG 72-Month Gujarat Cache Engine...", flush=True)

# Target regions:
# Region 1: Specific box from Earth Explorer user report: West: 73.10, South: 22.10, East: 73.30, North: 22.50
# Region 2: Full Gujarat preset: West: 68.10, South: 20.10, East: 74.50, North: 24.70

regions = [
    {"name": "Gujarat (Explorer Box)", "min_lon": 73.10, "max_lon": 73.30, "min_lat": 22.10, "max_lat": 22.50},
    {"name": "Gujarat (Full State)", "min_lon": 68.10, "max_lon": 74.50, "min_lat": 20.10, "max_lat": 24.70},
]

t_open = time.perf_counter()
ds = get_cached_gpm_dataset()
print(f"[{time.strftime('%X')}] GPM IMERG store opened in {time.perf_counter() - t_open:.2f}s", flush=True)

da = ds["precipitationCal"]

# Date range: 2015-01 to 2020-12 (72 months)
all_months = [m.strftime("%Y-%m") for m in pd.date_range("2015-01", "2020-12", freq="MS")]
print(f"[{time.strftime('%X')}] Target period: {all_months[0]} to {all_months[-1]} ({len(all_months)} months)", flush=True)

for reg in regions:
    min_lon = reg["min_lon"]
    max_lon = reg["max_lon"]
    min_lat = reg["min_lat"]
    max_lat = reg["max_lat"]
    reg_key = get_region_key(min_lon, min_lat, max_lon, max_lat)
    print(f"\n[{time.strftime('%X')}] Processing {reg['name']} ({reg_key})...", flush=True)

    # Check already cached months
    cached_recs, missing_months, audit = persistent_store.get_monthly_series(
        dataset_id="GPM_3IMERGM_07",
        region_key=reg_key,
        start_date=all_months[0],
        end_date=all_months[-1],
        variable="precipitationCal"
    )
    print(f"[{time.strftime('%X')}] Already cached: {len(cached_recs)}/72 months. Missing: {len(missing_months)} months.", flush=True)

    if not missing_months:
        print(f"[{time.strftime('%X')}] All 72 months already cached for {reg['name']}!", flush=True)
        continue

    def fetch_one_month(m_str: str):
        t_m = time.perf_counter()
        m = pd.to_datetime(m_str)
        slice_start = f"{m.year}-{m.month:02d}-15 00:00"
        slice_end = f"{m.year}-{m.month:02d}-15 05:30"
        days_in_m = calendar.monthrange(m.year, m.month)[1]
        hours_in_m = days_in_m * 24

        try:
            sub = da.sel(
                time=slice(slice_start, slice_end),
                lon=slice(min_lon, max_lon),
                lat=slice(min_lat, max_lat)
            )
            vals = sub.values
            valid_mask = ~np.isnan(vals)
            n_valid = int(valid_mask.sum())
            total_pts = int(vals.size)

            if n_valid > 0:
                mean_mm_hr = float(vals[valid_mask].mean())
                monthly_accum_mm = mean_mm_hr * hours_in_m
                cov_frac = float(n_valid / total_pts) if total_pts > 0 else 0.0
            else:
                mean_mm_hr = 0.0
                monthly_accum_mm = 0.0
                cov_frac = 0.0

            fetch_time_ms = (time.perf_counter() - t_m) * 1000.0

            rec = {
                "date": m_str,
                "value": monthly_accum_mm,
                "valid_pixels": n_valid,
                "coverage_fraction": cov_frac,
                "n_observations": int(vals.shape[0]),
                "fetch_time_ms": fetch_time_ms,
                "data_provenance": "REAL_NASA_DATA",
                "data_source": "Microsoft Planetary Computer GPM IMERG (zarr-abfs)",
                "units": "mm/month",
            }

            # Checkpoint immediately to SQLite
            persistent_store.persist_monthly_series(
                dataset_id="GPM_3IMERGM_07",
                region_key=reg_key,
                records=[rec],
                variable="precipitationCal",
                aggregation_method="SAMPLING_MIDMONTH_CHUNK",
                data_provenance="REAL_NASA_DATA",
                data_source="Microsoft Planetary Computer GPM IMERG (zarr-abfs)",
                units="mm/month",
            )
            print(f"[{time.strftime('%X')}] {m_str}: accum={monthly_accum_mm:.2f} mm/month (mean rate={mean_mm_hr:.4f} mm/hr) in {fetch_time_ms/1000:.2f}s [CHECKPOINTED]", flush=True)
            return rec
        except Exception as ex:
            print(f"[{time.strftime('%X')}] {m_str} ERROR: {ex}", flush=True)
            return None

    # Fetch in worker pool
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(fetch_one_month, missing_months))

print(f"\n[{time.strftime('%X')}] Cache population complete!", flush=True)

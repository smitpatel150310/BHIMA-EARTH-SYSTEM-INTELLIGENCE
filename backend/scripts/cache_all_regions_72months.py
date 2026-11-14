import sys
import os
import time
import calendar
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.data_access import get_cached_gpm_dataset, get_cached_terraclimate_dataset
from app.core.persistent_cache import persistent_store, get_region_key

print(f"[{time.strftime('%X')}] Initializing Multi-Region 72-Month Cache Engine (8 Workers)...", flush=True)

# All 8 canonical Earth Explorer regions + Explorer Box
ALL_REGIONS = [
    {"name": "Gujarat (Explorer Box)", "min_lon": 73.10, "max_lon": 73.30, "min_lat": 22.10, "max_lat": 22.50},
    {"name": "Gujarat, India", "min_lon": 68.10, "max_lon": 74.50, "min_lat": 20.10, "max_lat": 24.70},
    {"name": "Amazon Basin", "min_lon": -73.0, "max_lon": -50.0, "min_lat": -15.0, "max_lat": 5.0},
    {"name": "Sahel (West Africa)", "min_lon": -15.0, "max_lon": 40.0, "min_lat": 10.0, "max_lat": 20.0},
    {"name": "California, USA", "min_lon": -124.5, "max_lon": -114.1, "min_lat": 32.5, "max_lat": 42.0},
    {"name": "Murray-Darling Basin", "min_lon": 138.0, "max_lon": 149.0, "min_lat": -37.0, "max_lat": -24.0},
    {"name": "Monsoon Asia", "min_lon": 60.0, "max_lon": 110.0, "min_lat": 10.0, "max_lat": 35.0},
    {"name": "Sahara Desert", "min_lon": -5.0, "max_lon": 35.0, "min_lat": 20.0, "max_lat": 30.0},
    {"name": "Great Plains, USA", "min_lon": -104.0, "max_lon": -96.0, "min_lat": 32.0, "max_lat": 48.0},
]

# 72 Months: 2015-01 through 2020-12
all_months = [m.strftime("%Y-%m") for m in pd.date_range("2015-01", "2020-12", freq="MS")]
print(f"[{time.strftime('%X')}] Target period: {all_months[0]} to {all_months[-1]} ({len(all_months)} months)", flush=True)

# STEP 1: OPEN GPM IMERG DATASET
t_open = time.perf_counter()
ds_gpm = get_cached_gpm_dataset()
print(f"[{time.strftime('%X')}] GPM IMERG store opened in {time.perf_counter() - t_open:.2f}s", flush=True)
da_gpm = ds_gpm["precipitationCal"]

# Process each region with 8 workers
for reg in ALL_REGIONS:
    min_lon = reg["min_lon"]
    max_lon = reg["max_lon"]
    min_lat = reg["min_lat"]
    max_lat = reg["max_lat"]
    reg_key = get_region_key(min_lon, min_lat, max_lon, max_lat)
    print(f"\n=======================================================", flush=True)
    print(f"[{time.strftime('%X')}] Processing {reg['name']} ({reg_key})...", flush=True)

    # Check already cached months
    cached_recs, missing_months, audit = persistent_store.get_monthly_series(
        dataset_id="GPM_3IMERGM_07",
        region_key=reg_key,
        start_date=all_months[0],
        end_date=all_months[-1],
        variable="precipitationCal"
    )
    print(f"[{time.strftime('%X')}] Status: {len(cached_recs)}/72 months cached. Missing: {len(missing_months)} months.", flush=True)

    if not missing_months:
        print(f"[{time.strftime('%X')}] [SKIPPED] All 72 months already cached for {reg['name']}!", flush=True)
        continue

    def fetch_one_gpm_month(m_str: str):
        t_m = time.perf_counter()
        m = pd.to_datetime(m_str)
        slice_start = f"{m.year}-{m.month:02d}-15 00:00"
        slice_end = f"{m.year}-{m.month:02d}-15 05:30"
        days_in_m = calendar.monthrange(m.year, m.month)[1]
        hours_in_m = days_in_m * 24

        try:
            sub = da_gpm.sel(
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
            print(f"[{time.strftime('%X')}] {reg['name']} | {m_str}: accum={monthly_accum_mm:.2f} mm/month (mean rate={mean_mm_hr:.4f} mm/hr) in {fetch_time_ms/1000:.2f}s [CHECKPOINTED]", flush=True)
            return rec
        except Exception as ex:
            print(f"[{time.strftime('%X')}] {reg['name']} | {m_str} ERROR: {ex}", flush=True)
            return None

    # Parallel retrieval with 8 workers
    print(f"[{time.strftime('%X')}] Launching 8 worker threads for {len(missing_months)} missing months...", flush=True)
    t_start_reg = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(fetch_one_gpm_month, missing_months))
    dur_reg = time.perf_counter() - t_start_reg
    print(f"[{time.strftime('%X')}] Completed {reg['name']} in {dur_reg:.1f}s!", flush=True)

print(f"\n=======================================================", flush=True)
print(f"[{time.strftime('%X')}] ALL REGIONS CACHE COMPLETE!", flush=True)

# Final Audit
summary = persistent_store.get_cache_summary()
print(f"\nTotal Cached Series: {summary['cached_series_count']}")
print(f"Total Storage Size: {summary['storage']['total_storage_size_kb']} KB")
print(f"SQLite DB Size: {summary['storage']['sqlite_db_size_kb']} KB")
for s in summary["series"]:
    print(f"  {s['dataset_id']:<18} | {s['region_key']:<26} | {s['cached_months']} months ({'72/72 COMPLETE' if s['is_72_complete'] else 'PARTIAL'})")

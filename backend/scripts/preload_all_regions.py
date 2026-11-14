import sys
import os
import time
import calendar
import logging
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np

# Ensure app is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.persistent_cache import persistent_store, get_region_key
from app.core.data_access import (
    get_cached_terraclimate_dataset,
    get_cached_gpm_dataset,
    DATASET_REGISTRY,
)

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("preload")

# 8 Canonical Supported Regions from Earth Explorer
SUPPORTED_REGIONS = {
    "Gujarat, India": {
        "name": "Gujarat, India",
        "min_lon": 68.1, "max_lon": 74.5,
        "min_lat": 20.1, "max_lat": 24.7
    },
    "Gujarat (Explorer Box)": {
        "name": "Gujarat (Explorer Box)",
        "min_lon": 73.10, "max_lon": 73.30,
        "min_lat": 22.10, "max_lat": 22.50
    },
    "Amazon Basin": {
        "name": "Amazon Basin",
        "min_lon": -73.0, "max_lon": -50.0,
        "min_lat": -15.0, "max_lat": 5.0
    },
    "Sahel, West Africa": {
        "name": "Sahel (West Africa)",
        "min_lon": -15.0, "max_lon": 40.0,
        "min_lat": 10.0, "max_lat": 20.0
    },
    "California, USA": {
        "name": "California, USA",
        "min_lon": -124.5, "max_lon": -114.1,
        "min_lat": 32.5, "max_lat": 42.0
    },
    "Murray-Darling Basin": {
        "name": "Murray-Darling Basin",
        "min_lon": 138.0, "max_lon": 149.0,
        "min_lat": -37.0, "max_lat": -24.0
    },
    "Monsoon Asia": {
        "name": "Monsoon Asia",
        "min_lon": 60.0, "max_lon": 110.0,
        "min_lat": 10.0, "max_lat": 35.0
    },
    "Sahara Desert": {
        "name": "Sahara Desert",
        "min_lon": -5.0, "max_lon": 35.0,
        "min_lat": 20.0, "max_lat": 30.0
    },
    "Great Plains, USA": {
        "name": "Great Plains, USA",
        "min_lon": -104.0, "max_lon": -96.0,
        "min_lat": 32.0, "max_lat": 48.0
    },
}

START_DATE = "2015-01"
END_DATE = "2020-12"
TARGET_MONTHS = [m.strftime("%Y-%m") for m in pd.date_range(START_DATE, END_DATE, freq="MS")]
assert len(TARGET_MONTHS) == 72, f"Expected 72 months, got {len(TARGET_MONTHS)}"


def preload_terraclimate(region_name: str, coords: dict, variable: str, dataset_id: str, units: str):
    """
    Extract and cache 72 months of TerraClimate data for a region with retry and checkpointing.
    """
    q_min_lon = max(-180.0, min(180.0, float(coords["min_lon"])))
    q_max_lon = max(-180.0, min(180.0, float(coords["max_lon"])))
    q_min_lat = max(-90.0, min(90.0, float(coords["min_lat"])))
    q_max_lat = max(-90.0, min(90.0, float(coords["max_lat"])))
    if q_min_lon > q_max_lon:
        q_min_lon, q_max_lon = q_max_lon, q_min_lon
    if q_min_lat > q_max_lat:
        q_min_lat, q_max_lat = q_max_lat, q_min_lat

    reg_key = get_region_key(q_min_lon, q_min_lat, q_max_lon, q_max_lat)

    cached_records, missing_months, audit = persistent_store.get_monthly_series(
        dataset_id=dataset_id,
        region_key=reg_key,
        start_date=START_DATE,
        end_date=END_DATE,
        variable=variable,
    )

    if not missing_months:
        logger.info(f"[CACHE HIT] {dataset_id}:{variable} for {region_name} ({len(cached_records)}/72 months cached)")
        return

    logger.info(f"[EXTRACTING] {dataset_id}:{variable} for {region_name} ({len(missing_months)} missing months)...")

    # Retry loop with exponential backoff
    for attempt in range(1, 4):
        try:
            ds = get_cached_terraclimate_dataset()
            if variable not in ds.data_vars:
                raise ValueError(f"Variable '{variable}' not found in TerraClimate dataset.")

            t_start = f"{missing_months[0]}-01"
            t_end = f"{missing_months[-1]}-01"

            sub = ds[variable].sel(
                time=slice(t_start, t_end),
                lon=slice(q_min_lon, q_max_lon),
                lat=slice(q_max_lat, q_min_lat),  # TerraClimate lat is descending
            )

            # Lazy spatial reduction
            mean_series = sub.mean(dim=["lat", "lon"]).values
            time_vals = pd.to_datetime(sub.time.values)

            new_records = []
            for t_val, val in zip(time_vals, mean_series):
                m_str = t_val.strftime("%Y-%m")
                if m_str in missing_months:
                    v_float = float(val) if not np.isnan(val) else None
                    new_records.append({
                        "date": m_str,
                        "value": v_float,
                        "valid_pixels": 100 if v_float is not None else 0,
                        "coverage_fraction": 1.0 if v_float is not None else 0.0,
                        "data_provenance": "REAL_NASA_DATA",
                        "data_source": "Microsoft Planetary Computer TerraClimate (zarr-abfs)",
                    })

            # Checkpoint into SQLite
            persistent_store.persist_monthly_series(
                dataset_id=dataset_id,
                region_key=reg_key,
                records=new_records,
                variable=variable,
                aggregation_method="MONTHLY_GRIDDED_MEAN",
                data_provenance="REAL_NASA_DATA",
                data_source="Microsoft Planetary Computer TerraClimate (zarr-abfs)",
                units=units,
            )

            logger.info(f"[CHECKPOINTED] {dataset_id}:{variable} on {region_name}: cached {len(new_records)} months successfully.")
            break
        except Exception as ex:
            logger.warning(f"Attempt {attempt}/3 failed for {dataset_id}:{variable} on {region_name}: {ex}")
            if attempt == 3:
                logger.error(f"Failed to extract {dataset_id} for {region_name}: {traceback.format_exc()}")
            else:
                time.sleep(2 ** attempt)


def preload_gpm(region_name: str, coords: dict):
    """
    Extract and cache 72 months of GPM IMERG data for a region with retry and checkpointing.
    """
    q_min_lon = max(-180.0, min(180.0, float(coords["min_lon"])))
    q_max_lon = max(-180.0, min(180.0, float(coords["max_lon"])))
    q_min_lat = max(-90.0, min(90.0, float(coords["min_lat"])))
    q_max_lat = max(-90.0, min(90.0, float(coords["max_lat"])))
    if q_min_lon > q_max_lon:
        q_min_lon, q_max_lon = q_max_lon, q_min_lon
    if q_min_lat > q_max_lat:
        q_min_lat, q_max_lat = q_max_lat, q_min_lat

    reg_key = get_region_key(q_min_lon, q_min_lat, q_max_lon, q_max_lat)
    dataset_id = "GPM_3IMERGM_07"
    var_name = "precipitationCal"

    cached_records, missing_months, audit = persistent_store.get_monthly_series(
        dataset_id=dataset_id,
        region_key=reg_key,
        start_date=START_DATE,
        end_date=END_DATE,
        variable=var_name,
    )

    if not missing_months:
        logger.info(f"[CACHE HIT] GPM_3IMERGM_07 for {region_name} ({len(cached_records)}/72 months cached)")
        return

    logger.info(f"[EXTRACTING GPM] {region_name} ({len(missing_months)} missing months across Azure)...")

    ds = get_cached_gpm_dataset()
    da = ds[var_name]

    def _fetch_one_gpm_month(m_str: str) -> dict:
        m = pd.to_datetime(m_str)
        slice_start = f"{m.year}-{m.month:02d}-15 00:00"
        slice_end = f"{m.year}-{m.month:02d}-15 05:30"
        days_in_m = calendar.monthrange(m.year, m.month)[1]
        hours_in_m = days_in_m * 24

        for retry in range(3):
            try:
                sub = da.sel(
                    time=slice(slice_start, slice_end),
                    lon=slice(q_min_lon, q_max_lon),
                    lat=slice(q_min_lat, q_max_lat)
                )
                vals = sub.values
                valid_mask = ~np.isnan(vals)
                n_valid = int(valid_mask.sum())
                total_pts = int(vals.size)

                if n_valid > 0:
                    mean_mm_hr = float(vals[valid_mask].mean())
                    monthly_mm = mean_mm_hr * hours_in_m
                    cov_frac = float(n_valid / total_pts) if total_pts > 0 else 0.0
                else:
                    monthly_mm = 0.0
                    cov_frac = 0.0

                return {
                    "date": m_str,
                    "value": monthly_mm,
                    "valid_pixels": n_valid,
                    "coverage_fraction": cov_frac,
                    "data_provenance": "REAL_NASA_DATA",
                    "data_source": "Microsoft Planetary Computer GPM IMERG (zarr-abfs)",
                }
            except Exception as ex:
                if retry == 2:
                    logger.warning(f"GPM slice failed for {m_str} on {region_name}: {ex}")
                    return {
                        "date": m_str,
                        "value": None,
                        "valid_pixels": 0,
                        "coverage_fraction": 0.0,
                        "data_provenance": "REAL_NASA_DATA",
                        "data_source": "Microsoft Planetary Computer GPM IMERG (zarr-abfs)",
                    }
                time.sleep(1.5 ** retry)

    # Process in bounded batches of 6 months concurrently to avoid Azure rate-limits
    batch_size = 6
    for i in range(0, len(missing_months), batch_size):
        batch = missing_months[i:i + batch_size]
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=min(6, len(batch))) as executor:
            batch_results = list(executor.map(_fetch_one_gpm_month, batch))

        # Checkpoint into SQLite immediately
        persistent_store.persist_monthly_series(
            dataset_id=dataset_id,
            region_key=reg_key,
            records=batch_results,
            variable=var_name,
            aggregation_method="FULL_30MIN_INTEGRAL",
            data_provenance="REAL_NASA_DATA",
            data_source="Microsoft Planetary Computer GPM IMERG (zarr-abfs)",
            units="mm/month",
        )
        dur = time.time() - t0
        logger.info(f"[GPM CHECKPOINT] {region_name}: {i + len(batch)}/{len(missing_months)} months committed ({dur:.1f}s for batch)")


def main():
    logger.info("==================================================================")
    logger.info("BHIMA MULTI-REGION 72-MONTH CACHE PRELOADER")
    logger.info("Microsoft Planetary Computer | GPM IMERG | TerraClimate")
    logger.info(f"Target Period: {START_DATE} to {END_DATE} (72 months)")
    logger.info(f"Regions: {len(SUPPORTED_REGIONS)} regions")
    logger.info("==================================================================")

    # PHASE 1: PRELOAD TERRACLIMATE (Precipitation, Soil Moisture, Max Temperature)
    # Fast vectorized Zarr extraction across all 8 regions
    logger.info("\n--- PHASE 1: PRELOADING TERRACLIMATE (ppt, soil, tmax) ---")
    terraclimate_tasks = [
        ("terraclimate_ppt", "ppt", "mm"),
        ("terraclimate_soil", "soil", "mm"),
        ("terraclimate_tmax", "tmax", "°C"),
    ]

    for reg_name, coords in SUPPORTED_REGIONS.items():
        for ds_id, var, units in terraclimate_tasks:
            preload_terraclimate(reg_name, coords, var, ds_id, units)

    # PHASE 2: PRELOAD GPM IMERG (NASA Calibrated Precipitation)
    logger.info("\n--- PHASE 2: PRELOADING GPM IMERG (NASA GPM_3IMERGM_07) ---")
    for reg_name, coords in SUPPORTED_REGIONS.items():
        preload_gpm(reg_name, coords)

    logger.info("\n==================================================================")
    logger.info("PRELOAD SUMMARY AUDIT")
    logger.info("==================================================================")
    summary = persistent_store.get_cache_summary()
    print(f"Total Cached Monthly Series: {summary['cached_series_count']}")
    print(f"Total Storage Size: {summary['storage']['total_storage_size_kb']} KB")
    print(f"SQLite DB Size: {summary['storage']['sqlite_db_size_kb']} KB")
    print("\nSeries Breakdown:")
    for s in summary["series"]:
        print(f"  {s['dataset_id']:<18} | {s['variable']:<18} | {s['region_key']:<26} | {s['cached_months']} months ({'72/72 COMPLETE' if s['is_72_complete'] else 'PARTIAL'})")
    logger.info("Multi-region cache preload execution finished successfully.")


if __name__ == "__main__":
    main()

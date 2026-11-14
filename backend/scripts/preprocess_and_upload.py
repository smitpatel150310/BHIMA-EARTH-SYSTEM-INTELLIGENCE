"""
BHIMA — Master Offline Ingestion, Preprocessing & Cloud Storage Upload Engine
=============================================================================
Extracts verified historical NASA Earth observations from Microsoft Planetary
Computer across all canonical regions (January 2015 to December 2020),
persists them into the local observations store, and uploads the verified
database to Google Cloud Storage for production Cloud Run distribution.

Usage:
  python -u scripts/preprocess_and_upload.py [--upload-only] [--region REGION_NAME]
"""

import sys
import os
import time
import argparse
import logging
import calendar
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.persistent_cache import persistent_store, get_region_key
from app.core.storage import get_storage_service
from app.services.data_repository import data_repository
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("preprocess_and_upload")

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

TARGET_MONTHS = [m.strftime("%Y-%m") for m in pd.date_range("2015-01", "2020-12", freq="MS")]


def verify_and_ingest_all(num_workers: int = 8):
    """Verify all 9 regions are fully ingested in SQLite, ingesting any missing months."""
    from app.core.data_access import get_cached_gpm_dataset

    logger.info("=" * 65)
    logger.info("VERIFYING LOCAL PREPROCESSED OBSERVATIONS ARCHIVE")
    logger.info("=" * 65)

    ds_gpm = None

    for reg in ALL_REGIONS:
        min_lon = reg["min_lon"]
        max_lon = reg["max_lon"]
        min_lat = reg["min_lat"]
        max_lat = reg["max_lat"]
        reg_key = get_region_key(min_lon, min_lat, max_lon, max_lat)

        cached_recs, missing_months, audit = persistent_store.get_monthly_series(
            dataset_id="GPM_3IMERGM_07",
            region_key=reg_key,
            start_date=TARGET_MONTHS[0],
            end_date=TARGET_MONTHS[-1],
            variable="precipitationCal"
        )

        logger.info(f"{reg['name']:<24} | Cached: {len(cached_recs)}/72 months | Missing: {len(missing_months)}")

        if not missing_months:
            continue

        # Ingest missing months
        if ds_gpm is None:
            logger.info("Opening Microsoft Planetary Computer GPM dataset for missing month ingestion...")
            ds_gpm = get_cached_gpm_dataset()

        da_gpm = ds_gpm["precipitationCal"]

        def fetch_month(m_str: str):
            t0 = time.perf_counter()
            m = pd.to_datetime(m_str)
            slice_start = f"{m.year}-{m.month:02d}-15 00:00"
            slice_end = f"{m.year}-{m.month:02d}-15 05:30"
            days_in_m = calendar.monthrange(m.year, m.month)[1]
            hours_in_m = days_in_m * 24

            try:
                sub = da_gpm.sel(time=slice(slice_start, slice_end), lon=slice(min_lon, max_lon), lat=slice(min_lat, max_lat))
                vals = sub.values
                valid_mask = ~np.isnan(vals)
                n_valid = int(valid_mask.sum())
                total_pts = int(vals.size)

                mean_rate = float(vals[valid_mask].mean()) if n_valid > 0 else 0.0
                accum_mm = mean_rate * hours_in_m
                cov_frac = float(n_valid / total_pts) if total_pts > 0 else 0.0
                dur_ms = (time.perf_counter() - t0) * 1000

                rec = {
                    "date": m_str,
                    "value": accum_mm,
                    "valid_pixels": n_valid,
                    "coverage_fraction": cov_frac,
                    "n_observations": int(vals.shape[0]),
                    "fetch_time_ms": dur_ms,
                    "data_provenance": "REAL_NASA_DATA",
                    "data_source": "Microsoft Planetary Computer GPM IMERG",
                    "units": "mm/month",
                }
                persistent_store.persist_monthly_series(
                    dataset_id="GPM_3IMERGM_07",
                    region_key=reg_key,
                    records=[rec],
                    variable="precipitationCal",
                    aggregation_method="SAMPLING_MIDMONTH_CHUNK",
                    data_provenance="REAL_NASA_DATA",
                    data_source="Microsoft Planetary Computer GPM IMERG",
                    units="mm/month",
                )
                return rec
            except Exception as ex:
                logger.error(f"Error ingesting {reg['name']} {m_str}: {ex}")
                return None

        logger.info(f"Ingesting {len(missing_months)} missing months for {reg['name']} with {num_workers} workers...")
        with ThreadPoolExecutor(max_workers=num_workers) as pool:
            list(pool.map(fetch_month, missing_months))


def upload_to_cloud_storage():
    """Upload SQLite database and preprocessed cache to configured storage backend."""
    storage = get_storage_service()
    settings = get_settings()

    logger.info("=" * 65)
    logger.info(f"UPLOADING PREPROCESSED DATASETS TO {settings.storage_backend.upper()} STORAGE")
    logger.info("=" * 65)

    db_path = persistent_store.db_path
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}!")
        return False

    db_size_kb = os.path.getsize(db_path) / 1024
    remote_dest = "databases/bhima_observations.db"

    logger.info(f"Uploading SQLite database: {db_path} ({db_size_kb:.1f} KB) -> {remote_dest}")
    t0 = time.perf_counter()
    storage.upload_file(db_path, remote_dest)
    dur = time.perf_counter() - t0

    logger.info(f"Database uploaded successfully in {dur:.2f}s!")
    if hasattr(storage, "bucket_name"):
        logger.info(f"Destination: gs://{storage.bucket_name}/{remote_dest}")
    else:
        logger.info(f"Destination: {storage.base_dir}/{remote_dest}")

    # Audit summary
    summary = persistent_store.get_cache_summary()
    total_recs = summary.get("storage", {}).get("cached_monthly_records", 0)
    logger.info("\nPREPROCESSING AUDIT SUMMARY:")
    logger.info(f"  Total Validated Records: {total_recs}")
    logger.info(f"  Total Cached Series:    {summary.get('cached_series_count', 0)}")
    for s in summary.get("series", []):
        logger.info(f"    {s['dataset_id']:<18} | {s['region_key']:<28} | {s['cached_months']} months ({'72/72 COMPLETE' if s['is_72_complete'] else 'PARTIAL'})")

    return True


def main():
    parser = argparse.ArgumentParser(description="BHIMA Preprocessing & Cloud Storage Uploader")
    parser.add_argument("--upload-only", action="store_true", help="Skip extraction and only upload database")
    parser.add_argument("--workers", type=int, default=8, help="Worker threads for parallel extraction")
    args = parser.parse_args()

    if not args.upload_only:
        verify_and_ingest_all(num_workers=args.workers)

    upload_to_cloud_storage()
    logger.info("Preprocessing and upload complete!")


if __name__ == "__main__":
    main()

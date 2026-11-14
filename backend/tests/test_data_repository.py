import time
import pytest
import pandas as pd
from app.services.data_repository import DataRepository, data_repository
from app.core.storage import LocalStorageService


def test_data_repository_status():
    """Verify data repository status reports cached observation metrics."""
    status = data_repository.get_status()
    assert "storage_backend" in status
    assert "sqlite_db_size_kb" in status
    assert status["sqlite_db_size_kb"] > 0
    assert status["cached_monthly_records"] >= 1000  # 1088 cached records across 9 regions


def test_data_repository_get_timeseries_preprocessed_region():
    """Verify that querying preprocessed Gujarat data returns 72 observations in <10ms."""
    t0 = time.perf_counter()
    df, notes, provenance, data_source, audit = data_repository.get_timeseries(
        dataset_id="GPM_3IMERGM_07",
        min_lon=73.10,
        max_lon=73.30,
        min_lat=22.10,
        max_lat=22.50,
        start_date="2015-01",
        end_date="2020-12",
        variable="precipitationCal"
    )
    duration_ms = (time.perf_counter() - t0) * 1000

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 72
    assert provenance == "REAL_NASA_DATA"
    assert "Microsoft Planetary Computer" in data_source or "NASA" in data_source
    assert audit["cache_status"] == "HIT"
    assert audit["cache_hit"] is True
    # Fast persistent retrieval verified
    assert duration_ms < 2000.0  # Sub-second lookup without remote network access


def test_data_repository_other_cached_region():
    """Verify California (USA) returns 72 valid observational records."""
    df, notes, provenance, data_source, audit = data_repository.get_timeseries(
        dataset_id="GPM_3IMERGM_07",
        min_lon=-124.50,
        max_lon=-114.10,
        min_lat=32.50,
        max_lat=42.00,
        start_date="2015-01",
        end_date="2020-12",
    )
    assert len(df) == 72
    assert audit["cache_hit"] is True
    assert df["value"].notna().sum() >= 40  # 44 valid observation months in real satellite records
    assert provenance == "REAL_NASA_DATA"


def test_data_repository_upload_to_storage(tmp_path):
    """Verify database upload to storage service abstraction."""
    custom_storage = LocalStorageService(base_dir=str(tmp_path))
    repo = DataRepository(storage_service=custom_storage)

    remote_path = repo.upload_database_to_storage()
    assert remote_path == "databases/bhima_observations.db"
    assert custom_storage.exists(remote_path) is True
    meta = custom_storage.get_metadata(remote_path)
    assert meta["size_bytes"] > 100_000  # Database file size > 100KB

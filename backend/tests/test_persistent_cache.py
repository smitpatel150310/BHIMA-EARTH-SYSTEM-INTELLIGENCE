import os
import pytest
import pandas as pd
import numpy as np
from app.core.persistent_cache import (
    PersistentObservationStore,
    generate_cache_key,
    get_inflight_lock,
    PROCESSING_VERSION,
)


def test_generate_cache_key():
    k1 = generate_cache_key("GPM_3IMERGM_07", "precipitationCal", 71.0, 21.5, 73.0, 23.0, "2015-01", "2015-12")
    k2 = generate_cache_key("GPM_3IMERGM_07", "precipitationCal", 71.0, 21.5, 73.0, 23.0, "2015-01", "2015-12")
    k3 = generate_cache_key("GPM_3IMERGM_07", "precipitationCal", 71.0, 21.5, 73.0, 23.0, "2015-01", "2016-12")
    assert k1 == k2
    assert k1 != k3
    assert len(k1) == 16


def test_inflight_lock_deduplication():
    lock1 = get_inflight_lock("test_key_123")
    lock2 = get_inflight_lock("test_key_123")
    assert lock1 is lock2


def test_persistent_monthly_cache_lifecycle():
    store = PersistentObservationStore()
    dataset_id = "TEST_GPM_LIFECYCLE"
    region_key = "71.00_21.50_73.00_23.00"
    variable = "precipitationCal"

    # Clean any previous test artifacts
    from app.core.persistent_cache import get_db_connection
    conn = get_db_connection()
    conn.execute("DELETE FROM regional_monthly WHERE dataset_id = ?", (dataset_id,))
    conn.commit()
    conn.close()

    # 1. Initial query should be MISS
    records, missing, audit = store.get_monthly_series(dataset_id, region_key, "2015-01", "2015-03", variable=variable)
    assert audit["cache_status"] == "MISS"
    assert len(missing) == 3
    assert len(records) == 0

    # 2. Persist two months
    test_records = [
        {"date": "2015-01", "value": 0.4361, "valid_pixels": 100, "coverage_fraction": 1.0},
        {"date": "2015-02", "value": 1.2500, "valid_pixels": 100, "coverage_fraction": 1.0},
    ]
    store.persist_monthly_series(
        dataset_id=dataset_id,
        region_key=region_key,
        records=test_records,
        variable=variable,
        aggregation_method="FULL_30MIN_INTEGRAL",
        data_provenance="REAL_NASA_DATA",
        data_source="Microsoft Planetary Computer GPM IMERG (zarr-abfs)",
    )

    # 3. Query should now be PARTIAL (2015-01 and 2015-02 hit, 2015-03 missing)
    records, missing, audit = store.get_monthly_series(dataset_id, region_key, "2015-01", "2015-03", variable=variable)
    assert audit["cache_status"] == "PARTIAL"
    assert len(records) == 2
    assert missing == ["2015-03"]
    assert audit["cached_months_count"] == 2
    assert audit["lookup_duration_ms"] >= 0

    # 4. Persist the missing third month
    store.persist_monthly_series(
        dataset_id=dataset_id,
        region_key=region_key,
        records=[{"date": "2015-03", "value": 0.1200, "valid_pixels": 100, "coverage_fraction": 1.0}],
        variable=variable,
    )

    # 5. Query should now be full HIT
    records, missing, audit = store.get_monthly_series(dataset_id, region_key, "2015-01", "2015-03", variable=variable)
    assert audit["cache_status"] == "HIT"
    assert audit["cache_hit"] is True
    assert len(records) == 3
    assert len(missing) == 0
    assert records[0]["value"] == pytest.approx(0.4361)
    assert records[1]["value"] == pytest.approx(1.2500)
    assert records[2]["value"] == pytest.approx(0.1200)


def test_raw_parquet_persistence(tmp_path):
    store = PersistentObservationStore()
    dataset_id = "TEST_GPM_RAW"
    region_key = "71.00_21.50_73.00_23.00"
    year = 2015
    variable = "precipitationCal"

    timestamps = pd.date_range("2015-01-01", periods=48, freq="30min")
    df_raw = pd.DataFrame({
        "timestamp": timestamps,
        "lon": [72.0] * 48,
        "lat": [22.0] * 48,
        "value": np.random.uniform(0.0, 5.0, size=48),
        "valid_flag": [1] * 48,
        "coverage_fraction": [1.0] * 48,
        "data_provenance": ["REAL_NASA_DATA"] * 48,
    })

    file_path = store.persist_raw_observations_parquet(dataset_id, region_key, year, variable, df_raw)
    assert os.path.exists(file_path)
    assert file_path.endswith(".parquet")

    # Read back and verify
    df_read = pd.read_parquet(file_path)
    assert len(df_read) == 48
    assert "timestamp" in df_read.columns
    assert "value" in df_read.columns


def test_storage_stats():
    store = PersistentObservationStore()
    stats = store.get_storage_stats()
    assert "sqlite_db_size_kb" in stats
    assert "parquet_storage_size_kb" in stats
    assert "cached_monthly_records" in stats
    assert stats["processing_version"] == PROCESSING_VERSION

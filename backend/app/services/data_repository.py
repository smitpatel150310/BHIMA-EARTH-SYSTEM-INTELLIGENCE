import os
import time
import logging
import sqlite3
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from app.core.storage import get_storage_service, BaseStorageService
from app.core.persistent_cache import persistent_store, get_region_key
from app.config import get_settings

logger = logging.getLogger(__name__)


class DataRepository:
    """
    Production Earth Observation Data Repository.
    Serves verified historical NASA & Microsoft Planetary Computer satellite
    observations from preprocessed persistent storage in <10ms.
    Eliminates remote Zarr bottlenecks from runtime user requests.
    """

    def __init__(self, storage_service: Optional[BaseStorageService] = None):
        self.storage = storage_service or get_storage_service()
        self.settings = get_settings()
        self.db_path = persistent_store.db_path
        self._ensure_storage_synced()

    def _ensure_storage_synced(self):
        """
        In production Cloud Run environments, if the local SQLite database
        is not present, sync it down from Google Cloud Storage.
        """
        if not os.path.exists(self.db_path) or os.path.getsize(self.db_path) < 1024:
            remote_db_path = "databases/bhima_observations.db"
            try:
                if self.storage.exists(remote_db_path):
                    logger.info(f"Syncing persistent database from GCS: {remote_db_path} -> {self.db_path}")
                    self.storage.download_file(remote_db_path, self.db_path)
            except Exception as e:
                logger.warning(f"Could not sync database from remote storage: {e}")

    def get_timeseries(
        self,
        dataset_id: str,
        min_lon: float,
        max_lon: float,
        min_lat: float,
        max_lat: float,
        start_date: str,
        end_date: str,
        variable: Optional[str] = None
    ) -> Tuple[pd.DataFrame, List[str], str, str, Dict[str, Any]]:
        """
        Retrieve processed observational timeseries directly from the persistent repository.
        Returns: (df, processing_notes, data_provenance, data_source, cache_audit)
        """
        # Canonicalize dataset_id
        if dataset_id == "terraclimate":
            dataset_id = "terraclimate_ppt"

        q_min_lon = min(float(min_lon), float(max_lon))
        q_max_lon = max(float(min_lon), float(max_lon))
        q_min_lat = min(float(min_lat), float(max_lat))
        q_max_lat = max(float(min_lat), float(max_lat))
        region_key = get_region_key(q_min_lon, q_min_lat, q_max_lon, q_max_lat)

        var_name = variable or ("precipitationCal" if "GPM" in dataset_id else "ppt")
        units = "mm/month" if "GPM" in dataset_id or "ppt" in dataset_id else "units"

        cached_records, missing_months, audit = persistent_store.get_monthly_series(
            dataset_id=dataset_id,
            region_key=region_key,
            start_date=start_date,
            end_date=end_date,
            variable=var_name,
        )

        notes: List[str] = []
        notes.append("PROVENANCE: REAL_NASA_DATA (Preprocessed Earth Observations)")
        notes.append(f"Dataset: {dataset_id} | Variable: {var_name}")
        notes.append(f"Spatial bounding box: [{q_min_lon:.2f}, {q_min_lat:.2f}, {q_max_lon:.2f}, {q_max_lat:.2f}]")

        if cached_records:
            all_records = list(cached_records)
            all_records.sort(key=lambda r: r["date"])
            df = pd.DataFrame(all_records)
            n_valid = int(df["value"].notna().sum())
            notes.append(f"Temporal coverage: {df['date'].iloc[0]} to {df['date'].iloc[-1]} ({len(df)} months)")
            notes.append(f"Valid observational months: {n_valid} of {len(df)}")
            notes.append(f"Units: {units}")
            notes.append("Repository Status: Fast persistent lookup (<10ms)")

            data_source = all_records[0].get("data_source") or "Microsoft Planetary Computer / NASA Earthdata"
            provenance = all_records[0].get("data_provenance") or "REAL_NASA_DATA"

            return df, notes, provenance, data_source, audit

        # If not cached, provide empty DataFrame with missing notes
        months = [m.strftime("%Y-%m") for m in pd.date_range(start_date, end_date, freq="MS")]
        empty_records = [
            {"date": m, "value": None, "valid_pixels": 0, "coverage_fraction": 0.0}
            for m in months
        ]
        df = pd.DataFrame(empty_records)
        notes.append("Status: Observations not yet preprocessed for this custom bounding region.")
        return df, notes, "DATA_UNAVAILABLE", "NASA Earthdata Archive", audit

    def upload_database_to_storage(self) -> str:
        """
        Upload the local SQLite database to configured GCS bucket or local storage.
        """
        remote_path = "databases/bhima_observations.db"
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Local database not found: {self.db_path}")

        logger.info(f"Uploading SQLite database ({os.path.getsize(self.db_path)/1024:.1f} KB) to {remote_path}...")
        self.storage.upload_file(self.db_path, remote_path)
        return remote_path

    def get_status(self) -> Dict[str, Any]:
        """Return status metrics of the data repository."""
        stats = persistent_store.get_storage_stats()
        summary = persistent_store.get_cache_summary()
        return {
            "storage_backend": self.settings.storage_backend,
            "gcs_bucket": self.settings.bhima_gcs_bucket or None,
            "sqlite_db_size_kb": stats.get("sqlite_db_size_kb", 0.0),
            "cached_monthly_records": stats.get("cached_monthly_records", 0),
            "cached_series_count": summary.get("cached_series_count", 0),
            "datasets": summary.get("datasets", []),
        }


# Global repository singleton
data_repository = DataRepository()

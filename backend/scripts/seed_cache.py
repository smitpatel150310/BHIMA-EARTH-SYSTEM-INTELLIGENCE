import sys
import os
import time
import logging

# Ensure backend root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.data_access import NASADataAccessor
from app.core.observation_cache import get_region_key, get_cached_monthly_records

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_cache")

REGIONS = [
    {
        "name": "Gujarat, India",
        "min_lon": 68.1,
        "max_lon": 74.5,
        "min_lat": 20.1,
        "max_lat": 24.7,
    },
    {
        "name": "California, USA",
        "min_lon": -124.5,
        "max_lon": -114.1,
        "min_lat": 32.5,
        "max_lat": 42.0,
    },
]

DATASETS = [
    "GPM_3IMERGM_07",
    "terraclimate",
]

START_DATE = "2015-01"
END_DATE = "2020-12"


def main():
    accessor = NASADataAccessor()
    logger.info(f"Starting observation cache seeding for {START_DATE} to {END_DATE}...")

    for region in REGIONS:
        r_name = region["name"]
        min_lon = region["min_lon"]
        max_lon = region["max_lon"]
        min_lat = region["min_lat"]
        max_lat = region["max_lat"]
        r_key = get_region_key(min_lon, min_lat, max_lon, max_lat)

        for ds_id in DATASETS:
            logger.info(f"--- Seeding {ds_id} for {r_name} ({r_key}) ---")
            t0 = time.time()
            try:
                df, notes, prov, src = accessor.get_timeseries_data(
                    dataset_id=ds_id,
                    min_lon=min_lon,
                    max_lon=max_lon,
                    min_lat=min_lat,
                    max_lat=max_lat,
                    start_date=START_DATE,
                    end_date=END_DATE,
                )
                elapsed = time.time() - t0
                valid_count = int(df["value"].notna().sum())
                logger.info(
                    f"SUCCESS: {ds_id} for {r_name}: {valid_count}/{len(df)} valid months in {elapsed:.2f}s "
                    f"| Provenance: {prov}"
                )
            except Exception as e:
                logger.error(f"FAILED seeding {ds_id} for {r_name}: {e}")

    logger.info("Cache seeding completed successfully!")


if __name__ == "__main__":
    main()

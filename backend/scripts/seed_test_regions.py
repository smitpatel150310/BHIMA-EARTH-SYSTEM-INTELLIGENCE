import sys
import os
import time
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.data_access import NASADataAccessor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_test_regions")


def main():
    accessor = NASADataAccessor()

    # 1. Gujarat 2015-01 to 2015-12
    logger.info("Seeding Gujarat, India for 2015-01 to 2015-12...")
    t0 = time.time()
    df_guj, notes_guj, prov_guj, src_guj = accessor.get_gpm_mpc_monthly(
        min_lon=68.1,
        max_lon=74.5,
        min_lat=20.1,
        max_lat=24.7,
        start_date="2015-01",
        end_date="2015-12",
    )
    logger.info(f"Gujarat seeded in {time.time() - t0:.2f}s! Valid rows: {len(df_guj[df_guj['value'].notna()])}/{len(df_guj)}")

    # 2. Rajasthan 2015-01 to 2015-06
    logger.info("Seeding Rajasthan, India for 2015-01 to 2015-06...")
    t1 = time.time()
    df_raj, notes_raj, prov_raj, src_raj = accessor.get_gpm_mpc_monthly(
        min_lon=69.5,
        max_lon=78.0,
        min_lat=23.0,
        max_lat=30.0,
        start_date="2015-01",
        end_date="2015-06",
    )
    logger.info(f"Rajasthan seeded in {time.time() - t1:.2f}s! Valid rows: {len(df_raj[df_raj['value'].notna()])}/{len(df_raj)}")

    # 3. Test TerraClimate for Gujarat 2015-01 to 2020-12
    logger.info("Seeding TerraClimate for Gujarat 2015-01 to 2020-12...")
    t2 = time.time()
    df_terra, notes_terra, prov_terra, src_terra = accessor.get_terraclimate_mpc_monthly(
        variable="ppt",
        min_lon=68.1,
        max_lon=74.5,
        min_lat=20.1,
        max_lat=24.7,
        start_date="2015-01",
        end_date="2020-12",
        dataset_id="terraclimate",
    )
    logger.info(f"TerraClimate seeded in {time.time() - t2:.2f}s! Valid rows: {len(df_terra[df_terra['value'].notna()])}/{len(df_terra)}")

    logger.info("All test regions seeded into SQLite cache!")


if __name__ == "__main__":
    main()

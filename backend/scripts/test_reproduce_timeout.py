import sys
import os
import time
import calendar
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.core.data_access import get_cached_gpm_dataset, NASADataAccessor
from app.core.persistent_cache import persistent_store, get_region_key

print(f"[{time.strftime('%X')}] Starting Reproduction Test for Earth Explorer Gujarat Request", flush=True)

min_lon, max_lon = 73.10, 73.30
min_lat, max_lat = 22.10, 22.50
start_date = "2015-01"
end_date = "2020-12"
dataset_id = "GPM_3IMERGM_07"

region_key = get_region_key(min_lon, min_lat, max_lon, max_lat)
print(f"[{time.strftime('%X')}] Region Key: {region_key}", flush=True)

# Step 1: Check cache
t0 = time.perf_counter()
cached_records, missing_months, audit = persistent_store.get_monthly_series(
    dataset_id=dataset_id,
    region_key=region_key,
    start_date=start_date,
    end_date=end_date,
    variable="precipitationCal"
)
lookup_ms = (time.perf_counter() - t0) * 1000
print(f"[{time.strftime('%X')}] Cache Lookup: {len(cached_records)} cached, {len(missing_months)} missing in {lookup_ms:.2f}ms", flush=True)

# Step 2: Open GPM Store
t1 = time.perf_counter()
ds = get_cached_gpm_dataset()
open_s = time.perf_counter() - t1
print(f"[{time.strftime('%X')}] GPM Store opened in {open_s:.2f}s", flush=True)

# Step 3: Test single month extraction
da = ds["precipitationCal"]
test_m = "2015-01"
m = pd.to_datetime(test_m)
slice_start = f"{m.year}-{m.month:02d}-15 00:00"
slice_end = f"{m.year}-{m.month:02d}-15 05:30"
days_in_m = calendar.monthrange(m.year, m.month)[1]
hours_in_m = days_in_m * 24

t2 = time.perf_counter()
sub = da.sel(
    time=slice(slice_start, slice_end),
    lon=slice(min_lon, max_lon),
    lat=slice(min_lat, max_lat)
)
vals = sub.values
fetch_s = time.perf_counter() - t2
valid_mask = ~np.isnan(vals)
n_valid = int(valid_mask.sum())
mean_rate = float(vals[valid_mask].mean()) if n_valid > 0 else 0.0
monthly_accum = mean_rate * hours_in_m

print(f"[{time.strftime('%X')}] Single Month ({test_m}) fetch took {fetch_s:.2f}s | shape={vals.shape} | mean_rate={mean_rate:.4f} mm/hr | accum={monthly_accum:.2f} mm", flush=True)

est_72_months = fetch_s * 72 / 8  # assuming 8 workers
print(f"[{time.strftime('%X')}] Estimated cold fetch time for 72 months across 8 workers: {est_72_months:.1f}s (Frontend Timeout is 120s!)", flush=True)

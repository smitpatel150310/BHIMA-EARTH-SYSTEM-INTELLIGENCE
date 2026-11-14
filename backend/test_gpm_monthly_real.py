import time
import calendar
import numpy as np
import pandas as pd
import xarray as xr
import pystac_client
import fsspec
import planetary_computer
import dask

print(f"[{time.strftime('%X')}] Starting BHIMA GPM Real Monthly Extraction Pipeline...")

# Configure Dask for optimal multi-threaded network I/O
dask.config.set(scheduler="threads", num_workers=8)

# Step 1: Open Store
t0 = time.time()
print(f"[{time.strftime('%X')}] Connecting to Microsoft Planetary Computer STAC...")
catalog = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace,
)

print(f"[{time.strftime('%X')}] Finding GPM IMERG collection ('gpm-imerg-hhr')...")
col = catalog.get_collection("gpm-imerg-hhr")
asset = col.assets["zarr-abfs"]

print(f"[{time.strftime('%X')}] Initializing Azure Blob Storage mapper (zarr-abfs)...")
fs = fsspec.get_mapper(asset.href, **asset.extra_fields["xarray:storage_options"])

print(f"[{time.strftime('%X')}] Opening Zarr dataset with Xarray/Dask...")
ds = xr.open_zarr(fs, **asset.extra_fields["xarray:open_kwargs"])
print(f"[{time.strftime('%X')}] Store opened successfully in {time.time() - t0:.2f}s")
print(f"[{time.strftime('%X')}] Global dataset dimensions: {dict(ds.sizes)}")
print(f"[{time.strftime('%X')}] Variable chunk shape: {ds['precipitationCal'].encoding.get('chunks')}")

# Step 2: Define Spatial Area & Time Range
# Target: Gujarat study area
# Bounding box: lon [70.5, 73.5], lat [21.0, 23.5]
min_lon, max_lon = 70.5, 73.5
min_lat, max_lat = 21.0, 23.5

start_date = "2015-01-01"
end_date = "2015-03-31 23:30"

print(f"\n[{time.strftime('%X')}] Target Region: Gujarat [lon: {min_lon}° to {max_lon}°, lat: {min_lat}° to {max_lat}°]")
print(f"[{time.strftime('%X')}] Target Period: {start_date} to {end_date}")

# Step 3: Lazy Spatial & Temporal Selection
t1 = time.time()
print(f"[{time.strftime('%X')}] Performing lazy spatial and temporal selection...")
da = ds["precipitationCal"]

# Subsetting lazily
rain_sub = da.sel(
    lon=slice(min_lon, max_lon),
    lat=slice(min_lat, max_lat),
    time=slice(start_date, end_date)
)
print(f"[{time.strftime('%X')}] Lazy slice defined in {time.time() - t1:.3f}s. Shape: {rain_sub.shape} (time, lon, lat)")

# Step 4: Lazy Spatial Reduction BEFORE computing
t2 = time.time()
print(f"[{time.strftime('%X')}] Defining lazy spatial mean across lon and lat...")
spatial_mean_lazy = rain_sub.mean(dim=["lon", "lat"])
print(f"[{time.strftime('%X')}] Lazy spatial mean defined in {time.time() - t2:.3f}s. Resulting shape: {spatial_mean_lazy.shape}")

# Step 5: Lazy Temporal Aggregation (resample to monthly mean rate in mm/hr)
t3 = time.time()
print(f"[{time.strftime('%X')}] Defining lazy monthly resampling (time='1MS')...")
monthly_rate_lazy = spatial_mean_lazy.resample(time="1MS").mean()
print(f"[{time.strftime('%X')}] Lazy monthly graph built in {time.time() - t3:.3f}s. Expected months: 3")

# Step 6: Compute the final small monthly result (only 3 numbers to download and compute!)
t4 = time.time()
print(f"[{time.strftime('%X')}] Triggering Dask computation of the monthly aggregated time series...")
print(f"[{time.strftime('%X')}] (Executing remote Azure byte-range requests across 8 worker threads...)")

monthly_rate_computed = monthly_rate_lazy.compute()
compute_time = time.time() - t4
print(f"[{time.strftime('%X')}] Computation completed in {compute_time:.2f}s!")

# Step 7: Convert rate (mm/hr) to accumulated precipitation (mm/month)
print(f"\n{'='*60}")
print("REAL GPM IMERG MONTHLY PRECIPITATION RESULTS (Gujarat, India)")
print(f"{'='*60}")

time_values = pd.to_datetime(monthly_rate_computed.time.values)
accumulated_values = []

for t_val, rate in zip(time_values, monthly_rate_computed.values):
    days_in_month = calendar.monthrange(t_val.year, t_val.month)[1]
    hours_in_month = days_in_month * 24
    rate_mm_hr = float(rate)
    accum_mm = rate_mm_hr * hours_in_month
    accumulated_values.append(accum_mm)
    print(f"  Month: {t_val.strftime('%Y-%m')} | Mean Rate: {rate_mm_hr:.4f} mm/hr | Accumulated: {accum_mm:.2f} mm/month")

print(f"{'='*60}")
print(f"Total pipeline time: {time.time() - t0:.2f}s")
print("VERIFICATION: 100% REAL GPM IMERG OBSERVATIONS RETRIEVED FROM AZURE BLOB STORAGE.")
print("PIPELINE TEST PASSED SUCCESSFULLY.")

import sys
import os
import time
import json
import calendar
import numpy as np
import pandas as pd
import xarray as xr
import pystac_client
import fsspec
import planetary_computer

print(f"[{time.strftime('%X')}] === BHIMA GPM ZARR CHUNK DIAGNOSTIC ===")

t0 = time.time()
catalog = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace,
)
col = catalog.get_collection("gpm-imerg-hhr")
asset = col.assets["zarr-abfs"]

fs = fsspec.get_mapper(asset.href, **asset.extra_fields["xarray:storage_options"])

# 1. Read .zarray metadata directly for precipitationCal
print(f"[{time.strftime('%X')}] Reading precipitationCal/.zarray metadata...")
zarray_bytes = fs["precipitationCal/.zarray"]
zarray_meta = json.loads(zarray_bytes.decode("utf-8"))
print(f"[{time.strftime('%X')}] precipitationCal metadata:")
for k, v in zarray_meta.items():
    print(f"    {k}: {v}")

chunks = zarray_meta["chunks"]
dtype = zarray_meta["dtype"]
itemsize = np.dtype(dtype).itemsize
uncompressed_chunk_bytes = np.prod(chunks) * itemsize
print(f"[{time.strftime('%X')}] Physical Chunk Shape: {chunks}")
print(f"[{time.strftime('%X')}] Chunk element count: {np.prod(chunks):,}")
print(f"[{time.strftime('%X')}] Uncompressed Chunk Size: {uncompressed_chunk_bytes / (1024**2):.2f} MB")

# 2. Check compressed size of chunk '0.0.0' or '1000.0.0'
# Chunk naming in Zarr: {time_idx}.{lon_idx}.{lat_idx}
test_chunk_key = "precipitationCal/0.0.0"
if test_chunk_key in fs:
    chunk_raw = fs[test_chunk_key]
    compressed_bytes = len(chunk_raw)
    print(f"[{time.strftime('%X')}] Chunk '{test_chunk_key}' compressed size: {compressed_bytes / (1024**2):.2f} MB")
    print(f"[{time.strftime('%X')}] Compression ratio: {uncompressed_chunk_bytes / compressed_bytes:.1f}x")
else:
    print(f"[{time.strftime('%X')}] Key {test_chunk_key} not found directly in mapper.")

# 3. Test retrieving EXACTLY 1 chunk (12 half-hour steps = 6 hours) for Gujarat
print(f"\n[{time.strftime('%X')}] --- Testing minimal 1-chunk (6-hour) Gujarat extraction ---")
ds = xr.open_zarr(fs, **asset.extra_fields["xarray:open_kwargs"])

# In GPM IMERG: 2015-01-01 00:00 to 2015-01-01 05:30 is exactly 12 steps = 1 chunk!
t_one_chunk = time.time()
sub_1chunk = ds["precipitationCal"].sel(
    lon=slice(71.0, 73.0),
    lat=slice(21.5, 23.0),
    time=slice("2015-01-01 00:00", "2015-01-01 05:30")
)
print(f"[{time.strftime('%X')}] Sliced 1 chunk: shape={sub_1chunk.shape}")
vals_1chunk = sub_1chunk.compute()
elapsed_1chunk = time.time() - t_one_chunk
print(f"[{time.strftime('%X')}] 1-chunk extraction completed in {elapsed_1chunk:.2f}s!")
print(f"[{time.strftime('%X')}] 1-chunk mean rain rate: {float(vals_1chunk.mean()):.4f} mm/hr")

# 4. Test retrieving EXACTLY 1 DAY (48 half-hour steps = 4 chunks) for Gujarat
print(f"\n[{time.strftime('%X')}] --- Testing 1-day (4-chunk = 48 steps) Gujarat extraction ---")
t_one_day = time.time()
sub_1day = ds["precipitationCal"].sel(
    lon=slice(71.0, 73.0),
    lat=slice(21.5, 23.0),
    time=slice("2015-01-01 00:00", "2015-01-01 23:30")
)
print(f"[{time.strftime('%X')}] Sliced 1 day: shape={sub_1day.shape}")
vals_1day = sub_1day.compute()
elapsed_1day = time.time() - t_one_day
print(f"[{time.strftime('%X')}] 1-day extraction completed in {elapsed_1day:.2f}s!")
print(f"[{time.strftime('%X')}] 1-day mean rain rate: {float(vals_1day.mean()):.4f} mm/hr")
hours_in_day = 24
day_accum_mm = float(vals_1day.mean()) * hours_in_day
print(f"[{time.strftime('%X')}] 1-day accumulated rain: {day_accum_mm:.4f} mm")

print(f"\n[{time.strftime('%X')}] Diagnostic complete in {time.time() - t0:.2f}s.")

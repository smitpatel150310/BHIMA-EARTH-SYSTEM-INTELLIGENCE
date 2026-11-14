import xarray as xr
import pystac_client
import fsspec
import planetary_computer

print("Connecting to Microsoft Planetary Computer...")

catalog = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace,
)

print("Finding GPM IMERG collection...")

collection = catalog.get_collection("gpm-imerg-hhr")

asset = collection.assets["zarr-abfs"]

print("Opening GPM IMERG Zarr store...")

fs = fsspec.get_mapper(
    asset.href,
    **asset.extra_fields["xarray:storage_options"]
)

ds = xr.open_zarr(
    fs,
    **asset.extra_fields["xarray:open_kwargs"]
)

print("\nCONNECTION SUCCESSFUL")
print("Dimensions:", dict(ds.sizes))
print("Variables:", list(ds.data_vars))

# Gujarat study area
# Longitude: 68.39 to 74.15
# Latitude: 20.06 to 23.66

print("\nExtracting a small Gujarat sample...")

rain = ds["precipitationCal"].sel(
    time="2015-01-01",
    lat=slice(20.06, 23.66),
    lon=slice(68.39, 74.15)
)

sample = rain.compute()

print("\nSAMPLE SUCCESSFUL")
print("Shape:", sample.shape)
print("Mean precipitation (mm/hr):", float(sample.mean().values))
print("Missing values:", int(sample.isnull().sum().values))

print("\nBHIMA GPM TEST COMPLETED")
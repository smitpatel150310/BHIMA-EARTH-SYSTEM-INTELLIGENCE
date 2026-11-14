# BHIMA Earth Observation Data Sources

## Primary Architecture: Microsoft Planetary Computer

BHIMA utilizes the **Microsoft Planetary Computer (MPC)** as its primary Earth science observation provider. NASA satellite remote sensing datasets are queried via the STAC API and retrieved directly from cloud-optimized Zarr stores hosted on Microsoft Azure Blob Storage with automated Shared Access Signature (SAS) token signing.

**Key Architectural Principle**: NASA Earthdata login credentials are NOT required for accessing Microsoft Planetary Computer-hosted datasets. All observational data is public, authenticated via SAS tokens, and retrieved with full scientific fidelity.

---

## 1. GPM IMERG Half-Hourly & Monthly Precipitation (`gpm-imerg-hhr`)

### Summary
The Integrated Multi-satellitE Retrievals for GPM (IMERG) algorithm combines calibrated precipitation estimates from the GPM constellation satellites, geostationary infrared observations, and monthly surface precipitation gauge analyses (GPCC).

- **STAC Collection ID**: `gpm-imerg-hhr`
- **Asset Key**: `zarr-abfs`
- **Catalog Endpoint**: `https://planetarycomputer.microsoft.com/api/stac/v1`
- **Underlying Storage**: Azure Blob Storage (`abfs://imerg/gpm-imerg-hhr.zarr`)
- **Access Protocol**: Signed Azure Blob Storage Zarr access via `planetary-computer`, `adlfs`, and `xarray`
- **Spatial Coverage**: Global (90.0°S to 90.0°N, 180.0°W to 180.0°E)
- **Spatial Resolution**: 0.1° × 0.1° (~10 km at equator)
- **Temporal Coverage on MPC**: June 2000 to May 2021 (368,160 half-hourly time slices)
- **Native Variable**: `precipitationCal` (calibrated precipitation rate in mm/hr)
- **BHIMA Aggregation**: Temporal integration from 30-minute rates to monthly accumulation (mm/month) based on monthly hours
- **Data Provenance Tag**: `REAL_NASA_DATA`

### Access Implementation
```python
import pystac_client, planetary_computer, xarray as xr, fsspec

catalog = pystac_client.Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace,
)
collection = catalog.get_collection("gpm-imerg-hhr")
asset = collection.assets["zarr-abfs"]
fs = fsspec.get_mapper(asset.href, **asset.extra_fields["xarray:storage_options"])
ds = xr.open_zarr(fs, **asset.extra_fields["xarray:open_kwargs"])
```

### Scientific Considerations & Limitations
- Precipitation estimates integrate microwave and infrared satellite radiometer soundings with GPCC surface rain gauge calibration.
- Coverage on Microsoft Planetary Computer currently spans June 2000 through May 2021.
- Mountainous relief and snow/ice cover introduce higher microwave retrieval uncertainties.

---

## 2. MODIS Land Surface Temperature (`modis-11A2-061`)

- **STAC Collection ID**: `modis-11A2-061`
- **Platform**: Terra Satellite (MODIS instrument)
- **Temporal Resolution**: 8-Day composite
- **Spatial Resolution**: 1 km
- **Variables**: `LST_Day_1km`, `LST_Night_1km` (Kelvin)
- **Format**: Cloud-Optimized GeoTIFF (COG) via signed Azure Blob Storage

---

## 3. MODIS Vegetation Indices (`modis-13A1-061`)

- **STAC Collection ID**: `modis-13A1-061`
- **Platform**: Terra Satellite (MODIS instrument)
- **Temporal Resolution**: 16-Day composite
- **Spatial Resolution**: 500 m
- **Variables**: Normalized Difference Vegetation Index (`NDVI`), Enhanced Vegetation Index (`EVI`)
- **Format**: Cloud-Optimized GeoTIFF (COG) via signed Azure Blob Storage

---

## 4. TerraClimate High-Resolution Climate Grids (`terraclimate`)

- **STAC Collection ID**: `terraclimate`
- **Temporal Resolution**: Monthly (1958 to present)
- **Spatial Resolution**: 1/24° (~4 km)
- **Variables**: Soil moisture (`soil`), precipitation (`ppt`), maximum temperature (`tmax`), minimum temperature (`tmin`), actual evapotranspiration (`aet`), climate water deficit (`def`), runoff (`q`)
- **Format**: Zarr / Cloud-Optimized GeoTIFF via Microsoft Planetary Computer

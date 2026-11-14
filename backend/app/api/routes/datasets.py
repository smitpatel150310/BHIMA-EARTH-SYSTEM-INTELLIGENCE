from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from app.core.data_access import NASADataAccessor, NASADataAccessError
from app.core.stac_discovery import discover_stac_collections, get_dataset_coverage
from app.core.persistent_cache import persistent_store
from app.config import get_settings

router = APIRouter(prefix="/datasets", tags=["datasets"])


def get_accessor():
    settings = get_settings()
    return NASADataAccessor(
        username=settings.nasa_earthdata_username,
        password=settings.nasa_earthdata_password
    )


@router.get("/")
async def list_datasets(accessor: NASADataAccessor = Depends(get_accessor)):
    return {"datasets": accessor.get_all_datasets()}


@router.get("/discover")
async def discover_datasets(force_refresh: bool = False):
    """
    Discover STAC Earth Observation collections available on Microsoft Planetary Computer.
    Returns rich metadata: spatial extent, temporal frequency, format, variables, citations.
    """
    collections = discover_stac_collections(force_refresh=force_refresh)
    return {
        "provider": "Microsoft Planetary Computer STAC API",
        "stac_url": "https://planetarycomputer.microsoft.com/api/stac/v1",
        "count": len(collections),
        "collections": collections
    }


@router.get("/coverage")
async def get_coverage(
    dataset_id: str = Query(..., description="Dataset ID (e.g. GPM_3IMERGM_07 or terraclimate)"),
    region_key: Optional[str] = Query(None, description="Optional region key (e.g. 71.00_21.50_73.00_23.00)")
):
    """
    Retrieve spatial bounding box, temporal period, and local cache availability for a dataset.
    """
    coverage = get_dataset_coverage(dataset_id=dataset_id, region_key=region_key)
    if "error" in coverage:
        raise HTTPException(status_code=404, detail=coverage["error"])
    return coverage


@router.get("/storage")
async def get_cache_storage():
    """
    Report storage metrics: SQLite DB size, compressed Parquet size, record counts.
    """
    return persistent_store.get_storage_stats()


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str, accessor: NASADataAccessor = Depends(get_accessor)):
    try:
        return accessor.get_dataset_info(dataset_id)
    except NASADataAccessError as e:
        raise HTTPException(status_code=404, detail=str(e))

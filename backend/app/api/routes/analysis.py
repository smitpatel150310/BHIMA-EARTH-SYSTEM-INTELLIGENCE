import time
import uuid
import asyncio
import logging
import threading
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Query
from app.core.data_access import NASADataAccessor, NASADataAccessError
from app.core.analysis import ScientificAnalysisEngine, AnalysisError
from app.core.job_store import job_store
from app.core.persistent_cache import (
    persistent_store,
    get_region_key,
    generate_cache_key,
    get_inflight_lock,
)
from app.models.schemas import TimeSeriesRequest, ComparisonRequest
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])


def get_dataset_db_variable(dataset_id: str) -> str:
    """Map public dataset identifier to its backing database storage variable."""
    if dataset_id in ("terraclimate", "terraclimate_ppt"):
        return "ppt"
    if dataset_id == "terraclimate_soil":
        return "soil"
    if dataset_id == "terraclimate_tmax":
        return "tmax"
    if dataset_id == "MOD11C3_061":
        return "land_surface_temperature"
    return "precipitationCal"


def get_accessor():
    settings = get_settings()
    return NASADataAccessor(
        username=settings.nasa_earthdata_username,
        password=settings.nasa_earthdata_password
    )


def get_engine():
    return ScientificAnalysisEngine()


def _run_timeseries_analysis(
    request: TimeSeriesRequest,
    accessor: NASADataAccessor,
    engine: ScientificAnalysisEngine
):
    """Synchronous worker function executed in a worker thread via asyncio.to_thread."""
    df, notes, provenance, data_source, cache_audit = accessor.get_timeseries_data(
        dataset_id=request.dataset_id,
        min_lon=request.region.min_lon,
        max_lon=request.region.max_lon,
        min_lat=request.region.min_lat,
        max_lat=request.region.max_lat,
        start_date=request.start_date,
        end_date=request.end_date,
        region_name=request.region.name,
    )

    info = accessor.get_dataset_info(request.dataset_id)
    result = engine.run_full_analysis(
        df=df,
        dataset_id=request.dataset_id,
        variable=info["variable"],
        units=info["units"],
        region_name=request.region.name,
        source_description=info["description"],
        processing_notes=notes,
        data_provenance=provenance,
        data_source=data_source,
        cache_audit=cache_audit,
    )
    return result


def _run_compare_analysis(
    request: ComparisonRequest,
    accessor: NASADataAccessor,
    engine: ScientificAnalysisEngine
):
    """Synchronous worker function executed in a worker thread via asyncio.to_thread."""
    info = accessor.get_dataset_info(request.dataset_id)
    results = {}
    for region_key, region in [("region_a", request.region_a), ("region_b", request.region_b)]:
        df, notes, provenance, data_source, cache_audit = accessor.get_timeseries_data(
            dataset_id=request.dataset_id,
            min_lon=region.min_lon,
            max_lon=region.max_lon,
            min_lat=region.min_lat,
            max_lat=region.max_lat,
            start_date=request.start_date,
            end_date=request.end_date,
            region_name=region.name,
        )
        result = engine.run_full_analysis(
            df=df,
            dataset_id=request.dataset_id,
            variable=info["variable"],
            units=info["units"],
            region_name=region.name,
            source_description=info["description"],
            processing_notes=notes,
            data_provenance=provenance,
            data_source=data_source,
            cache_audit=cache_audit,
        )
        results[region_key] = result

    return {
        "region_a": results["region_a"],
        "region_b": results["region_b"],
        "comparison_notes": [
            f"Both regions analyzed using identical dataset ({info['name']}) and units ({info['units']}).",
            "Direct non-parametric trend comparison (Mann-Kendall & Sen's Slope) is statistically valid within stated limitations."
        ],
        "computed_at": results["region_a"]["computed_at"],
        "data_provenance": results["region_a"].get("data_provenance", "REAL_NASA_DATA"),
        "data_source": results["region_a"].get("data_source", "Microsoft Planetary Computer (Local Cache)"),
    }


@router.post("/timeseries")
async def get_timeseries(
    request: TimeSeriesRequest,
    async_mode: bool = Query(False, description="Run in background and poll for status"),
    accessor: NASADataAccessor = Depends(get_accessor),
    engine: ScientificAnalysisEngine = Depends(get_engine)
):
    """
    Extract regional time series and compute trends directly from local observation cache.
    Zero external NASA/Planetary Computer calls. Instant <15ms execution.
    """
    try:
        result = await asyncio.to_thread(_run_timeseries_analysis, request, accessor, engine)
        return result
    except NASADataAccessError as nde:
        raise HTTPException(status_code=404, detail=str(nde))
    except Exception as e:
        logger.error(f"Analysis error for {request.region.name}: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_analysis_job_status(
    job_id: str,
    accessor: NASADataAccessor = Depends(get_accessor),
    engine: ScientificAnalysisEngine = Depends(get_engine),
):
    """
    Poll status of an asynchronous analysis job.
    Retrieves state from persistent database engine.
    If the worker was frozen by serverless execution lifecycle, seamlessly completes
    computation during this active polling invocation.
    """
    job = job_store.get_job(job_id)
    if not job:
        logger.warning(f"[JobStore] Job ID '{job_id}' not found in persistent store")
        raise HTTPException(status_code=404, detail=f"Analysis job {job_id} not found.")

    status = job.get("status", "queued")

    # Completed or Failed: return immediately
    if status in ("completed", "failed"):
        return {
            "job_id": job["job_id"],
            "status": status,
            "progress_pct": job.get("progress_pct", 100),
            "progress": job.get("progress_pct", 100),
            "message": job.get("message", ""),
            "result": job.get("result"),
            "error": job.get("error"),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
        }

    # If still processing / queued and request payload is available:
    req_payload = job.get("request_payload")
    if req_payload and isinstance(req_payload, dict):
        try:
            req = TimeSeriesRequest(**req_payload)
            reg_key = get_region_key(
                req.region.min_lon,
                req.region.min_lat,
                req.region.max_lon,
                req.region.max_lat,
            )

            db_var = get_dataset_db_variable(req.dataset_id)

            # Check if all months are now present in cache
            cached_recs, missing_months, _ = persistent_store.get_monthly_series(
                dataset_id=req.dataset_id,
                region_key=reg_key,
                start_date=req.start_date,
                end_date=req.end_date,
                variable=db_var,
            )

            if len(missing_months) == 0:
                logger.info(f"[JobStore] All observations in cache for job {job_id}. Completing analysis...")
                res = await asyncio.to_thread(_run_timeseries_analysis, req, accessor, engine)
                updated = job_store.update_job(
                    job_id=job_id,
                    status="completed",
                    progress_pct=100,
                    message="Analysis completed successfully.",
                    result=res,
                )
                return updated or job

            # If background worker was frozen in serverless environment, take over execution safely
            lock = get_inflight_lock(f"job_exec_{job_id}")
            if lock.acquire(blocking=False):
                try:
                    logger.info(
                        f"[JobStore] Taking over serverless execution for job {job_id} "
                        f"({len(missing_months)} missing months)..."
                    )
                    job_store.update_job(
                        job_id=job_id,
                        status="processing",
                        progress_pct=50,
                        message=f"Extracting {len(missing_months)} missing months from Microsoft Planetary Computer archive...",
                    )
                    res = await asyncio.to_thread(_run_timeseries_analysis, req, accessor, engine)
                    updated = job_store.update_job(
                        job_id=job_id,
                        status="completed",
                        progress_pct=100,
                        message="Analysis completed successfully.",
                        result=res,
                    )
                    return updated or job
                except Exception as ex:
                    logger.error(f"[JobStore] Polling execution for job {job_id} failed: {ex}", exc_info=True)
                    updated = job_store.update_job(
                        job_id=job_id,
                        status="failed",
                        progress_pct=100,
                        message=f"Analysis failed: {str(ex)}",
                        error=str(ex),
                    )
                    return updated or job
                finally:
                    lock.release()

        except Exception as ex:
            logger.warning(f"[JobStore] Error checking payload for job {job_id}: {ex}")

    return {
        "job_id": job["job_id"],
        "status": status,
        "progress_pct": job.get("progress_pct", 10),
        "progress": job.get("progress_pct", 10),
        "message": job.get("message", "Processing NASA Earth observations..."),
        "result": None,
        "error": None,
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
    }



@router.post("/compare")
async def compare_regions(
    request: ComparisonRequest,
    accessor: NASADataAccessor = Depends(get_accessor),
    engine: ScientificAnalysisEngine = Depends(get_engine)
):
    """
    Compare environmental time series and trends between two regions.
    Uses asyncio.to_thread to keep the event loop non-blocking.
    """
    try:
        result = await asyncio.to_thread(
            _run_compare_analysis,
            request,
            accessor,
            engine
        )
        return result
    except NASADataAccessError as e:
        logger.error(f"Comparison data access error: {e}")
        raise HTTPException(status_code=503, detail=f"Comparison data retrieval failed: {str(e)}")
    except Exception as e:
        logger.error(f"Comparison error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Comparison analysis failed: {str(e)}")


@router.get("/cache/summary")
async def get_cache_summary():
    """
    Get detailed audit of cached datasets, regions, and storage consumption (Part 7).
    """
    return persistent_store.get_cache_summary()


@router.get("/cache/status")
async def get_cache_status(
    dataset_id: str,
    min_lon: float,
    max_lon: float,
    min_lat: float,
    max_lat: float,
    start_date: str = "2015-01",
    end_date: str = "2020-12",
):
    """
    Inspect whether a dataset and region combination is cached in SQLite (Part 6).
    """
    if dataset_id == "terraclimate":
        dataset_id = "terraclimate_ppt"

    q_min_lon = min(float(min_lon), float(max_lon))
    q_max_lon = max(float(min_lon), float(max_lon))
    q_min_lat = min(float(min_lat), float(max_lat))
    q_max_lat = max(float(min_lat), float(max_lat))

    region_key = get_region_key(q_min_lon, q_min_lat, q_max_lon, q_max_lat)
    db_var = get_dataset_db_variable(dataset_id)

    cached_recs, missing_months, audit = persistent_store.get_monthly_series(
        dataset_id=dataset_id,
        region_key=region_key,
        start_date=start_date,
        end_date=end_date,
        variable=db_var,
    )

    total_months = len(cached_recs) + len(missing_months)
    is_cached = len(missing_months) == 0 and len(cached_recs) > 0

    return {
        "dataset_id": dataset_id,
        "region_key": region_key,
        "start_date": start_date,
        "end_date": end_date,
        "is_cached": is_cached,
        "cached_months": len(cached_recs),
        "total_months": total_months,
        "missing_months": len(missing_months),
        "cache_status": "HIT" if is_cached else ("PARTIAL" if cached_recs else "MISS"),
        "lookup_duration_ms": audit.get("lookup_duration_ms", 0.0),
        "data_provenance": cached_recs[0].get("data_provenance") if cached_recs else "REAL_NASA_DATA",
    }


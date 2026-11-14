import time
import uuid
import asyncio
import logging
import threading
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Query
from app.core.data_access import NASADataAccessor, NASADataAccessError
from app.core.analysis import ScientificAnalysisEngine, AnalysisError
from app.core.persistent_cache import persistent_store, get_region_key, generate_cache_key
from app.models.schemas import TimeSeriesRequest, ComparisonRequest
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])


class JobState:
    def __init__(self, job_id: str, cache_key: str):
        self.job_id = job_id
        self.cache_key = cache_key
        self.status = "processing"  # "processing" | "completed" | "failed"
        self.progress_pct = 5
        self.message = "Connecting to NASA Earth observation archive..."
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at = time.time()
        self.updated_at = time.time()


_jobs: Dict[str, JobState] = {}
_jobs_lock = threading.Lock()
_jobs_by_cache_key: Dict[str, str] = {}


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
        end_date=request.end_date
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
            end_date=request.end_date
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
        "data_source": results["region_a"].get("data_source", "Microsoft Planetary Computer"),
    }


@router.post("/timeseries")
async def get_timeseries(
    request: TimeSeriesRequest,
    async_mode: bool = Query(False, description="Run in background and poll for status"),
    accessor: NASADataAccessor = Depends(get_accessor),
    engine: ScientificAnalysisEngine = Depends(get_engine)
):
    """
    Extract regional time series and compute trends.
    If async_mode=true or if requested, runs in background and returns job_id for polling.
    If cached, returns AnalysisResult immediately.
    """
    reg_key = get_region_key(
        request.region.min_lon,
        request.region.min_lat,
        request.region.max_lon,
        request.region.max_lat
    )

    # Check if entire requested range is already in cache
    cached_recs, missing_months, audit = persistent_store.get_monthly_series(
        dataset_id=request.dataset_id,
        region_key=reg_key,
        start_date=request.start_date,
        end_date=request.end_date,
    )

    if len(missing_months) == 0:
        # Cache hit! Return immediately
        return await asyncio.to_thread(_run_timeseries_analysis, request, accessor, engine)

    # If async_mode is requested and we have missing months:
    if async_mode:
        cache_key = generate_cache_key(
            dataset_id=request.dataset_id,
            variable="precipitationCal",
            min_lon=request.region.min_lon,
            min_lat=request.region.min_lat,
            max_lon=request.region.max_lon,
            max_lat=request.region.max_lat,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        with _jobs_lock:
            existing_job_id = _jobs_by_cache_key.get(cache_key)
            if existing_job_id and existing_job_id in _jobs:
                job = _jobs[existing_job_id]
                if job.status == "processing":
                    return {
                        "job_id": job.job_id,
                        "status": "processing",
                        "progress_pct": job.progress_pct,
                        "message": job.message,
                    }
                elif job.status == "completed" and job.result:
                    return job.result

            job_id = str(uuid.uuid4())[:12]
            job = JobState(job_id=job_id, cache_key=cache_key)
            _jobs[job_id] = job
            _jobs_by_cache_key[cache_key] = job_id

        def _run_job_bg(j_id: str, req: TimeSeriesRequest):
            try:
                res = _run_timeseries_analysis(req, accessor, engine)
                with _jobs_lock:
                    if j_id in _jobs:
                        _jobs[j_id].status = "completed"
                        _jobs[j_id].progress_pct = 100
                        _jobs[j_id].message = "Analysis completed successfully."
                        _jobs[j_id].result = res
                        _jobs[j_id].updated_at = time.time()
            except Exception as ex:
                logger.error(f"Background analysis job {j_id} failed: {ex}", exc_info=True)
                with _jobs_lock:
                    if j_id in _jobs:
                        _jobs[j_id].status = "failed"
                        _jobs[j_id].error = str(ex)
                        _jobs[j_id].message = f"Analysis failed: {str(ex)}"
                        _jobs[j_id].updated_at = time.time()

        threading.Thread(target=_run_job_bg, args=(job_id, request), daemon=True).start()
        return {
            "job_id": job_id,
            "status": "processing",
            "progress_pct": 10,
            "message": f"Extracting {len(missing_months)} missing months from Microsoft Planetary Computer archive...",
        }

    # Synchronous mode (for tests and direct callers)
    try:
        result = await asyncio.to_thread(_run_timeseries_analysis, request, accessor, engine)
        return result
    except NASADataAccessError as e:
        logger.error(f"Data retrieval failed: {e}")
        raise HTTPException(status_code=503, detail=f"Earth observation data retrieval failed: {str(e)}")
    except AnalysisError as e:
        raise HTTPException(status_code=422, detail=f"Scientific analysis error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in timeseries endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal analysis error: {str(e)}")


@router.get("/jobs/{job_id}")
async def get_analysis_job_status(job_id: str):
    """Poll status of an asynchronous analysis job."""
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Analysis job {job_id} not found.")
        return {
            "job_id": job.job_id,
            "status": job.status,
            "progress_pct": job.progress_pct,
            "message": job.message,
            "result": job.result,
            "error": job.error,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
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

    cached_recs, missing_months, audit = persistent_store.get_monthly_series(
        dataset_id=dataset_id,
        region_key=region_key,
        start_date=start_date,
        end_date=end_date,
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


from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum


class DatasetID(str, Enum):
    GPM_IMERG_MONTHLY = "GPM_3IMERGM_07"
    MODIS_LST = "MOD11C3_061"
    TERRACLIMATE = "terraclimate"
    TERRACLIMATE_PPT = "terraclimate_ppt"
    TERRACLIMATE_SOIL = "terraclimate_soil"
    TERRACLIMATE_TMAX = "terraclimate_tmax"
    ERA5 = "era5-pds"
    MODIS_LST_8DAY = "MOD11A2_061"
    MODIS_NDVI = "MOD13Q1_061"
    LULC = "io-lulc-9-class"


class TemporalResolution(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class RegionRequest(BaseModel):
    name: str
    min_lon: float = Field(..., ge=-180, le=180)
    max_lon: float = Field(..., ge=-180, le=180)
    min_lat: float = Field(..., ge=-90, le=90)
    max_lat: float = Field(..., ge=-90, le=90)


class TimeSeriesRequest(BaseModel):
    dataset_id: Union[DatasetID, str]
    region: RegionRequest
    start_date: str  # YYYY-MM
    end_date: str    # YYYY-MM
    temporal_resolution: TemporalResolution = TemporalResolution.MONTHLY


class DataPoint(BaseModel):
    date: str
    value: Optional[float]
    valid_pixels: Optional[int] = None
    coverage_fraction: Optional[float] = None


class TimeSeriesResult(BaseModel):
    dataset_id: str
    variable: str
    units: str
    region: Union[RegionRequest, str]
    start_date: str
    end_date: str
    temporal_resolution: str
    data: List[DataPoint]
    n_valid: int
    n_missing: int
    retrieval_timestamp: str
    source_description: str
    processing_notes: List[str]
    validation_issues: Optional[List[str]] = None
    data_provenance: str = "REAL_NASA_DATA"
    data_source: Optional[str] = None
    cache_status: Optional[str] = "MISS"
    cache_hit: Optional[bool] = False
    lookup_duration_ms: Optional[float] = 0.0
    storage_type: Optional[str] = None


class TrendResult(BaseModel):
    method: str
    slope: float  # units per year
    slope_units: str
    intercept: Optional[float] = None
    p_value: float
    is_significant: bool  # p < 0.05
    significance_level: float = 0.05
    trend_direction: str  # 'increasing', 'decreasing', 'no_trend'
    confidence_interval_low: Optional[float] = None
    confidence_interval_high: Optional[float] = None
    n_observations: int
    period_start: str
    period_end: str
    interpretation: str
    limitations: List[str]
    tau: Optional[float] = None
    s: Optional[float] = None
    var_s: Optional[float] = None
    z: Optional[float] = None


class AnalysisResult(BaseModel):
    analysis_id: str
    timeseries: TimeSeriesResult
    trend: Optional[Union[TrendResult, Dict[str, Any]]] = None
    statistics: Dict[str, Any]
    methodology: str
    computed_at: str
    data_provenance: str = "REAL_NASA_DATA"
    data_source: Optional[str] = None
    cache_status: Optional[str] = "MISS"
    cache_hit: Optional[bool] = False
    lookup_duration_ms: Optional[float] = 0.0
    storage_type: Optional[str] = None


class ComparisonRequest(BaseModel):
    dataset_id: DatasetID
    region_a: RegionRequest
    region_b: RegionRequest
    start_date: str
    end_date: str
    temporal_resolution: TemporalResolution = TemporalResolution.MONTHLY


class ComparisonResult(BaseModel):
    region_a_analysis: AnalysisResult
    region_b_analysis: AnalysisResult
    comparison_notes: List[str]
    computed_at: str


class AgentMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    timestamp: Optional[str] = None


class AgentRequest(BaseModel):
    message: str
    conversation_history: List[AgentMessage] = []
    investigation_context: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    response: str
    tool_calls_made: List[Dict[str, Any]] = []
    analysis_results: Optional[Dict[str, Any]] = None
    timestamp: str


class DatasetInfo(BaseModel):
    id: str
    name: str
    provider: str
    product_id: str
    source_url: str
    spatial_resolution: str
    temporal_resolution: str
    units: str
    variable: str
    coverage_start: str
    coverage_end: str
    description: str
    limitations: List[str]

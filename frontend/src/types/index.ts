export interface DatasetInfo {
  id: string;
  name: string;
  provider: string;
  product_id: string;
  source_url: string;
  spatial_resolution: string;
  temporal_resolution: string;
  units: string;
  variable: string;
  coverage_start: string;
  coverage_end: string;
  description: string;
  limitations: string[];
}

export interface RegionRequest {
  name: string;
  min_lon: number;
  max_lon: number;
  min_lat: number;
  max_lat: number;
}

export interface TimeSeriesRequest {
  dataset_id: string;
  region: RegionRequest;
  start_date: string;    // YYYY-MM
  end_date: string;      // YYYY-MM
  temporal_resolution?: string;
}

export interface DataPoint {
  date: string;    // YYYY-MM
  value: number | null;
  valid_pixels?: number;
  coverage_fraction?: number;
}

export interface TimeSeriesData {
  dataset_id: string;
  variable: string;
  units: string;
  region: string | RegionRequest;
  start_date: string;
  end_date: string;
  temporal_resolution: string;
  data: DataPoint[];
  n_valid: number;
  n_missing: number;
  retrieval_timestamp: string;
  source_description: string;
  processing_notes: string[];
  validation_issues?: string[];
  data_provenance?: 'REAL_NASA_DATA' | 'SYNTHETIC_DEMO_DATA' | 'DATA_UNAVAILABLE' | string;
  data_source?: string;
}

export interface TrendResult {
  method: string;
  slope: number;      // per year
  slope_units: string;
  intercept?: number;
  p_value: number;
  is_significant: boolean;
  trend_direction: 'increasing' | 'decreasing' | 'no_trend';
  confidence_interval_low?: number;
  confidence_interval_high?: number;
  n_observations: number;
  period_start: string;
  period_end: string;
  interpretation: string;
  limitations: string[];
  tau?: number;
  s?: number;
  var_s?: number;
  z?: number;
  error?: string;
}

export interface AnalysisResult {
  analysis_id: string;
  timeseries: TimeSeriesData;
  trend: TrendResult | null;
  statistics: Record<string, any>;
  methodology: string;
  computed_at: string;
  data_provenance?: 'REAL_NASA_DATA' | 'SYNTHETIC_DEMO_DATA' | 'DATA_UNAVAILABLE' | string;
  data_source?: string;
}

export interface ComparisonRequest {
  dataset_id: string;
  region_a: RegionRequest;
  region_b: RegionRequest;
  start_date: string;
  end_date: string;
  temporal_resolution?: string;
}

export interface ComparisonResult {
  region_a?: AnalysisResult;
  region_b?: AnalysisResult;
  region_a_analysis?: AnalysisResult;
  region_b_analysis?: AnalysisResult;
  comparison_notes: string[];
  computed_at: string;
  data_provenance?: 'REAL_NASA_DATA' | 'SYNTHETIC_DEMO_DATA' | 'DATA_UNAVAILABLE' | string;
  data_source?: string;
}

export interface ToolCallRecord {
  tool: string;
  args?: Record<string, any>;
  success?: boolean;
}

export interface AgentMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  tool_calls?: ToolCallRecord[];
}

export interface AgentRequest {
  message: string;
  conversation_history?: AgentMessage[];
  investigation_context?: Record<string, any>;
}

export interface AgentResponse {
  response: string;
  tool_calls_made: ToolCallRecord[];
  analysis_results?: any;
  timestamp: string;
}

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: Record<string, any>;
}

export interface HealthResponse {
  status: string;
  version?: string;
  timestamp?: string;
  services?: Record<string, string>;
}

export interface CacheStatusResponse {
  dataset_id: string;
  region_key: string;
  start_date: string;
  end_date: string;
  is_cached: boolean;
  cached_months: number;
  total_months: number;
  missing_months: number;
  cache_status: 'HIT' | 'PARTIAL' | 'MISS';
  lookup_duration_ms: number;
  data_provenance?: string;
}

export interface CacheSummaryResponse {
  total_records: number;
  cached_series_count: number;
  datasets: string[];
  series: Array<{
    dataset_id: string;
    region_key: string;
    cached_months: number;
    earliest_date: string;
    latest_date: string;
    is_72_complete: boolean;
  }>;
  storage: {
    sqlite_db_size_kb: number;
    parquet_cache_size_kb: number;
    total_storage_size_kb: number;
  };
}

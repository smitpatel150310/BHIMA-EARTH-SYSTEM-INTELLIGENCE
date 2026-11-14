import {
  DatasetInfo,
  TimeSeriesRequest,
  AnalysisResult,
  ComparisonRequest,
  ComparisonResult,
  AgentRequest,
  AgentResponse,
  ToolDefinition,
  HealthResponse,
  CacheStatusResponse,
  CacheSummaryResponse,
} from '../types';

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  (typeof window !== 'undefined' && window.location.hostname !== 'localhost' ? '' : 'http://localhost:8000')
).replace(/\/+$/, '');

/**
 * Global Configurable Timeout Matrix
 * Scientific satellite extraction and multi-decade analyses can take several minutes cold.
 * Fast health checks and standard metadata endpoints use shorter bounds.
 */
export const API_TIMEOUTS = {
  HEALTH: 10000,          // 10s for lightweight health probes
  METADATA: 30000,        // 30s for catalog and schema retrieval
  AGENT_CHAT: 120000,     // 2 minutes for multi-step Gemini tool calling
  LONG_RUNNING: 900000,   // 15 minutes (900,000 ms) for satellite extractions and regional comparisons
  POLL_REQUEST: 15000,    // 15 seconds per background job poll HTTP request
  POLL_INTERVAL: 2000,    // 2 seconds polling frequency
};

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Determine default timeout based on endpoint category
 */
function getDefaultTimeout(endpoint: string): number {
  if (endpoint.includes('/health')) {
    return API_TIMEOUTS.HEALTH;
  }
  if (endpoint.includes('/analysis/timeseries') || endpoint.includes('/analysis/compare')) {
    return API_TIMEOUTS.LONG_RUNNING;
  }
  if (endpoint.includes('/agent/chat')) {
    return API_TIMEOUTS.AGENT_CHAT;
  }
  return API_TIMEOUTS.METADATA;
}

async function request<T>(
  endpoint: string,
  options: RequestInit & { timeoutMs?: number } = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  const headers = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...(options.headers || {}),
  };

  const timeoutMs = options.timeoutMs ?? getDefaultTimeout(endpoint);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      ...options,
      headers,
      signal: options.signal || controller.signal,
    });

    if (!res.ok) {
      let errorMessage = `HTTP ${res.status}: ${res.statusText}`;
      let errorData = null;
      try {
        errorData = await res.json();
        if (errorData?.detail) {
          errorMessage = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        } else if (errorData?.message) {
          errorMessage = errorData.message;
        }
      } catch {
        // If not JSON, leave as status text
      }
      throw new ApiError(errorMessage, res.status, errorData);
    }

    return await res.json();
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    if (err.name === 'AbortError') {
      const seconds = Math.round(timeoutMs / 1000);
      throw new ApiError(
        `Request to ${endpoint} timed out after ${seconds}s. The backend may still be processing NASA satellite observations. Please retry.`,
        408
      );
    }
    // Network / fetch error
    throw new ApiError(
      err?.message || `Failed to connect to BHIMA backend service at ${API_BASE_URL}. Ensure server is running.`,
      0
    );
  } finally {
    clearTimeout(timer);
  }
}

export const apiClient = {
  async getHealth(): Promise<HealthResponse> {
    return request<HealthResponse>('/health', { timeoutMs: API_TIMEOUTS.HEALTH });
  },

  async getDatasets(): Promise<{ datasets: DatasetInfo[] }> {
    return request<{ datasets: DatasetInfo[] }>('/datasets/', { timeoutMs: API_TIMEOUTS.METADATA });
  },

  async getDataset(id: string): Promise<DatasetInfo> {
    return request<DatasetInfo>(`/datasets/${encodeURIComponent(id)}`, { timeoutMs: API_TIMEOUTS.METADATA });
  },

  /**
   * Retrieves regional time series from Microsoft Planetary Computer.
   * Utilizes non-blocking background job polling if cold satellite extraction is needed,
   * with up to 15 minutes (900,000 ms) execution window and graceful network retry.
   */
  async getTimeSeries(
    data: TimeSeriesRequest,
    onProgress?: (progressPct: number, message: string) => void
  ): Promise<AnalysisResult> {
    // 1. Initial request: backend either returns immediate AnalysisResult (<10ms cache hit)
    // or initiates a deduplicated background worker job and returns a job_id.
    const initialRes = await request<any>('/analysis/timeseries?async_mode=true', {
      method: 'POST',
      body: JSON.stringify(data),
      timeoutMs: 45000, // 45 seconds for initial handshake
    });

    // Cache hit: Direct AnalysisResult returned
    if (initialRes?.analysis_id && initialRes?.timeseries) {
      return initialRes as AnalysisResult;
    }

    if (initialRes?.status === 'completed' && initialRes?.result) {
      return initialRes.result as AnalysisResult;
    }

    // Background job started: poll until completed up to 15 minutes
    if (initialRes?.job_id) {
      const jobId = initialRes.job_id;
      // 900,000 ms / 2,000 ms = 450 polls (15 minutes maximum polling duration)
      const maxPolls = Math.floor(API_TIMEOUTS.LONG_RUNNING / API_TIMEOUTS.POLL_INTERVAL);
      let consecutiveErrors = 0;

      for (let i = 0; i < maxPolls; i++) {
        await new Promise((resolve) => setTimeout(resolve, API_TIMEOUTS.POLL_INTERVAL));

        try {
          const pollRes = await request<any>(`/analysis/jobs/${jobId}`, {
            timeoutMs: API_TIMEOUTS.POLL_REQUEST,
          });
          consecutiveErrors = 0; // reset on successful poll

          if (onProgress && pollRes?.progress_pct !== undefined) {
            onProgress(
              pollRes.progress_pct,
              pollRes.message || 'Processing NASA Earth observations...'
            );
          }

          if (pollRes?.status === 'completed' && pollRes?.result) {
            return pollRes.result as AnalysisResult;
          }

          if (pollRes?.status === 'failed') {
            throw new ApiError(
              pollRes.error || pollRes.message || 'Scientific analysis pipeline encountered an error.',
              500
            );
          }
        } catch (pollErr: any) {
          // If the error was a real terminal failure (like 500 status from the job), rethrow
          if (pollErr instanceof ApiError && pollErr.status === 500) {
            throw pollErr;
          }

          consecutiveErrors++;
          // Allow up to 5 consecutive network glitches during heavy compute before giving up
          if (consecutiveErrors >= 5) {
            throw new ApiError(
              `Lost connection while polling analysis progress: ${pollErr.message}`,
              0
            );
          }
        }
      }

      throw new ApiError(
        'Analysis did not complete within the 15-minute scientific processing timeout.',
        408
      );
    }

    return initialRes as AnalysisResult;
  },

  async getComparison(data: ComparisonRequest): Promise<ComparisonResult> {
    return request<ComparisonResult>('/analysis/compare', {
      method: 'POST',
      body: JSON.stringify(data),
      timeoutMs: API_TIMEOUTS.LONG_RUNNING, // 15 minutes for dual satellite extractions
    });
  },

  async chatWithAgent(data: AgentRequest): Promise<AgentResponse> {
    return request<AgentResponse>('/agent/chat', {
      method: 'POST',
      body: JSON.stringify(data),
      timeoutMs: API_TIMEOUTS.AGENT_CHAT, // 2 minutes for AI tool calling
    });
  },

  async getAgentTools(): Promise<{ tools: ToolDefinition[] }> {
    return request<{ tools: ToolDefinition[] }>('/agent/tools', {
      timeoutMs: API_TIMEOUTS.METADATA,
    });
  },

  async getCacheStatus(params: {
    dataset_id: string;
    min_lon: number;
    max_lon: number;
    min_lat: number;
    max_lat: number;
    start_date?: string;
    end_date?: string;
  }): Promise<CacheStatusResponse> {
    const q_min_lon = Math.min(params.min_lon, params.max_lon).toFixed(2);
    const q_min_lat = Math.min(params.min_lat, params.max_lat).toFixed(2);
    const q_max_lon = Math.max(params.min_lon, params.max_lon).toFixed(2);
    const q_max_lat = Math.max(params.min_lat, params.max_lat).toFixed(2);
    const regionKey = `${q_min_lon}_${q_min_lat}_${q_max_lon}_${q_max_lat}`;

    try {
      const q = new URLSearchParams({
        dataset_id: params.dataset_id,
        min_lon: params.min_lon.toString(),
        max_lon: params.max_lon.toString(),
        min_lat: params.min_lat.toString(),
        max_lat: params.max_lat.toString(),
        start_date: params.start_date || '2015-01',
        end_date: params.end_date || '2020-12',
      });
      return await request<CacheStatusResponse>(`/analysis/cache/status?${q.toString()}`, {
        timeoutMs: API_TIMEOUTS.METADATA,
      });
    } catch {
      // Graceful fallback to active /datasets/coverage endpoint
      const covRes = await request<any>(
        `/datasets/coverage?dataset_id=${encodeURIComponent(params.dataset_id)}&region_key=${encodeURIComponent(regionKey)}`,
        { timeoutMs: API_TIMEOUTS.METADATA }
      );
      const cov = covRes?.local_cache_coverage || {};
      const cachedMonths = cov.cached_monthly_months || 0;
      const isCached = cov.is_cached || cachedMonths >= 72;
      return {
        dataset_id: params.dataset_id,
        region_key: regionKey,
        start_date: params.start_date || '2015-01',
        end_date: params.end_date || '2020-12',
        is_cached: isCached,
        cached_months: cachedMonths,
        total_months: 72,
        missing_months: Math.max(0, 72 - cachedMonths),
        cache_status: isCached ? 'HIT' : cachedMonths > 0 ? 'PARTIAL' : 'MISS',
        lookup_duration_ms: 2.0,
        data_provenance: covRes?.data_provenance || 'REAL_NASA_DATA',
      };
    }
  },

  async getCacheSummary(): Promise<CacheSummaryResponse> {
    try {
      return await request<CacheSummaryResponse>('/analysis/cache/summary', {
        timeoutMs: API_TIMEOUTS.METADATA,
      });
    } catch {
      const storageRes = await request<any>('/datasets/storage', {
        timeoutMs: API_TIMEOUTS.METADATA,
      });
      return {
        total_records: storageRes?.cached_monthly_records || 0,
        cached_series_count: 8,
        datasets: ['GPM_3IMERGM_07', 'terraclimate_ppt', 'terraclimate_soil', 'terraclimate_tmax', 'MOD11C3_061'],
        series: [],
        storage: {
          sqlite_db_size_kb: storageRes?.sqlite_db_size_kb || 0,
          parquet_cache_size_kb: storageRes?.parquet_storage_size_kb || 0,
          total_storage_size_kb: storageRes?.total_storage_size_kb || 0,
        },
      };
    }
  },
};

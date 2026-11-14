import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from './client';
import {
  TimeSeriesRequest,
  ComparisonRequest,
  AgentRequest,
} from '../types';

export const queryKeys = {
  health: ['health'] as const,
  datasets: ['datasets'] as const,
  dataset: (id: string) => ['datasets', id] as const,
  timeseries: (req?: Partial<TimeSeriesRequest>) => ['timeseries', req] as const,
  compare: (req?: Partial<ComparisonRequest>) => ['compare', req] as const,
  tools: ['agent', 'tools'] as const,
  cacheStatus: (params: any) => ['cache', 'status', params] as const,
  cacheSummary: ['cache', 'summary'] as const,
};

export function useHealthCheck() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 30000,
    retry: 2,
  });
}

export function useDatasets() {
  return useQuery({
    queryKey: queryKeys.datasets,
    queryFn: () => apiClient.getDatasets(),
    staleTime: 1000 * 60 * 10, // 10 minutes
  });
}

export function useDataset(id?: string) {
  return useQuery({
    queryKey: queryKeys.dataset(id || ''),
    queryFn: () => apiClient.getDataset(id!),
    enabled: Boolean(id),
    staleTime: 1000 * 60 * 10,
  });
}

export function useTimeSeries(request: TimeSeriesRequest | null) {
  const isEnabled = Boolean(
    request &&
    request.dataset_id &&
    request.region &&
    request.start_date &&
    request.end_date
  );

  return useQuery({
    queryKey: queryKeys.timeseries(request || undefined),
    queryFn: () => apiClient.getTimeSeries(request!),
    enabled: isEnabled,
    staleTime: 1000 * 60 * 5,
  });
}

export function useCompare(request: ComparisonRequest | null) {
  const isEnabled = Boolean(
    request &&
    request.dataset_id &&
    request.region_a &&
    request.region_b &&
    request.start_date &&
    request.end_date
  );

  return useQuery({
    queryKey: queryKeys.compare(request || undefined),
    queryFn: () => apiClient.getComparison(request!),
    enabled: isEnabled,
    staleTime: 1000 * 60 * 5,
  });
}

export function useAgentChat() {
  return useMutation({
    mutationFn: (request: AgentRequest) => apiClient.chatWithAgent(request),
  });
}

export function useAgentTools() {
  return useQuery({
    queryKey: queryKeys.tools,
    queryFn: () => apiClient.getAgentTools(),
    staleTime: 1000 * 60 * 15,
  });
}

export function useCacheStatus(params: {
  dataset_id?: string;
  min_lon?: number;
  max_lon?: number;
  min_lat?: number;
  max_lat?: number;
  start_date?: string;
  end_date?: string;
} | null) {
  const isEnabled = Boolean(
    params &&
    params.dataset_id &&
    params.min_lon !== undefined &&
    params.max_lon !== undefined &&
    params.min_lat !== undefined &&
    params.max_lat !== undefined
  );

  return useQuery({
    queryKey: queryKeys.cacheStatus(params),
    queryFn: () =>
      apiClient.getCacheStatus({
        dataset_id: params!.dataset_id!,
        min_lon: params!.min_lon!,
        max_lon: params!.max_lon!,
        min_lat: params!.min_lat!,
        max_lat: params!.max_lat!,
        start_date: params?.start_date,
        end_date: params?.end_date,
      }),
    enabled: isEnabled,
    staleTime: 1000 * 10, // 10 seconds
    refetchInterval: 15000, // poll periodically in case caching background job completes
  });
}

export function useCacheSummary() {
  return useQuery({
    queryKey: queryKeys.cacheSummary,
    queryFn: () => apiClient.getCacheSummary(),
    staleTime: 1000 * 30, // 30 seconds
  });
}

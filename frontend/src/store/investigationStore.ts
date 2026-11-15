import { create } from 'zustand';
import { RegionRequest, AnalysisResult } from '../types';

export const REGION_PRESETS: Record<string, RegionRequest> = {
  'Gujarat, India': {
    name: 'Gujarat, India',
    min_lon: 68.1,
    max_lon: 74.5,
    min_lat: 20.1,
    max_lat: 24.7,
  },
  'Amazon Basin': {
    name: 'Amazon Basin',
    min_lon: -73.0,
    max_lon: -50.0,
    min_lat: -15.0,
    max_lat: 5.0,
  },
  'Sahel (West Africa)': {
    name: 'Sahel (West Africa)',
    min_lon: -15.0,
    max_lon: 40.0,
    min_lat: 10.0,
    max_lat: 20.0,
  },
  'California, USA': {
    name: 'California, USA',
    min_lon: -124.5,
    max_lon: -114.1,
    min_lat: 32.5,
    max_lat: 42.0,
  },
  'Murray-Darling Basin': {
    name: 'Murray-Darling Basin',
    min_lon: 138.0,
    max_lon: 149.0,
    min_lat: -37.0,
    max_lat: -24.0,
  },
  'Monsoon Asia': {
    name: 'Monsoon Asia',
    min_lon: 60.0,
    max_lon: 110.0,
    min_lat: 10.0,
    max_lat: 35.0,
  },
  'Sahara Desert': {
    name: 'Sahara Desert',
    min_lon: -5.0,
    max_lon: 35.0,
    min_lat: 20.0,
    max_lat: 30.0,
  },
  'Great Plains, USA': {
    name: 'Great Plains, USA',
    min_lon: -104.0,
    max_lon: -96.0,
    min_lat: 32.0,
    max_lat: 48.0,
  },
  'Central Gujarat (Vadodara)': {
    name: 'Central Gujarat (Vadodara)',
    min_lon: 73.1,
    max_lon: 73.3,
    min_lat: 22.1,
    max_lat: 22.5,
  },
  'Rajasthan, India': {
    name: 'Rajasthan, India',
    min_lon: 69.5,
    max_lon: 78.0,
    min_lat: 23.0,
    max_lat: 30.0,
  },
};

export interface RecentInvestigation {
  id: string;
  datasetId: string;
  regionName: string;
  startDate: string;
  endDate: string;
  timestamp: string;
  slope?: number;
  isSignificant?: boolean;
}

interface InvestigationState {
  selectedDataset: string;      // dataset_id
  selectedRegion: RegionRequest | null;
  startDate: string;            // YYYY-MM
  endDate: string;              // YYYY-MM
  analysisResult: AnalysisResult | null;
  isLoading: boolean;
  error: string | null;
  progressMsg: string;
  progressPct: number | null;
  startTime: number | null;
  recentInvestigations: RecentInvestigation[];
  
  // Actions
  setDataset: (id: string) => void;
  setRegion: (region: RegionRequest | null) => void;
  setDateRange: (start: string, end: string) => void;
  setResult: (result: AnalysisResult | null) => void;
  setLoading: (loading: boolean) => void;
  setProgress: (msg: string, pct?: number | null) => void;
  setError: (error: string | null) => void;
  reset: () => void;
  addRecentInvestigation: (item: RecentInvestigation) => void;
}

const DEFAULT_DATASET = 'GPM_3IMERGM_07';
const DEFAULT_REGION: RegionRequest = REGION_PRESETS['Gujarat, India'];
const DEFAULT_START_DATE = '2015-01';
const DEFAULT_END_DATE = '2020-12';

const STORAGE_KEY = 'bhima_recent_investigations';

function loadRecent(): RecentInvestigation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveRecent(list: RecentInvestigation[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list.slice(0, 10)));
  } catch {
    // ignore
  }
}

export const useInvestigationStore = create<InvestigationState>((set, get) => ({
  selectedDataset: DEFAULT_DATASET,
  selectedRegion: DEFAULT_REGION,
  startDate: DEFAULT_START_DATE,
  endDate: DEFAULT_END_DATE,
  analysisResult: null,
  isLoading: false,
  error: null,
  progressMsg: '',
  progressPct: null,
  startTime: null,
  recentInvestigations: loadRecent(),

  setDataset: (id: string) => set({ selectedDataset: id, error: null }),
  setRegion: (region: RegionRequest | null) => set({ selectedRegion: region, error: null }),
  setDateRange: (start: string, end: string) => set({ startDate: start, endDate: end, error: null }),
  
  setResult: (result: AnalysisResult | null) => {
    set({
      analysisResult: result,
      isLoading: false,
      error: null,
      progressMsg: '',
      progressPct: null,
      startTime: null,
    });
    if (result) {
      const state = get();
      const regionName = typeof result.timeseries.region === 'string'
        ? result.timeseries.region
        : result.timeseries.region?.name || 'Custom Region';

      const recentItem: RecentInvestigation = {
        id: result.analysis_id || `${Date.now()}`,
        datasetId: result.timeseries.dataset_id || state.selectedDataset,
        regionName,
        startDate: result.timeseries.start_date || state.startDate,
        endDate: result.timeseries.end_date || state.endDate,
        timestamp: new Date().toISOString(),
        slope: result.trend?.slope,
        isSignificant: result.trend?.is_significant,
      };

      const updated = [
        recentItem,
        ...state.recentInvestigations.filter(
          (i) => !(i.regionName === regionName && i.datasetId === recentItem.datasetId)
        ),
      ].slice(0, 8);

      saveRecent(updated);
      set({ recentInvestigations: updated });
    }
  },

  setLoading: (loading: boolean) =>
    set({
      isLoading: loading,
      error: loading ? null : get().error,
      startTime: loading ? Date.now() : null,
      progressMsg: loading ? 'Initializing Earth observation retrieval...' : '',
      progressPct: null,
    }),

  setProgress: (msg: string, pct?: number | null) =>
    set({
      progressMsg: msg,
      progressPct: pct !== undefined ? pct : get().progressPct,
    }),

  setError: (error: string | null) =>
    set({
      error,
      isLoading: false,
      progressMsg: '',
      progressPct: null,
      startTime: null,
    }),

  reset: () =>
    set({
      selectedDataset: DEFAULT_DATASET,
      selectedRegion: DEFAULT_REGION,
      startDate: DEFAULT_START_DATE,
      endDate: DEFAULT_END_DATE,
      analysisResult: null,
      isLoading: false,
      error: null,
      progressMsg: '',
      progressPct: null,
      startTime: null,
    }),

  addRecentInvestigation: (item: RecentInvestigation) => {
    const updated = [item, ...get().recentInvestigations.filter((i) => i.id !== item.id)].slice(0, 8);
    saveRecent(updated);
    set({ recentInvestigations: updated });
  },
}));

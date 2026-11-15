import React from 'react';
import { useInvestigationStore } from '../store/investigationStore';
import { useDatasets, useCacheStatus } from '../api/queries';
import { apiClient } from '../api/client';
import { ExplorerMap } from '../components/map/ExplorerMap';
import { RegionSelector } from '../components/map/RegionSelector';
import { MapLegend } from '../components/map/MapLegend';
import { AnalysisPanel } from '../components/analysis/AnalysisPanel';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { ErrorState } from '../components/ui/ErrorState';
import { LoadingState } from '../components/ui/LoadingState';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Calendar, Database, Play, CheckCircle2, RotateCcw, Zap } from 'lucide-react';

export const ExplorerPage: React.FC = () => {
  const {
    selectedDataset,
    selectedRegion,
    startDate,
    endDate,
    analysisResult,
    isLoading,
    error,
    progressMsg,
    progressPct,
    startTime,
    setDataset,
    setRegion,
    setDateRange,
    setResult,
    setLoading,
    setProgress,
    setError,
    reset,
  } = useInvestigationStore();

  const { data: datasetData } = useDatasets();
  const datasets = datasetData?.datasets || [
    {
      id: 'GPM_3IMERGM_07',
      name: 'GPM IMERG Monthly Precipitation v07',
      units: 'mm/month',
      variable: 'Precipitation',
      spatial_resolution: '0.1° × 0.1° (~10 km)',
      coverage_start: '2000-06',
      coverage_end: '2024-05',
      provider: 'NASA GES DISC',
    },
    {
      id: 'MOD11C3_061',
      name: 'MODIS/Terra Land Surface Temperature Monthly CMG',
      units: 'Kelvin',
      variable: 'Land Surface Temp',
      spatial_resolution: '0.05° (~5.6 km)',
      coverage_start: '2000-03',
      coverage_end: '2024-06',
      provider: 'NASA LP DAAC',
    },
  ];

  const currentDataset = datasets.find((d) => d.id === selectedDataset) || datasets[0];

  const cacheStatusParams = selectedRegion
    ? {
        dataset_id: selectedDataset,
        min_lon: selectedRegion.min_lon,
        max_lon: selectedRegion.max_lon,
        min_lat: selectedRegion.min_lat,
        max_lat: selectedRegion.max_lat,
        start_date: startDate,
        end_date: endDate,
      }
    : null;

  const { data: cacheStatus, isLoading: isCacheChecking } = useCacheStatus(cacheStatusParams);

  const handleRunInvestigation = async () => {
    // Prevent duplicate submissions if already running
    if (isLoading) return;

    if (!selectedRegion) {
      setError('Please select or specify a geographic bounding region.');
      return;
    }

    setLoading(true);
    setProgress('Connecting to Microsoft Planetary Computer & Azure Blob Storage...');

    try {
      const res = await apiClient.getTimeSeries(
        {
          dataset_id: selectedDataset,
          region: selectedRegion,
          start_date: startDate,
          end_date: endDate,
          temporal_resolution: 'monthly',
        },
        (pct, msg) => {
          setProgress(msg, pct);
        }
      );
      setResult(res);
    } catch (err: any) {
      setError(
        err?.message ||
          'Investigation failed to complete. The Microsoft Planetary Computer cluster may be busy. Please retry.'
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-bhima-border pb-4">
        <div>
          <h2 className="text-xl font-bold text-bhima-text">Earth Explorer</h2>
          <p className="text-xs text-bhima-muted">
            Configure spatial polygons and request area-weighted time series extractions from NASA archives.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={reset}
            disabled={isLoading}
            leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Reset Form
          </Button>
        </div>
      </div>

      {/* Two Column Layout: Controls (Left) + Map (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Panel: Controls */}
        <div className="lg:col-span-4 space-y-5">
          <Card className="space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-bhima-secondary">
              Investigation Parameters
            </h3>

            {/* 1. Dataset Selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-bhima-text uppercase tracking-wider flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-bhima-primary" />
                NASA Earth Dataset
              </label>
              <select
                value={selectedDataset}
                onChange={(e) => setDataset(e.target.value)}
                disabled={isLoading}
                className="w-full bg-white border border-bhima-border rounded-md px-3 py-2 text-xs font-medium text-bhima-text focus:outline-none focus:ring-1 focus:ring-bhima-primary cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
              {currentDataset && (
                <div className="flex items-center justify-between text-[11px] text-bhima-muted pt-1">
                  <span>Units: {currentDataset.units}</span>
                  <Badge variant="outline">{currentDataset.spatial_resolution}</Badge>
                </div>
              )}
            </div>

            {/* 2. Region Selector & Cache Status Indicator */}
            <div className="space-y-1.5">
              <RegionSelector
                value={selectedRegion}
                onChange={(reg) => setRegion(reg)}
                label="Target Bounding Box"
              />

              {/* Processed Observations Indicator */}
              {selectedRegion && cacheStatus?.is_cached && (
                <div className="pt-1">
                  <div className="flex items-center justify-between p-2 rounded bg-emerald-50/80 border border-emerald-200/80 text-emerald-800 text-[11px]">
                    <div className="flex items-center gap-1.5 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                      <span>Validated Earth Observations Available ({cacheStatus.cached_months}/{cacheStatus.total_months} months)</span>
                    </div>
                    <span className="font-mono text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded font-semibold">
                      Instant &lt;10ms
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* 3. Date Range (YYYY-MM) */}
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-bhima-text uppercase tracking-wider flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-bhima-primary" />
                Temporal Range (Monthly)
              </label>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-[11px] text-bhima-muted block mb-0.5">Start Month</span>
                  <input
                    type="month"
                    value={startDate}
                    onChange={(e) => setDateRange(e.target.value, endDate)}
                    disabled={isLoading}
                    min="2000-01"
                    max="2024-12"
                    className="w-full bg-white border border-bhima-border rounded px-2.5 py-1.5 text-xs font-mono text-bhima-text focus:ring-1 focus:ring-bhima-primary focus:outline-none disabled:opacity-60"
                  />
                </div>
                <div>
                  <span className="text-[11px] text-bhima-muted block mb-0.5">End Month</span>
                  <input
                    type="month"
                    value={endDate}
                    onChange={(e) => setDateRange(startDate, e.target.value)}
                    disabled={isLoading}
                    min="2000-01"
                    max="2024-12"
                    className="w-full bg-white border border-bhima-border rounded px-2.5 py-1.5 text-xs font-mono text-bhima-text focus:ring-1 focus:ring-bhima-primary focus:outline-none disabled:opacity-60"
                  />
                </div>
              </div>
            </div>

            {/* 4. Action Button with circular spinner */}
            <Button
              className="w-full mt-2"
              size="lg"
              onClick={handleRunInvestigation}
              disabled={isLoading}
              leftIcon={
                isLoading ? (
                  <LoadingSpinner size="sm" variant="white" />
                ) : cacheStatus?.is_cached ? (
                  <Zap className="w-4 h-4 fill-current text-amber-300" />
                ) : (
                  <Play className="w-4 h-4 fill-current" />
                )
              }
            >
              {isLoading
                ? progressPct !== null
                  ? `Investigating (${progressPct}%)...`
                  : 'Investigating...'
                : cacheStatus?.is_cached
                ? 'Execute Instant Investigation (<10ms)'
                : 'Execute Investigation'}
            </Button>
          </Card>

          {/* Map & Sensor Meta */}
          <MapLegend
            spatialResolution={currentDataset?.spatial_resolution}
            variableName={currentDataset?.variable}
            units={currentDataset?.units}
          />
        </div>

        {/* Right Panel: MapLibre Map */}
        <div className="lg:col-span-8 space-y-4">
          <div className="h-[460px] rounded-lg overflow-hidden border border-bhima-border shadow-xs bg-white">
            <ExplorerMap
              region={selectedRegion}
              onRegionChange={(reg) => setRegion(reg)}
              cachedObservationsCount={cacheStatus?.cached_months ?? (selectedRegion ? 72 : undefined)}
            />
          </div>

          <div className="flex items-center justify-between text-xs text-bhima-muted px-1">
            <span>Coordinate Reference System: WGS 84 (EPSG:4326)</span>
            <span>OpenStreetMap Basemap Grid</span>
          </div>
        </div>
      </div>

      {/* Prominent Loading Panel when investigating */}
      {isLoading && (
        <div className="pt-4 border-t border-bhima-border animate-fade-in">
          <LoadingState
            title="Investigating Earth Observation Records"
            message={
              progressMsg ||
              'Retrieving and processing scientific data from Microsoft Planetary Computer...'
            }
            progressPct={progressPct}
            startTime={startTime}
            stage={progressPct !== null ? `Processed Chunks: ${progressPct}%` : 'Extracting Earth System Observations'}
            spinnerSize="lg"
          />
        </div>
      )}

      {/* Error state if failed */}
      {!isLoading && error && (
        <ErrorState
          title="Analysis Execution Failed"
          message={error}
          onRetry={handleRunInvestigation}
        />
      )}

      {/* Results View when available */}
      {!isLoading && analysisResult && (
        <div className="pt-6 border-t border-bhima-border space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-bhima-text flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              Investigation Findings
            </h3>
            <span className="text-xs font-mono text-bhima-muted">
              Computed: {new Date(analysisResult.computed_at).toLocaleTimeString()}
            </span>
          </div>

          <AnalysisPanel result={analysisResult} />
        </div>
      )}
    </div>
  );
};

export default ExplorerPage;

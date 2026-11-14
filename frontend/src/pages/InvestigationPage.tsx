import React from 'react';
import { useInvestigationStore } from '../store/investigationStore';
import { AnalysisPanel } from '../components/analysis/AnalysisPanel';
import { TrendChart } from '../components/charts/TrendChart';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { ErrorState } from '../components/ui/ErrorState';
import { LoadingState } from '../components/ui/LoadingState';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { Search, Play, ArrowRight, BarChart2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiClient } from '../api/client';

export const InvestigationPage: React.FC = () => {
  const {
    analysisResult,
    selectedDataset,
    selectedRegion,
    startDate,
    endDate,
    isLoading,
    error,
    progressMsg,
    progressPct,
    startTime,
    setResult,
    setLoading,
    setProgress,
    setError,
  } = useInvestigationStore();

  const handleRunInvestigation = async () => {
    if (isLoading) return;

    if (!selectedRegion) {
      setError('Please select a region first in the Explorer.');
      return;
    }

    setLoading(true);
    setProgress('Querying Microsoft Planetary Computer & Azure Blob Storage...');

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
          'Failed to retrieve analysis from backend. Microsoft Planetary Computer may be undergoing maintenance.'
      );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-bhima-border pb-4">
        <div>
          <h2 className="text-xl font-bold text-bhima-text">Investigation Analysis</h2>
          <p className="text-xs text-bhima-muted">
            Non-parametric statistical verification and temporal decomposition of satellite records.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link to="/app/explorer">
            <Button variant="outline" size="sm" disabled={isLoading}>
              Modify Geometry
            </Button>
          </Link>
          <Button
            size="sm"
            onClick={handleRunInvestigation}
            disabled={isLoading}
            leftIcon={
              isLoading ? (
                <LoadingSpinner size="xs" variant="white" />
              ) : (
                <Play className="w-3.5 h-3.5 fill-current" />
              )
            }
          >
            {isLoading
              ? 'Investigating...'
              : analysisResult
              ? 'Re-run Analysis'
              : 'Run Investigation'}
          </Button>
        </div>
      </div>

      {/* Prominent Loading Panel */}
      {isLoading && (
        <LoadingState
          title="Executing Scientific Investigation Pipeline"
          message={
            progressMsg ||
            'Computing area-weighted spatial mean, Hamed-Rao Mann-Kendall trend, and Sen’s slope...'
          }
          progressPct={progressPct}
          startTime={startTime}
          stage={progressPct !== null ? `Observation Chunks: ${progressPct}%` : 'Statistical Computation'}
          spinnerSize="lg"
        />
      )}

      {/* Error state */}
      {!isLoading && error && (
        <ErrorState
          title="Analysis Could Not Complete"
          message={error}
          onRetry={handleRunInvestigation}
        />
      )}

      {/* Result Display */}
      {!isLoading && analysisResult ? (
        <div className="space-y-6">
          <AnalysisPanel result={analysisResult} />

          {/* Annual Decadal Trend View */}
          {analysisResult.trend && (
            <div className="space-y-2 pt-4 border-t border-bhima-border">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-bhima-text flex items-center gap-1.5">
                  <BarChart2 className="w-4 h-4 text-bhima-secondary" />
                  Multi-Decadal Annual Aggregates & Long-Term Trajectory
                </h3>
                <span className="text-xs text-bhima-muted">
                  Slope: {analysisResult.trend.slope.toFixed(3)} {analysisResult.trend.slope_units}
                </span>
              </div>
              <TrendChart
                timeseries={analysisResult.timeseries}
                trend={analysisResult.trend}
                height={280}
              />
            </div>
          )}
        </div>
      ) : (
        !isLoading &&
        !error && (
          <EmptyState
            icon={Search}
            title="No Active Investigation Result"
            description={`Selected region: ${
              selectedRegion?.name || 'Gujarat, India'
            } (${startDate} to ${endDate}). Execute the pipeline to compute the Mann-Kendall test and Sen's slope.`}
            action={
              <Button
                onClick={handleRunInvestigation}
                disabled={isLoading}
                rightIcon={<ArrowRight className="w-4 h-4" />}
              >
                Execute for {selectedRegion?.name || 'Gujarat, India'}
              </Button>
            }
          />
        )
      )}
    </div>
  );
};

export default InvestigationPage;

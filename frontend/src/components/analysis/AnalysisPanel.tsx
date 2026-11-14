import React from 'react';
import { AnalysisResult } from '../../types';
import { TimeSeriesChart } from '../charts/TimeSeriesChart';
import { TrendCard } from './TrendCard';
import { StatisticsCard } from './StatisticsCard';
import { SourceInfo } from './SourceInfo';
import { Badge } from '../ui/Badge';
import { Calendar, MapPin, Activity } from 'lucide-react';

export interface AnalysisPanelProps {
  result: AnalysisResult;
  showExtendedTrendChart?: boolean;
}

export const AnalysisPanel: React.FC<AnalysisPanelProps> = ({ result }) => {
  const regionName =
    typeof result.timeseries.region === 'string'
      ? result.timeseries.region
      : result.timeseries.region?.name || 'Selected Region';

  return (
    <div className="space-y-6">
      {/* Investigation summary bar */}
      <div className="bg-white border border-bhima-border rounded-lg p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-bhima-secondary">
              Analysis Run: {result.analysis_id}
            </span>
            <Badge variant="primary">{result.timeseries.variable}</Badge>

            {/* Explicit Data Provenance Badge */}
            {result.data_provenance === 'REAL_NASA_DATA' ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-100/80 border border-emerald-300 text-emerald-800 text-[11px] font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-pulse" />
                REAL NASA OBSERVATIONS (Microsoft Planetary Computer)
              </span>
            ) : result.data_provenance === 'SYNTHETIC_DEMO_DATA' ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-100 border border-amber-300 text-amber-800 text-[11px] font-semibold">
                SYNTHETIC DEMO DATA — NOT MEASURED OBSERVATIONS
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-rose-100 border border-rose-300 text-rose-800 text-[11px] font-semibold">
                DATA UNAVAILABLE
              </span>
            )}
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-bhima-text flex items-center gap-2">
            <MapPin className="w-5 h-5 text-bhima-primary" />
            {regionName}
          </h2>
          {result.data_source && (
            <p className="text-xs text-bhima-muted flex items-center gap-1">
              <span className="font-medium text-bhima-text">Provider:</span> {result.data_source}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs text-bhima-muted">
          <div className="flex items-center gap-1.5 bg-bhima-subtle px-3 py-1.5 rounded border border-bhima-border">
            <Calendar className="w-3.5 h-3.5 text-bhima-secondary" />
            <span>
              {result.timeseries.start_date} → {result.timeseries.end_date}
            </span>
          </div>
          <div className="flex items-center gap-1.5 bg-bhima-subtle px-3 py-1.5 rounded border border-bhima-border">
            <Activity className="w-3.5 h-3.5 text-bhima-secondary" />
            <span className="capitalize">{result.timeseries.temporal_resolution}</span>
          </div>
        </div>
      </div>

      {/* Main Time Series Chart */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-bhima-text">
            Temporal Trajectory & Sen's Linear Trend Overlay
          </h3>
          <span className="text-xs text-bhima-muted">Units: {result.timeseries.units}</span>
        </div>
        <TimeSeriesChart timeseries={result.timeseries} trend={result.trend} />
      </div>

      {/* Analytical Cards Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TrendCard trend={result.trend} />
        <StatisticsCard statistics={result.statistics} timeseries={result.timeseries} />
      </div>

      {/* Scientific Source and Lineage */}
      <SourceInfo timeseries={result.timeseries} methodology={result.methodology} />
    </div>
  );
};

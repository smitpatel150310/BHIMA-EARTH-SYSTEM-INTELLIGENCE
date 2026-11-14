import React from 'react';
import { Card } from '../ui/Card';
import { TimeSeriesData } from '../../types';
import { Calculator } from 'lucide-react';

export interface StatisticsCardProps {
  statistics: Record<string, any>;
  timeseries: TimeSeriesData;
}

export const StatisticsCard: React.FC<StatisticsCardProps> = ({ statistics, timeseries }) => {
  const nValid = timeseries.n_valid ?? timeseries.data.filter((d) => d.value !== null).length;
  const nMissing = timeseries.n_missing ?? timeseries.data.filter((d) => d.value === null).length;
  const total = nValid + nMissing;
  const completeness = total > 0 ? ((nValid / total) * 100).toFixed(1) : '100.0';

  const mean = statistics.mean ?? statistics.average;
  const median = statistics.median;
  const std = statistics.std ?? statistics.standard_deviation;
  const min = statistics.min;
  const max = statistics.max;
  const p25 = statistics.p25 ?? statistics.percentile_25;
  const p75 = statistics.p75 ?? statistics.percentile_75;

  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between border-b border-bhima-border pb-2.5">
        <div className="flex items-center gap-2">
          <Calculator className="w-4 h-4 text-bhima-primary" />
          <h4 className="text-sm font-semibold text-bhima-text">Descriptive Statistics</h4>
        </div>
        <span className="text-[11px] font-mono text-bhima-muted">
          Completeness: <strong className="text-bhima-text font-medium">{completeness}%</strong>
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div className="bg-bhima-subtle/50 p-2.5 rounded border border-bhima-border">
          <div className="text-[10px] text-bhima-muted uppercase">Mean</div>
          <div className="text-sm font-mono font-semibold text-bhima-text mt-0.5">
            {mean !== undefined && mean !== null ? Number(mean).toFixed(2) : '—'}
          </div>
          <div className="text-[10px] text-bhima-muted">{timeseries.units}</div>
        </div>

        <div className="bg-bhima-subtle/50 p-2.5 rounded border border-bhima-border">
          <div className="text-[10px] text-bhima-muted uppercase">Median</div>
          <div className="text-sm font-mono font-semibold text-bhima-text mt-0.5">
            {median !== undefined && median !== null ? Number(median).toFixed(2) : '—'}
          </div>
          <div className="text-[10px] text-bhima-muted">{timeseries.units}</div>
        </div>

        <div className="bg-bhima-subtle/50 p-2.5 rounded border border-bhima-border">
          <div className="text-[10px] text-bhima-muted uppercase">Std Deviation</div>
          <div className="text-sm font-mono font-semibold text-bhima-text mt-0.5">
            {std !== undefined && std !== null ? Number(std).toFixed(2) : '—'}
          </div>
          <div className="text-[10px] text-bhima-muted">± variability</div>
        </div>

        <div className="bg-bhima-subtle/50 p-2.5 rounded border border-bhima-border">
          <div className="text-[10px] text-bhima-muted uppercase">Range [Min – Max]</div>
          <div className="text-sm font-mono font-semibold text-bhima-text mt-0.5">
            {min !== undefined && max !== undefined
              ? `${Number(min).toFixed(1)} – ${Number(max).toFixed(1)}`
              : '—'}
          </div>
          <div className="text-[10px] text-bhima-muted">{timeseries.units}</div>
        </div>
      </div>

      {/* Observation counts */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-bhima-border text-[11px] text-bhima-muted">
        <div>
          Valid observations: <span className="font-mono text-bhima-text font-medium">{nValid}</span>
        </div>
        <div>
          Missing/Masked: <span className="font-mono text-bhima-text font-medium">{nMissing}</span>
        </div>
        {p25 !== undefined && p75 !== undefined && (
          <div>
            IQR [25%–75%]:{' '}
            <span className="font-mono text-bhima-text font-medium">
              {Number(p25).toFixed(1)} – {Number(p75).toFixed(1)}
            </span>
          </div>
        )}
      </div>
    </Card>
  );
};

import React from 'react';
import { TrendResult } from '../../types';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { TrendingUp, TrendingDown, Minus, CheckCircle, HelpCircle } from 'lucide-react';

export interface TrendCardProps {
  trend: TrendResult | null | undefined;
}

export const TrendCard: React.FC<TrendCardProps> = ({ trend }) => {
  if (!trend) {
    return (
      <Card className="text-center py-6 text-bhima-muted text-xs">
        No trend analysis calculated for this query.
      </Card>
    );
  }

  const isPositive = trend.slope > 0;
  const isZero = trend.slope === 0;

  const DirectionIcon = isZero ? Minus : isPositive ? TrendingUp : TrendingDown;
  const directionVariant = isZero ? 'default' : isPositive ? 'success' : 'danger';

  return (
    <Card className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <span className="text-[11px] font-semibold text-bhima-secondary uppercase tracking-wider block">
            Non-Parametric Trend
          </span>
          <h4 className="text-base font-bold text-bhima-text mt-0.5">{trend.method}</h4>
        </div>
        <div className="flex items-center gap-1.5">
          <Badge variant={trend.is_significant ? 'success' : 'default'} size="md">
            {trend.is_significant ? (
              <span className="flex items-center gap-1">
                <CheckCircle className="w-3 h-3" /> Significant (p &lt; 0.05)
              </span>
            ) : (
              'Not Significant'
            )}
          </Badge>
          <Badge variant={directionVariant} size="md">
            <span className="flex items-center gap-1 capitalize">
              <DirectionIcon className="w-3 h-3" />
              {trend.trend_direction?.replace('_', ' ') || 'No Trend'}
            </span>
          </Badge>
        </div>
      </div>

      {/* Main slope metric */}
      <div className="bg-bhima-subtle/80 rounded-md p-3.5 border border-bhima-border">
        <div className="text-[11px] text-bhima-muted">Sen's Slope Estimate</div>
        <div className="flex items-baseline gap-2 mt-1">
          <span className="text-2xl font-bold font-mono text-bhima-text">
            {trend.slope > 0 ? `+${trend.slope.toFixed(4)}` : trend.slope.toFixed(4)}
          </span>
          <span className="text-xs font-mono text-bhima-muted">{trend.slope_units}</span>
        </div>
        {trend.confidence_interval_low !== undefined && trend.confidence_interval_high !== undefined && (
          <div className="text-[11px] font-mono text-bhima-muted mt-1">
            95% CI: [{trend.confidence_interval_low.toFixed(4)}, {trend.confidence_interval_high.toFixed(4)}]
          </div>
        )}
      </div>

      {/* Metrics breakdown grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
        <div className="border border-bhima-border rounded p-2 bg-white">
          <div className="text-[10px] text-bhima-muted uppercase">p-value</div>
          <div className="font-mono font-medium text-bhima-text mt-0.5">
            {trend.p_value < 0.001 ? '< 0.001' : trend.p_value.toFixed(4)}
          </div>
        </div>

        <div className="border border-bhima-border rounded p-2 bg-white">
          <div className="text-[10px] text-bhima-muted uppercase">Kendall Tau (τ)</div>
          <div className="font-mono font-medium text-bhima-text mt-0.5">
            {trend.tau !== undefined && trend.tau !== null ? trend.tau.toFixed(3) : '—'}
          </div>
        </div>

        <div className="border border-bhima-border rounded p-2 bg-white">
          <div className="text-[10px] text-bhima-muted uppercase">Z-Score</div>
          <div className="font-mono font-medium text-bhima-text mt-0.5">
            {trend.z !== undefined && trend.z !== null ? trend.z.toFixed(2) : '—'}
          </div>
        </div>

        <div className="border border-bhima-border rounded p-2 bg-white">
          <div className="text-[10px] text-bhima-muted uppercase">Observed Points</div>
          <div className="font-mono font-medium text-bhima-text mt-0.5">
            {trend.n_observations}
          </div>
        </div>
      </div>

      {/* Interpretation */}
      {trend.interpretation && (
        <div className="text-xs text-bhima-text bg-[#F3F6F4] p-3 rounded border border-bhima-border leading-relaxed">
          <span className="font-semibold text-bhima-primary">Scientific Interpretation: </span>
          {trend.interpretation}
        </div>
      )}

      {/* Limitations note */}
      {trend.limitations && trend.limitations.length > 0 && (
        <div className="text-[11px] text-bhima-muted pt-2 border-t border-bhima-border">
          <div className="flex items-center gap-1 font-medium text-bhima-secondary mb-1">
            <HelpCircle className="w-3 h-3" /> Limitations & Scientific Caveats
          </div>
          <ul className="list-disc list-inside space-y-0.5 pl-1">
            {trend.limitations.map((lim, idx) => (
              <li key={idx}>{lim}</li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
};

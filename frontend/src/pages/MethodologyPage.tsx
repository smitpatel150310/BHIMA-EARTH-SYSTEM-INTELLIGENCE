import React from 'react';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { BookOpen, CheckCircle, HelpCircle, Shield, TrendingUp, Layers, Calculator } from 'lucide-react';

export const MethodologyPage: React.FC = () => {
  return (
    <div className="space-y-8 max-w-4xl">
      {/* Header */}
      <div className="border-b border-bhima-border pb-4">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-bhima-secondary mb-1">
          <BookOpen className="w-3.5 h-3.5 text-bhima-primary" />
          <span>Scientific Protocol</span>
        </div>
        <h2 className="text-2xl font-bold text-bhima-text">Statistical Methodology & Analysis Protocol</h2>
        <p className="text-xs text-bhima-muted mt-1 leading-relaxed">
          Mathematical formulation and algorithmic implementation of BHIMA’s trend detection engine.
        </p>
      </div>

      {/* 1. Spatial Averaging & Extraction */}
      <Card className="space-y-4">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-bhima-primary/10 text-bhima-primary flex items-center justify-center font-bold text-xs">
            01
          </div>
          <h3 className="text-sm font-bold text-bhima-text">
            Spatial Extraction & Area-Weighted Averaging
          </h3>
        </div>

        <p className="text-xs text-bhima-muted leading-relaxed">
          Given a rectangular geographic bounding box defined by longitudinal bounds [λ_min, λ_max] and
          latitudinal bounds [φ_min, φ_max], the spatial average for any time step t is computed over all
          valid raster grid cells within the polygon:
        </p>

        <div className="bg-bhima-subtle/80 p-3 rounded font-mono text-xs text-bhima-text border border-bhima-border">
          x̄(t) = ( Σ [ w_i * x_i(t) ] ) / ( Σ w_i )
        </div>

        <p className="text-xs text-bhima-muted leading-relaxed">
          Where <span className="font-mono text-bhima-text">w_i = cos(φ_i)</span> represents the latitudinal area-weighting
          factor, ensuring high-latitude grid cells (which have smaller physical ground areas on an equirectangular grid)
          are not disproportionately weighted against equatorial cells. Cells tagged as missing or fill values
          (e.g., cloud occlusion in MODIS or ocean masks in gauge calibration) are excluded, and the valid pixel fraction
          is recorded.
        </p>
      </Card>

      {/* 2. Mann-Kendall Non-Parametric Test */}
      <Card className="space-y-4">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-bhima-primary/10 text-bhima-primary flex items-center justify-center font-bold text-xs">
            02
          </div>
          <h3 className="text-sm font-bold text-bhima-text">
            The Mann-Kendall Non-Parametric Test for Monotonic Trend
          </h3>
        </div>

        <p className="text-xs text-bhima-muted leading-relaxed">
          Environmental time series frequently deviate from normal distributions and contain extreme weather outliers.
          Standard ordinary least-squares (OLS) regression is sensitive to outliers and assumes normality of residuals.
          BHIMA therefore employs the non-parametric <strong>Mann-Kendall (MK) test</strong> (Mann 1945, Kendall 1975) to
          statistically assess whether there is a monotonic upward or downward trend.
        </p>

        <div className="bg-bhima-subtle/80 p-3 rounded font-mono text-xs text-bhima-text border border-bhima-border space-y-1">
          <div>S = Σ_{'{i=1}'}^{'{n-1}'} Σ_{'{j=i+1}'}^{'{n}'} sgn(x_j - x_i)</div>
          <div className="text-[11px] text-bhima-muted mt-1">
            sgn(θ) = +1 if θ &gt; 0, 0 if θ = 0, -1 if θ &lt; 0
          </div>
        </div>

        <p className="text-xs text-bhima-muted leading-relaxed">
          For sample sizes <span className="font-mono text-bhima-text">n &gt; 10</span>, the statistic S is approximately normally
          distributed with mean <span className="font-mono text-bhima-text">E(S) = 0</span> and variance computed with tie corrections:
        </p>

        <div className="bg-bhima-subtle/80 p-3 rounded font-mono text-xs text-bhima-text border border-bhima-border">
          Var(S) = [ n(n - 1)(2n + 5) - Σ t_k(t_k - 1)(2t_k + 5) ] / 18
        </div>

        <p className="text-xs text-bhima-muted leading-relaxed">
          The standardized test statistic <span className="font-mono text-bhima-text">Z</span> is computed, and a two-tailed
          hypothesis test is conducted at significance level <span className="font-mono text-bhima-text">α = 0.05</span>. The null
          hypothesis <span className="font-mono text-bhima-text">H₀</span> (no trend) is rejected when <span className="font-mono text-bhima-text">p &lt; 0.05</span>.
        </p>
      </Card>

      {/* 3. Sen's Slope Estimator */}
      <Card className="space-y-4">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded bg-bhima-primary/10 text-bhima-primary flex items-center justify-center font-bold text-xs">
            03
          </div>
          <h3 className="text-sm font-bold text-bhima-text">
            Sen’s Non-Parametric Slope Estimator
          </h3>
        </div>

        <p className="text-xs text-bhima-muted leading-relaxed">
          While the MK test determines the presence and statistical significance of a monotonic trend, <strong>Sen’s slope estimator</strong> (Sen 1968)
          calculates the robust magnitude of the trend. It computes the slopes of all pairwise combinations of data points:
        </p>

        <div className="bg-bhima-subtle/80 p-3 rounded font-mono text-xs text-bhima-text border border-bhima-border">
          Q_k = (x_j - x_i) / (j - i), for all 1 ≤ i &lt; j ≤ n
        </div>

        <p className="text-xs text-bhima-muted leading-relaxed">
          Sen’s slope <span className="font-mono text-bhima-text">Q_med</span> is the median of all <span className="font-mono text-bhima-text">N = n(n - 1) / 2</span> pairwise
          slopes. This estimator is exceptionally resilient against missing data, spikes, and sensor recalibrations, boasting a breakdown
          point of 29%.
        </p>
      </Card>

      {/* 4. Limitations and Seasonality */}
      <Card className="space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-bhima-secondary">
          <HelpCircle className="w-4 h-4 text-bhima-primary" />
          <span>Scientific Caveats & Recommendations</span>
        </div>

        <div className="space-y-2 text-xs text-bhima-muted leading-relaxed">
          <p>
            • <strong>Autocorrelation:</strong> Monthly hydrologic and temperature data exhibit positive serial autocorrelation
            (persistence). While Sen’s slope magnitude remains unbiased, positive autocorrelation can inflate the apparent significance
            of standard MK test statistics. Users should evaluate multi-year annual aggregates alongside monthly tests.
          </p>
          <p>
            • <strong>Seasonality:</strong> Regions influenced by monsoonal regimes experience strong cyclical seasonality.
            Comparing equivalent calendar periods or annual totals provides the most reliable long-term decadal insights.
          </p>
        </div>
      </Card>
    </div>
  );
};

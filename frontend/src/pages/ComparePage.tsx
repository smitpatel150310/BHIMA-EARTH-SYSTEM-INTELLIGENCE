import React, { useState } from 'react';
import { RegionRequest, ComparisonResult, AnalysisResult } from '../types';
import { REGION_PRESETS } from '../store/investigationStore';
import { apiClient } from '../api/client';
import { RegionSelector } from '../components/map/RegionSelector';
import { ComparisonChart } from '../components/charts/ComparisonChart';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { ErrorState } from '../components/ui/ErrorState';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingState } from '../components/ui/LoadingState';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { BarChart2, ArrowRightLeft, TrendingUp, TrendingDown, Minus, CheckCircle, Calendar, Play } from 'lucide-react';

export const ComparePage: React.FC = () => {
  const [regionA, setRegionA] = useState<RegionRequest>(REGION_PRESETS['Amazon Basin']);
  const [regionB, setRegionB] = useState<RegionRequest>(REGION_PRESETS['Sahel (West Africa)']);
  const [datasetId, setDatasetId] = useState<string>('GPM_3IMERGM_07');
  const [startDate, setStartDate] = useState<string>('2015-01');
  const [endDate, setEndDate] = useState<string>('2020-12');

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null);
  const [startTime, setStartTime] = useState<number | null>(null);

  const handleCompare = async () => {
    if (isLoading) return;
    setIsLoading(true);
    setStartTime(Date.now());
    setError(null);

    try {
      const res = await apiClient.getComparison({
        dataset_id: datasetId,
        region_a: regionA,
        region_b: regionB,
        start_date: startDate,
        end_date: endDate,
        temporal_resolution: 'monthly',
      });
      setComparisonResult(res);
    } catch (err: any) {
      setError(err?.message || 'Comparison analysis failed against the backend service.');
    } finally {
      setIsLoading(false);
      setStartTime(null);
    }
  };

  const aResult: AnalysisResult | undefined =
    comparisonResult?.region_a_analysis || comparisonResult?.region_a;
  const bResult: AnalysisResult | undefined =
    comparisonResult?.region_b_analysis || comparisonResult?.region_b;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-bhima-border pb-4">
        <h2 className="text-xl font-bold text-bhima-text">Comparative Regional Analysis</h2>
        <p className="text-xs text-bhima-muted">
          Benchmark hydrological and climatological divergence across contrasting biomes over identical temporal periods.
        </p>
      </div>

      {/* Configuration Controls */}
      <Card className="space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Region A */}
          <div className="bg-bhima-subtle/40 p-4 rounded-md border border-bhima-border space-y-3">
            <div className="flex items-center justify-between border-b border-bhima-border pb-2">
              <span className="text-xs font-bold text-bhima-primary uppercase tracking-wider flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#31594B]" />
                Region A Baseline
              </span>
              <Badge variant="outline">Target 1</Badge>
            </div>
            <RegionSelector value={regionA} onChange={setRegionA} label="Select Region A" />
          </div>

          {/* Region B */}
          <div className="bg-bhima-subtle/40 p-4 rounded-md border border-bhima-border space-y-3">
            <div className="flex items-center justify-between border-b border-bhima-border pb-2">
              <span className="text-xs font-bold text-[#A85A3F] uppercase tracking-wider flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#A85A3F]" />
                Region B Benchmark
              </span>
              <Badge variant="outline">Target 2</Badge>
            </div>
            <RegionSelector value={regionB} onChange={setRegionB} label="Select Region B" />
          </div>
        </div>

        {/* Temporal & Dataset Settings */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-bhima-border">
          <div>
            <label className="text-xs font-semibold text-bhima-text block mb-1">Dataset</label>
            <select
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
              className="w-full bg-white border border-bhima-border rounded px-3 py-1.5 text-xs font-medium text-bhima-text"
            >
              <option value="GPM_3IMERGM_07">GPM IMERG Monthly Precipitation</option>
              <option value="MOD11C3_061">MODIS Land Surface Temperature</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-bhima-text block mb-1">Start Month</label>
            <input
              type="month"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full bg-white border border-bhima-border rounded px-2.5 py-1.5 text-xs font-mono"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-bhima-text block mb-1">End Month</label>
            <input
              type="month"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full bg-white border border-bhima-border rounded px-2.5 py-1.5 text-xs font-mono"
            />
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <Button
            size="md"
            onClick={handleCompare}
            disabled={isLoading}
            leftIcon={
              isLoading ? (
                <LoadingSpinner size="sm" variant="white" />
              ) : (
                <ArrowRightLeft className="w-4 h-4" />
              )
            }
          >
            {isLoading ? 'Comparing Regions...' : 'Execute Regional Comparison'}
          </Button>
        </div>
      </Card>

      {/* Prominent Loading Panel */}
      {isLoading && (
        <LoadingState
          title="Executing Dual Regional Extraction"
          message={`Retrieving and harmonizing satellite observations for ${regionA.name} and ${regionB.name} from Microsoft Planetary Computer...`}
          startTime={startTime}
          stage="Cross-Regional STAC Harmonization"
          spinnerSize="lg"
        />
      )}

      {!isLoading && error && (
        <ErrorState
          title="Comparison Failed"
          message={error}
          onRetry={handleCompare}
        />
      )}

      {/* Comparison Results */}
      {!isLoading && aResult && bResult ? (
        <div className="space-y-6">
          {/* Provenance Banner */}
          <div className="flex items-center justify-between p-3 rounded-md bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
              <span className="font-semibold">
                Provenance: {comparisonResult?.data_provenance || 'REAL_NASA_DATA'}
              </span>
              <span className="text-emerald-700">
                — {comparisonResult?.data_source || 'Microsoft Planetary Computer GPM IMERG'}
              </span>
            </div>
            <span className="text-[11px] text-emerald-700 font-mono">
              Synchronized STAC Access
            </span>
          </div>

          {/* Dual Time Series Chart */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-bhima-text">
                Comparative Time Series Overlay ({regionA.name} vs {regionB.name})
              </h3>
              <span className="text-xs text-bhima-muted">
                Units: {aResult.timeseries.units}
              </span>
            </div>
            <ComparisonChart regionA={aResult} regionB={bResult} height={380} />
          </div>

          {/* Side-by-Side Trend & Statistical Comparison Table */}
          <Card className="space-y-4">
            <h4 className="text-sm font-semibold text-bhima-text border-b border-bhima-border pb-2">
              Statistical & Trend Comparison Matrix
            </h4>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="border-b border-bhima-border text-bhima-muted">
                    <th className="py-2 px-3 font-semibold uppercase text-[10px]">Parameter</th>
                    <th className="py-2 px-3 font-semibold text-bhima-primary">
                      {regionA.name} (Region A)
                    </th>
                    <th className="py-2 px-3 font-semibold text-[#A85A3F]">
                      {regionB.name} (Region B)
                    </th>
                    <th className="py-2 px-3 font-semibold text-bhima-text">Delta (A - B)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-bhima-border">
                  <tr>
                    <td className="py-2.5 px-3 font-medium text-bhima-muted">Sen's Slope</td>
                    <td className="py-2.5 px-3 font-mono font-bold">
                      {aResult.trend
                        ? `${aResult.trend.slope > 0 ? '+' : ''}${aResult.trend.slope.toFixed(3)} ${aResult.trend.slope_units}`
                        : '—'}
                    </td>
                    <td className="py-2.5 px-3 font-mono font-bold">
                      {bResult.trend
                        ? `${bResult.trend.slope > 0 ? '+' : ''}${bResult.trend.slope.toFixed(3)} ${bResult.trend.slope_units}`
                        : '—'}
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      {aResult.trend && bResult.trend
                        ? `${(aResult.trend.slope - bResult.trend.slope).toFixed(3)} / yr`
                        : '—'}
                    </td>
                  </tr>

                  <tr>
                    <td className="py-2.5 px-3 font-medium text-bhima-muted">Statistical Significance</td>
                    <td className="py-2.5 px-3">
                      <Badge variant={aResult.trend?.is_significant ? 'success' : 'default'}>
                        p = {aResult.trend?.p_value?.toFixed(4) ?? '—'}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge variant={bResult.trend?.is_significant ? 'success' : 'default'}>
                        p = {bResult.trend?.p_value?.toFixed(4) ?? '—'}
                      </Badge>
                    </td>
                    <td className="py-2.5 px-3 text-bhima-muted">α = 0.05 threshold</td>
                  </tr>

                  <tr>
                    <td className="py-2.5 px-3 font-medium text-bhima-muted">Mean Value</td>
                    <td className="py-2.5 px-3 font-mono">
                      {Number(aResult.statistics?.mean ?? 0).toFixed(2)} {aResult.timeseries.units}
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      {Number(bResult.statistics?.mean ?? 0).toFixed(2)} {bResult.timeseries.units}
                    </td>
                    <td className="py-2.5 px-3 font-mono">
                      {(
                        Number(aResult.statistics?.mean ?? 0) - Number(bResult.statistics?.mean ?? 0)
                      ).toFixed(2)}{' '}
                      {aResult.timeseries.units}
                    </td>
                  </tr>

                  <tr>
                    <td className="py-2.5 px-3 font-medium text-bhima-muted">Observed Points</td>
                    <td className="py-2.5 px-3 font-mono">{aResult.timeseries.n_valid}</td>
                    <td className="py-2.5 px-3 font-mono">{bResult.timeseries.n_valid}</td>
                    <td className="py-2.5 px-3 font-mono text-bhima-muted">
                      {aResult.timeseries.n_valid === bResult.timeseries.n_valid
                        ? 'Identical'
                        : `${aResult.timeseries.n_valid - bResult.timeseries.n_valid}`}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>

          {/* Comparison Notes from Backend */}
          {comparisonResult?.comparison_notes && comparisonResult.comparison_notes.length > 0 && (
            <Card className="space-y-2 bg-[#F3F6F4]">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-bhima-primary">
                Scientific Comparison Synthesis
              </h4>
              <ul className="space-y-1.5 text-xs text-bhima-text leading-relaxed">
                {comparisonResult.comparison_notes.map((note, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-bhima-primary font-bold shrink-0">•</span>
                    <span>{note}</span>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      ) : (
        <EmptyState
          icon={BarChart2}
          title="Ready to Compare"
          description={`Click "Execute Regional Comparison" to query and evaluate NASA observations for ${regionA.name} and ${regionB.name}.`}
          action={
            <Button onClick={handleCompare} isLoading={isLoading}>
              Run Comparison Now
            </Button>
          }
        />
      )}
    </div>
  );
};

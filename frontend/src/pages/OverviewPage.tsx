import React from 'react';
import { Link } from 'react-router-dom';
import {
  Globe,
  BarChart2,
  MessageCircle,
  Database,
  ArrowRight,
  TrendingUp,
  Activity,
  Layers,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { useInvestigationStore } from '../store/investigationStore';
import { useHealthCheck, useDatasets } from '../api/queries';

export const OverviewPage: React.FC = () => {
  const { recentInvestigations, setRegion, setDataset, setDateRange } = useInvestigationStore();
  const { data: health, isLoading: healthLoading } = useHealthCheck();
  const { data: datasetData } = useDatasets();

  const datasets = datasetData?.datasets || [];
  const isHealthy = health?.status === 'ok';

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="bg-white border border-bhima-border rounded-lg p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-[0_1px_3px_rgba(0,0,0,0.02)]">
        <div className="max-w-2xl space-y-2">
          <div className="inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-bhima-secondary">
            <span>BHIMA Operations Dashboard</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-bhima-text">
            Earth System Intelligence Platform
          </h1>
          <p className="text-sm text-bhima-muted leading-relaxed">
            Monitor climate indices, calculate Mann-Kendall monotonic trends, and query NASA's
            calibrated satellite observations with rigorous statistical uncertainty intervals.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
          <Link to="/app/explorer">
            <Button size="md" rightIcon={<ArrowRight className="w-4 h-4" />}>
              Start Investigation
            </Button>
          </Link>
          <Link to="/app/ask">
            <Button variant="outline" size="md" leftIcon={<MessageCircle className="w-4 h-4" />}>
              Ask BHIMA
            </Button>
          </Link>
        </div>
      </div>

      {/* Quick Metrics Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card padding="md" className="space-y-1">
          <div className="flex items-center justify-between text-xs text-bhima-muted">
            <span>Indexed Datasets</span>
            <Database className="w-4 h-4 text-bhima-secondary" />
          </div>
          <div className="text-2xl font-bold text-bhima-text font-mono">
            {datasets.length || 2}
          </div>
          <div className="text-[11px] text-bhima-muted">NASA GPM IMERG & MODIS LST</div>
        </Card>

        <Card padding="md" className="space-y-1">
          <div className="flex items-center justify-between text-xs text-bhima-muted">
            <span>Primary Variables</span>
            <Layers className="w-4 h-4 text-bhima-secondary" />
          </div>
          <div className="text-2xl font-bold text-bhima-text font-mono">2</div>
          <div className="text-[11px] text-bhima-muted">Precipitation & Surface Temp</div>
        </Card>

        <Card padding="md" className="space-y-1">
          <div className="flex items-center justify-between text-xs text-bhima-muted">
            <span>Temporal Depth</span>
            <Clock className="w-4 h-4 text-bhima-secondary" />
          </div>
          <div className="text-2xl font-bold text-bhima-text font-mono">23+ Yrs</div>
          <div className="text-[11px] text-bhima-muted">2000-01 to Present Monthly</div>
        </Card>

        <Card padding="md" className="space-y-1">
          <div className="flex items-center justify-between text-xs text-bhima-muted">
            <span>Backend Engine</span>
            <Activity className="w-4 h-4 text-bhima-secondary" />
          </div>
          <div className="flex items-center gap-2 mt-1">
            {healthLoading ? (
              <LoadingSpinner size="xs" variant="accent" />
            ) : (
              <span
                className={`w-2.5 h-2.5 rounded-full ${
                  isHealthy ? 'bg-emerald-600' : 'bg-red-500'
                }`}
              />
            )}
            <span className="text-sm font-semibold text-bhima-text">
              {isHealthy ? 'Operational' : healthLoading ? 'Connecting...' : 'Offline / Degraded'}
            </span>
          </div>
          <div className="text-[11px] text-bhima-muted font-mono">
            FastAPI + Microsoft Planetary Computer Pipeline
          </div>
        </Card>
      </div>

      {/* Main Grid: Quick Actions + Recent Investigations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions (1 col) */}
        <div className="space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-bhima-secondary">
            Quick Workflows
          </h3>

          <div className="space-y-3">
            <Link to="/app/explorer" className="block group">
              <Card className="hover:border-bhima-primary/40 transition-colors p-4">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded bg-bhima-subtle group-hover:bg-bhima-primary/10 text-bhima-primary transition-colors">
                    <Globe className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-bhima-text group-hover:text-bhima-primary transition-colors">
                      Earth Explorer
                    </h4>
                    <p className="text-xs text-bhima-muted mt-1 leading-relaxed">
                      Select geographic coordinates and compute Sen's slope precipitation trends on
                      an interactive MapLibre canvas.
                    </p>
                  </div>
                </div>
              </Card>
            </Link>

            <Link to="/app/compare" className="block group">
              <Card className="hover:border-bhima-primary/40 transition-colors p-4">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded bg-bhima-subtle group-hover:bg-bhima-primary/10 text-bhima-primary transition-colors">
                    <BarChart2 className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-bhima-text group-hover:text-bhima-primary transition-colors">
                      Compare Regions
                    </h4>
                    <p className="text-xs text-bhima-muted mt-1 leading-relaxed">
                      Evaluate divergent hydrological shifts between biomes (e.g. Amazon Basin vs
                      Sahel Africa).
                    </p>
                  </div>
                </div>
              </Card>
            </Link>

            <Link to="/app/ask" className="block group">
              <Card className="hover:border-bhima-primary/40 transition-colors p-4">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded bg-bhima-subtle group-hover:bg-bhima-primary/10 text-bhima-primary transition-colors">
                    <MessageCircle className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-bhima-text group-hover:text-bhima-primary transition-colors">
                      Ask BHIMA Copilot
                    </h4>
                    <p className="text-xs text-bhima-muted mt-1 leading-relaxed">
                      Ask natural language questions. The AI agent executes analysis tools and
                      cites statistical confidence.
                    </p>
                  </div>
                </div>
              </Card>
            </Link>
          </div>
        </div>

        {/* Recent Investigations List (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-bhima-secondary">
              Recent Regional Investigations
            </h3>
            <span className="text-xs text-bhima-muted">Stored locally</span>
          </div>

          {recentInvestigations.length === 0 ? (
            <Card className="text-center py-10 space-y-3">
              <div className="w-10 h-10 rounded-full bg-bhima-subtle flex items-center justify-center mx-auto text-bhima-secondary">
                <Globe className="w-5 h-5" />
              </div>
              <div className="space-y-1">
                <h4 className="text-sm font-semibold text-bhima-text">No prior investigations</h4>
                <p className="text-xs text-bhima-muted max-w-sm mx-auto">
                  Run an analysis in the Earth Explorer to save your regional investigation here.
                </p>
              </div>
              <Link to="/app/explorer">
                <Button size="sm" variant="outline" rightIcon={<ArrowRight className="w-3.5 h-3.5" />}>
                  Launch Gujarat, India Preset
                </Button>
              </Link>
            </Card>
          ) : (
            <div className="space-y-2">
              {recentInvestigations.map((inv) => (
                <Card key={inv.id} className="p-3.5 hover:border-bhima-border transition-colors">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-bhima-text">
                          {inv.regionName}
                        </span>
                        <Badge variant="outline">{inv.datasetId}</Badge>
                        {inv.isSignificant !== undefined && (
                          <Badge variant={inv.isSignificant ? 'success' : 'default'}>
                            {inv.isSignificant ? 'Significant p<0.05' : 'Not Significant'}
                          </Badge>
                        )}
                      </div>
                      <div className="text-[11px] text-bhima-muted font-mono">
                        Period: {inv.startDate} → {inv.endDate}
                      </div>
                    </div>

                    <div className="flex items-center gap-4">
                      {inv.slope !== undefined && (
                        <div className="text-right">
                          <span className="text-[10px] text-bhima-muted uppercase block">
                            Sen's Slope
                          </span>
                          <span className="text-xs font-mono font-bold text-bhima-text">
                            {inv.slope > 0 ? `+${inv.slope.toFixed(2)}` : inv.slope.toFixed(2)} / yr
                          </span>
                        </div>
                      )}
                      <Link to="/app/explorer">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            setDateRange(inv.startDate, inv.endDate);
                            setDataset(inv.datasetId);
                          }}
                        >
                          Reload
                        </Button>
                      </Link>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

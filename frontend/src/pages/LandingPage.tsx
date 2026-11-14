import React from 'react';
import { Link } from 'react-router-dom';
import {
  Globe,
  TrendingUp,
  ShieldCheck,
  Cpu,
  ArrowRight,
  Database,
  BarChart2,
  FileCheck2,
  Layers,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';

export const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-bhima-bg text-bhima-text flex flex-col">
      {/* Top Navigation */}
      <header className="h-16 border-b border-bhima-border bg-white sticky top-0 z-30">
        <div className="max-w-[1200px] mx-auto h-full px-4 sm:px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-bhima-primary flex items-center justify-center text-white font-bold text-sm tracking-tight">
              B
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-base tracking-tight text-bhima-text leading-none">
                BHIMA
              </span>
              <span className="text-[10px] text-bhima-secondary font-medium tracking-wider uppercase mt-0.5">
                Earth System Intelligence
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <Link
              to="/app/methodology"
              className="text-xs font-medium text-bhima-muted hover:text-bhima-text hidden sm:block"
            >
              Methodology
            </Link>
            <Link
              to="/app/data-sources"
              className="text-xs font-medium text-bhima-muted hover:text-bhima-text hidden sm:block"
            >
              Data Sources
            </Link>
            <Link to="/app/explorer">
              <Button size="sm" rightIcon={<ArrowRight className="w-3.5 h-3.5" />}>
                Start Exploring
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-16 sm:py-24 border-b border-bhima-border bg-white">
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            <div className="lg:col-span-7 space-y-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-bhima-subtle border border-bhima-border text-xs font-medium text-bhima-secondary">
                <span className="w-2 h-2 rounded-full bg-bhima-primary" />
                NASA Space Apps Challenge 2026
              </div>

              <h1 className="text-3xl sm:text-5xl font-bold tracking-tight text-bhima-text leading-[1.15]">
                Investigate Earth’s Changing Climate with Scientific Rigor.
              </h1>

              <p className="text-base sm:text-lg text-bhima-muted leading-relaxed font-normal max-w-2xl">
                BHIMA connects directly to NASA Earth observation archives, executing spatial
                aggregation and non-parametric statistical testing (Mann-Kendall and Sen's Slope) to
                verify multi-decadal environmental trends without fabrication.
              </p>

              <div className="flex flex-wrap items-center gap-3 pt-2">
                <Link to="/app/explorer">
                  <Button size="lg" rightIcon={<ArrowRight className="w-4 h-4" />}>
                    Start Exploring
                  </Button>
                </Link>
                <a href="#workflow">
                  <Button variant="outline" size="lg">
                    How It Works
                  </Button>
                </a>
              </div>

              {/* Scientific transparency badge */}
              <div className="pt-4 flex items-center gap-6 text-xs text-bhima-muted border-t border-bhima-border">
                <div className="flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-bhima-primary" />
                  <span>Real NASA IMERG & MODIS</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <FileCheck2 className="w-4 h-4 text-bhima-primary" />
                  <span>p &lt; 0.05 Significance Tests</span>
                </div>
              </div>
            </div>

            {/* Clean Scientific Illustration (NO fake screenshots) */}
            <div className="lg:col-span-5">
              <div className="bg-bhima-bg border border-bhima-border rounded-xl p-5 shadow-xs relative overflow-hidden">
                <div className="flex items-center justify-between border-b border-bhima-border pb-3 mb-4 text-xs font-medium text-bhima-text">
                  <div className="flex items-center gap-2">
                    <Globe className="w-4 h-4 text-bhima-primary" />
                    <span>Spatial Bounding Box: Gujarat Basin</span>
                  </div>
                  <Badge variant="primary">2001–2023</Badge>
                </div>

                {/* SVG vector diagram representing Earth grid and trend calculation */}
                <div className="bg-white rounded border border-bhima-border p-4 aspect-[4/3] flex flex-col justify-between relative overflow-hidden">
                  <svg className="w-full h-full" viewBox="0 0 340 220" fill="none">
                    {/* Grid lines */}
                    <path d="M20 40 H320 M20 80 H320 M20 120 H320 M20 160 H320 M20 200 H320" stroke="#EEF1ED" strokeWidth="1" />
                    <path d="M60 20 V200 M120 20 V200 M180 20 V200 M240 20 V200 M300 20 V200" stroke="#EEF1ED" strokeWidth="1" />
                    
                    {/* Regional bounding box polygon */}
                    <rect x="80" y="60" width="160" height="90" fill="#31594B" fillOpacity="0.08" stroke="#31594B" strokeWidth="1.5" strokeDasharray="3 3" />
                    
                    {/* Time series curve */}
                    <path
                      d="M 30 150 Q 70 80 110 130 T 190 100 T 270 70 T 320 60"
                      fill="none"
                      stroke="#84978B"
                      strokeWidth="1.5"
                    />

                    {/* Sen's slope trendline */}
                    <line x1="30" y1="145" x2="320" y2="65" stroke="#31594B" strokeWidth="2.5" />

                    {/* Sample data nodes */}
                    <circle cx="110" cy="130" r="3.5" fill="#31594B" />
                    <circle cx="190" cy="100" r="3.5" fill="#31594B" />
                    <circle cx="270" cy="70" r="3.5" fill="#31594B" />
                  </svg>

                  <div className="pt-2 border-t border-bhima-border flex items-center justify-between text-[11px] text-bhima-muted">
                    <span>Mann-Kendall: S = +142, p = 0.018</span>
                    <span className="font-mono text-bhima-primary font-semibold">Sen's: +4.82 mm/yr</span>
                  </div>
                </div>

                <div className="mt-3 flex items-center justify-between text-[11px] text-bhima-muted">
                  <span>Sensor: GPM IMERG Final Run v07</span>
                  <span>Spatial Resolution: 0.1° × 0.1°</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* NASA Data Sources Section */}
      <section className="py-16 border-b border-bhima-border">
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <span className="text-xs font-semibold uppercase tracking-wider text-bhima-secondary">
              Authoritative Datasets
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold text-bhima-text mt-1">
              Direct NASA Earth Observation Assets
            </h2>
            <p className="text-sm text-bhima-muted mt-2">
              BHIMA operates on standardized scientific data products curated by NASA DAACs,
              preserving data lineage and spatial integrity.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <Badge variant="primary">Precipitation</Badge>
                  <h3 className="text-base font-bold text-bhima-text mt-2">
                    GPM IMERG Monthly v07
                  </h3>
                  <div className="text-xs font-mono text-bhima-muted mt-0.5">
                    Product: GPM_3IMERGM_07
                  </div>
                </div>
                <div className="text-right text-xs">
                  <span className="text-bhima-muted block">Coverage</span>
                  <span className="font-mono font-medium text-bhima-text">2000 – Present</span>
                </div>
              </div>

              <p className="text-xs text-bhima-muted leading-relaxed">
                Integrated Multi-satellitE Retrievals for GPM (IMERG) fuses precipitation estimates
                from microwave and infrared sensors calibrated with surface rain gauges across a
                global 0.1° grid.
              </p>

              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-bhima-border text-[11px]">
                <div>
                  <span className="text-bhima-muted block">Provider</span>
                  <span className="font-medium text-bhima-text">NASA GES DISC</span>
                </div>
                <div>
                  <span className="text-bhima-muted block">Spatial Res</span>
                  <span className="font-medium text-bhima-text">0.1° (~10 km)</span>
                </div>
                <div>
                  <span className="text-bhima-muted block">Units</span>
                  <span className="font-mono text-bhima-text">mm/month</span>
                </div>
              </div>
            </Card>

            <Card className="space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <Badge variant="default">Thermal</Badge>
                  <h3 className="text-base font-bold text-bhima-text mt-2">
                    MODIS Land Surface Temp
                  </h3>
                  <div className="text-xs font-mono text-bhima-muted mt-0.5">
                    Product: MOD11C3_061
                  </div>
                </div>
                <div className="text-right text-xs">
                  <span className="text-bhima-muted block">Coverage</span>
                  <span className="font-mono font-medium text-bhima-text">2000 – Present</span>
                </div>
              </div>

              <p className="text-xs text-bhima-muted leading-relaxed">
                Monthly 0.05-degree Climate Modeling Grid (CMG) Land Surface Temperature and
                Emissivity derived from the Terra Moderate Resolution Imaging Spectroradiometer.
              </p>

              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-bhima-border text-[11px]">
                <div>
                  <span className="text-bhima-muted block">Provider</span>
                  <span className="font-medium text-bhima-text">NASA LP DAAC</span>
                </div>
                <div>
                  <span className="text-bhima-muted block">Spatial Res</span>
                  <span className="font-medium text-bhima-text">0.05° (~5.6 km)</span>
                </div>
                <div>
                  <span className="text-bhima-muted block">Units</span>
                  <span className="font-mono text-bhima-text">Kelvin / °C</span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="workflow" className="py-16 border-b border-bhima-border bg-white">
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <span className="text-xs font-semibold uppercase tracking-wider text-bhima-secondary">
              Workflow
            </span>
            <h2 className="text-2xl sm:text-3xl font-bold text-bhima-text mt-1">
              End-to-End Investigation Architecture
            </h2>
            <p className="text-sm text-bhima-muted mt-2">
              A transparent 4-stage pipeline from coordinate definition to peer-grade statistical verification.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="p-4 bg-bhima-bg rounded-lg border border-bhima-border space-y-2">
              <div className="w-8 h-8 rounded bg-bhima-primary/10 text-bhima-primary flex items-center justify-center font-bold text-xs">
                01
              </div>
              <h4 className="text-sm font-semibold text-bhima-text">Define Geometry</h4>
              <p className="text-xs text-bhima-muted leading-relaxed">
                Specify bounding coordinates [min_lon, min_lat, max_lon, max_lat] or choose from presets like Gujarat, Amazon, or Sahel.
              </p>
            </div>

            <div className="p-4 bg-bhima-bg rounded-lg border border-bhima-border space-y-2">
              <div className="w-8 h-8 rounded bg-bhima-primary/10 text-bhima-primary flex items-center justify-center font-bold text-xs">
                02
              </div>
              <h4 className="text-sm font-semibold text-bhima-text">Extract Gridded Pixels</h4>
              <p className="text-xs text-bhima-muted leading-relaxed">
                Query NASA OPeNDAP or HDF5 arrays to perform area-weighted spatial averaging across the bounding polygon.
              </p>
            </div>

            <div className="p-4 bg-bhima-bg rounded-lg border border-bhima-border space-y-2">
              <div className="w-8 h-8 rounded bg-bhima-primary/10 text-bhima-primary flex items-center justify-center font-bold text-xs">
                03
              </div>
              <h4 className="text-sm font-semibold text-bhima-text">Mann-Kendall & Sen's</h4>
              <p className="text-xs text-bhima-muted leading-relaxed">
                Calculate Kendall's tau rank correlation and Sen’s median pairwise slope without assuming normal data distribution.
              </p>
            </div>

            <div className="p-4 bg-bhima-bg rounded-lg border border-bhima-border space-y-2">
              <div className="w-8 h-8 rounded bg-bhima-primary/10 text-bhima-primary flex items-center justify-center font-bold text-xs">
                04
              </div>
              <h4 className="text-sm font-semibold text-bhima-text">Intelligent Copilot</h4>
              <p className="text-xs text-bhima-muted leading-relaxed">
                Interact with the Ask BHIMA agent to execute comparisons, inspect anomalies, and interpret climatological context.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Features: 3 Pillars */}
      <section className="py-16 border-b border-bhima-border">
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card className="space-y-3">
              <div className="w-9 h-9 rounded bg-bhima-subtle flex items-center justify-center text-bhima-primary">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-semibold text-bhima-text">
                Uncompromising Scientific Integrity
              </h3>
              <p className="text-xs text-bhima-muted leading-relaxed">
                No hallucinated values, no synthetic fills without logging. If data is missing or
                below quality thresholds, coverage fractions and valid pixel counts are explicitly
                disclosed.
              </p>
            </Card>

            <Card className="space-y-3">
              <div className="w-9 h-9 rounded bg-bhima-subtle flex items-center justify-center text-bhima-primary">
                <BarChart2 className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-semibold text-bhima-text">
                Dual Regional Comparison
              </h3>
              <p className="text-xs text-bhima-muted leading-relaxed">
                Benchmark contrasting climate zones side-by-side. Compare the drying trend of the
                Sahel against the precipitation shifts in the Amazon basin over identical temporal
                windows.
              </p>
            </Card>

            <Card className="space-y-3">
              <div className="w-9 h-9 rounded bg-bhima-subtle flex items-center justify-center text-bhima-primary">
                <Cpu className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-semibold text-bhima-text">
                Tool-Calling Earth Science Copilot
              </h3>
              <p className="text-xs text-bhima-muted leading-relaxed">
                Ask BHIMA utilizes structured tool calling to invoke backend time series routines,
                inspect metadata, and report statistical findings with exact p-values.
              </p>
            </Card>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 bg-white mt-auto border-t border-bhima-border">
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6 flex flex-col md:flex-row items-center justify-between gap-6 text-xs text-bhima-muted">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded bg-bhima-primary text-white flex items-center justify-center font-bold text-xs">
              B
            </div>
            <div>
              <span className="font-semibold text-bhima-text">BHIMA</span> — Earth System Intelligence
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-6">
            <Link to="/app/overview" className="hover:text-bhima-text">Platform</Link>
            <Link to="/app/explorer" className="hover:text-bhima-text">Explorer</Link>
            <Link to="/app/compare" className="hover:text-bhima-text">Compare</Link>
            <Link to="/app/data-sources" className="hover:text-bhima-text">Data Sources</Link>
            <Link to="/app/methodology" className="hover:text-bhima-text">Methodology</Link>
          </div>

          <div className="text-right">
            <div>NASA Space Apps Challenge 2026</div>
            <div className="text-[11px] text-bhima-secondary">Data: NASA GES DISC & LP DAAC</div>
          </div>
        </div>
      </footer>
    </div>
  );
};

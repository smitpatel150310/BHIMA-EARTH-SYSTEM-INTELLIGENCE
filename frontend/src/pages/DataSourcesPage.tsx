import React from 'react';
import { useDatasets } from '../api/queries';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { LoadingState } from '../components/ui/LoadingState';
import { Database, ExternalLink, ShieldCheck, AlertCircle, Layers, Calendar, MapPin } from 'lucide-react';

export const DataSourcesPage: React.FC = () => {
  const { data: datasetData, isLoading } = useDatasets();

  const fallbackDatasets = [
    {
      id: 'GPM_3IMERGM_07',
      name: 'NASA GPM IMERG Precipitation (Microsoft Planetary Computer STAC)',
      provider: 'NASA GES DISC / Microsoft Planetary Computer',
      product_id: 'gpm-imerg-hhr',
      source_url: 'https://planetarycomputer.microsoft.com/dataset/gpm-imerg-hhr',
      spatial_resolution: '0.1° × 0.1° (~10 km at equator)',
      temporal_resolution: 'Monthly (aggregated from half-hourly HHR observations)',
      units: 'mm/month (accumulated from calibrated rate in mm/hr)',
      variable: 'precipitationCal',
      coverage_start: '2000-06-01',
      coverage_end: '2021-05-31',
      description:
        'NASA Integrated Multi-satellitE Retrievals for GPM (IMERG) calibrated precipitation estimates (HHR) hosted on Microsoft Planetary Computer. Preprocessed and persisted for high-speed regional queries without requiring Earthdata credentials.',
      limitations: [
        'Cloud-native Earth observation archive on Microsoft Planetary Computer (June 2000 to May 2021)',
        'Gauge calibration introduces regional latency (~3.5 months for Final Run)',
        'Reduced sensitivity over frozen, snow-covered, or complex high-altitude mountain terrain',
        'Spatial averaging across coastal boundary cells blends land and oceanic rainfall characteristics',
      ],
    },
    {
      id: 'MOD11C3_061',
      name: 'MODIS/Terra Land Surface Temperature/Emissivity Monthly L3 Global 0.05Deg CMG V061',
      provider: 'NASA Land Processes Distributed Active Archive Center (LP DAAC)',
      product_id: 'MOD11C3_061',
      source_url: 'https://lpdaac.usgs.gov/products/mod11c3v061/',
      spatial_resolution: '0.05° (~5.6 km at equator)',
      temporal_resolution: 'Monthly (2000-03 to present)',
      units: 'Kelvin (K) / degrees Celsius (°C)',
      variable: 'LST_Day_CMG',
      coverage_start: '2000-03-01',
      coverage_end: 'Present',
      description:
        'The MOD11C3 Version 6.1 product provides monthly composited land surface temperature (LST) and emissivity data on a 0.05 degree climate modeling grid (CMG). Composed by averaging the daily 0.05-degree CMG LST cells over each calendar month.',
      limitations: [
        'Cloud-cover occlusion masks optical/thermal infrared retrievals',
        'Thermal skin temperature represents radiometric surface, not 2-meter air temperature',
        'Emissivity errors over arid sand dunes and dynamic seasonal snow boundaries',
      ],
    },
  ];

  const datasets = datasetData?.datasets && datasetData.datasets.length > 0
    ? datasetData.datasets
    : fallbackDatasets;

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div className="border-b border-bhima-border pb-4">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-bhima-secondary mb-1">
          <Database className="w-3.5 h-3.5 text-bhima-primary" />
          <span>Scientific Data Lineage</span>
        </div>
        <h2 className="text-2xl font-bold text-bhima-text">NASA Earth Observation Data Sources</h2>
        <p className="text-xs text-bhima-muted mt-1 leading-relaxed">
          Comprehensive specifications, data providers, sensor architectures, and calibration constraints.
        </p>
      </div>

      {/* Dataset Catalog */}
      <div className="space-y-6">
        {datasets.map((dataset) => (
          <Card key={dataset.id} className="p-6 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-bhima-border pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant="primary">{dataset.variable}</Badge>
                  <span className="text-xs font-mono text-bhima-secondary">{dataset.id}</span>
                </div>
                <h3 className="text-base font-bold text-bhima-text">{dataset.name}</h3>
                <p className="text-xs text-bhima-muted">{dataset.provider}</p>
              </div>

              {dataset.source_url && (
                <a
                  href={dataset.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-medium text-bhima-primary hover:underline shrink-0"
                >
                  <span>NASA Product Portal</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>

            {/* Description */}
            <p className="text-xs text-bhima-text leading-relaxed">{dataset.description}</p>

            {/* Specifications Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-bhima-subtle/50 p-3.5 rounded-md border border-bhima-border text-xs">
              <div>
                <div className="text-[10px] text-bhima-muted uppercase flex items-center gap-1">
                  <Layers className="w-3 h-3 text-bhima-secondary" /> Spatial Resolution
                </div>
                <div className="font-medium text-bhima-text mt-1">{dataset.spatial_resolution}</div>
              </div>

              <div>
                <div className="text-[10px] text-bhima-muted uppercase flex items-center gap-1">
                  <Calendar className="w-3 h-3 text-bhima-secondary" /> Temporal Cadence
                </div>
                <div className="font-medium text-bhima-text mt-1">{dataset.temporal_resolution}</div>
              </div>

              <div>
                <div className="text-[10px] text-bhima-muted uppercase">Physical Units</div>
                <div className="font-mono font-medium text-bhima-text mt-1">{dataset.units}</div>
              </div>

              <div>
                <div className="text-[10px] text-bhima-muted uppercase">Temporal Bounds</div>
                <div className="font-medium text-bhima-text mt-1">
                  {dataset.coverage_start} → {dataset.coverage_end}
                </div>
              </div>
            </div>

            {/* Known Limitations */}
            {dataset.limitations && dataset.limitations.length > 0 && (
              <div className="space-y-2 pt-2">
                <span className="text-[11px] font-semibold text-bhima-secondary uppercase tracking-wider flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
                  Known Limitations & Caveats
                </span>
                <ul className="space-y-1 text-xs text-bhima-muted">
                  {dataset.limitations.map((lim, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-bhima-secondary shrink-0">•</span>
                      <span>{lim}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Card>
        ))}
      </div>

      {/* Disclaimers & Rigor Statement */}
      <Card className="bg-[#F3F6F4] border-bhima-border space-y-3">
        <div className="flex items-center gap-2 text-bhima-primary font-bold text-xs uppercase tracking-wider">
          <ShieldCheck className="w-4 h-4" />
          <span>Scientific Data Ethics & Integrity Policy</span>
        </div>
        <p className="text-xs text-bhima-muted leading-relaxed">
          BHIMA adheres to strict NASA Earth Science Data and Information System (ESDIS) standards.
          All observations are extracted from calibrated data streams without synthetic filling,
          imputation, or artificial enhancement. When quality masks or missing orbits occur, they
          are explicitly propagated into the uncertainty reporting.
        </p>
      </Card>
    </div>
  );
};

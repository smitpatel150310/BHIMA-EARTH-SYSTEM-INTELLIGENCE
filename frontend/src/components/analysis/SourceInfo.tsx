import React, { useState } from 'react';
import { Card } from '../ui/Card';
import { TimeSeriesData } from '../../types';
import { Button } from '../ui/Button';
import { Database, ChevronDown, ChevronUp, Download, ShieldCheck, AlertTriangle } from 'lucide-react';

export interface SourceInfoProps {
  timeseries: TimeSeriesData;
  methodology?: string;
}

export const SourceInfo: React.FC<SourceInfoProps> = ({ timeseries, methodology }) => {
  const [showNotes, setShowNotes] = useState(false);

  const handleDownloadCSV = () => {
    const regionName = typeof timeseries.region === 'string'
      ? timeseries.region
      : timeseries.region?.name || 'region';

    const headers = ['date', 'value', 'units', 'dataset_id', 'valid_pixels', 'coverage_fraction'];
    const rows = timeseries.data.map((d) => [
      d.date,
      d.value !== null ? d.value : '',
      timeseries.units,
      timeseries.dataset_id,
      d.valid_pixels ?? '',
      d.coverage_fraction ?? '',
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute(
      'download',
      `bhima_${timeseries.dataset_id}_${regionName.toLowerCase().replace(/[^a-z0-9]/g, '_')}_${timeseries.start_date}_${timeseries.end_date}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Card className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-bhima-border pb-3">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-bhima-primary" />
          <h4 className="text-sm font-semibold text-bhima-text">Scientific Source & Lineage</h4>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={handleDownloadCSV}
          leftIcon={<Download className="w-3.5 h-3.5" />}
        >
          Export Raw CSV
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
        <div className="space-y-1">
          <div className="text-[11px] text-bhima-muted">Dataset Identifier & Provider</div>
          <div className="font-mono font-medium text-bhima-text">{timeseries.dataset_id}</div>
          <div className="text-[11px] text-bhima-muted">{timeseries.source_description}</div>
          {timeseries.data_source && (
            <div className="text-[11px] font-medium text-emerald-800 bg-emerald-50 border border-emerald-200 rounded px-2 py-1 mt-1">
              Source: {timeseries.data_source}
            </div>
          )}
        </div>

        <div className="space-y-1">
          <div className="text-[11px] text-bhima-muted">Temporal Range & Cadence</div>
          <div className="font-medium text-bhima-text">
            {timeseries.start_date} to {timeseries.end_date} ({timeseries.temporal_resolution})
          </div>
          <div className="text-[11px] text-bhima-muted font-mono">
            Retrieved: {new Date(timeseries.retrieval_timestamp || Date.now()).toUTCString()}
          </div>
          <div className="text-[11px] font-semibold text-bhima-primary mt-1">
            Data Status: {timeseries.data_provenance || 'REAL_NASA_DATA'}
          </div>
        </div>
      </div>

      {methodology && (
        <div className="text-xs bg-bhima-subtle/50 p-2.5 rounded border border-bhima-border text-bhima-muted leading-relaxed">
          <strong className="text-bhima-text font-medium">Pipeline: </strong>
          {methodology}
        </div>
      )}

      {/* Validation issues if any */}
      {timeseries.validation_issues && timeseries.validation_issues.length > 0 && (
        <div className="p-2.5 rounded bg-amber-50 border border-amber-200 text-xs text-amber-900 space-y-1">
          <div className="flex items-center gap-1.5 font-semibold">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            Validation Notes
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-[11px]">
            {timeseries.validation_issues.map((iss, i) => (
              <li key={i}>{iss}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Collapsible processing notes */}
      {timeseries.processing_notes && timeseries.processing_notes.length > 0 && (
        <div className="pt-2 border-t border-bhima-border">
          <button
            type="button"
            onClick={() => setShowNotes(!showNotes)}
            className="flex items-center justify-between w-full text-xs font-medium text-bhima-muted hover:text-bhima-text"
          >
            <span className="flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-bhima-secondary" />
              Quality & Processing Logs ({timeseries.processing_notes.length})
            </span>
            {showNotes ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          {showNotes && (
            <ul className="mt-2 space-y-1 text-[11px] text-bhima-muted font-mono bg-bhima-subtle/40 p-2.5 rounded border border-bhima-border">
              {timeseries.processing_notes.map((note, index) => (
                <li key={index} className="flex items-start gap-1.5">
                  <span className="text-bhima-secondary shrink-0">•</span>
                  <span>{note}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
};

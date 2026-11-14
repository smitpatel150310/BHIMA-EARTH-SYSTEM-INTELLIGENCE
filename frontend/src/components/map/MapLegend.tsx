import React from 'react';
import { Layers, Info } from 'lucide-react';

export interface MapLegendProps {
  spatialResolution?: string;
  variableName?: string;
  units?: string;
  className?: string;
}

export const MapLegend: React.FC<MapLegendProps> = ({
  spatialResolution = '0.1° × 0.1° (~10 km)',
  variableName = 'Precipitation Rate',
  units = 'mm/month',
  className = '',
}) => {
  return (
    <div
      className={`bg-white/95 backdrop-blur-xs border border-bhima-border rounded-md p-3 text-xs shadow-xs space-y-2 ${className}`}
    >
      <div className="flex items-center justify-between border-b border-bhima-border pb-1.5">
        <span className="font-semibold text-bhima-text flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-bhima-secondary" />
          Layer Specs
        </span>
        <span className="text-[10px] font-mono text-bhima-muted">EPSG:4326</span>
      </div>

      <div className="space-y-1 text-[11px]">
        <div className="flex justify-between">
          <span className="text-bhima-muted">Variable:</span>
          <span className="font-medium text-bhima-text">{variableName}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-bhima-muted">Units:</span>
          <span className="font-mono text-bhima-text">{units}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-bhima-muted">Spatial Grid:</span>
          <span className="font-mono text-bhima-text">{spatialResolution}</span>
        </div>
      </div>

      <div className="pt-1.5 border-t border-bhima-border">
        <div className="text-[10px] text-bhima-muted uppercase tracking-wider mb-1">
          Sen's Slope Trend Direction
        </div>
        <div className="flex items-center gap-3 text-[10px]">
          <span className="inline-flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#387259]" />
            Increasing
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-[#A8423F]" />
            Decreasing
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-bhima-secondary" />
            No Trend
          </span>
        </div>
      </div>
    </div>
  );
};

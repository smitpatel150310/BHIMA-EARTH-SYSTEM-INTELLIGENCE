import React, { useState } from 'react';
import { RegionRequest } from '../../types';
import { REGION_PRESETS } from '../../store/investigationStore';
import { MapPin, Sliders, Check } from 'lucide-react';

export interface RegionSelectorProps {
  value: RegionRequest | null;
  onChange: (region: RegionRequest) => void;
  label?: string;
}

export const RegionSelector: React.FC<RegionSelectorProps> = ({
  value,
  onChange,
  label = 'Target Region',
}) => {
  const [isCustom, setIsCustom] = useState(false);
  const [customForm, setCustomForm] = useState<RegionRequest>({
    name: value?.name || 'Custom Bounding Box',
    min_lon: value?.min_lon ?? 68.1,
    max_lon: value?.max_lon ?? 74.5,
    min_lat: value?.min_lat ?? 20.1,
    max_lat: value?.max_lat ?? 24.7,
  });

  const handlePresetSelect = (presetKey: string) => {
    const preset = REGION_PRESETS[presetKey];
    if (preset) {
      onChange(preset);
      setCustomForm(preset);
    }
  };

  const handleCustomFieldChange = (field: keyof RegionRequest, val: string | number) => {
    const updated = {
      ...customForm,
      [field]: typeof val === 'string' && field !== 'name' ? parseFloat(val) || 0 : val,
    };
    setCustomForm(updated);
    onChange(updated);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold text-bhima-text uppercase tracking-wider flex items-center gap-1.5">
          <MapPin className="w-3.5 h-3.5 text-bhima-primary" />
          {label}
        </label>
        <button
          type="button"
          onClick={() => setIsCustom(!isCustom)}
          className="text-[11px] font-medium text-bhima-primary hover:underline flex items-center gap-1"
        >
          <Sliders className="w-3 h-3" />
          {isCustom ? 'Pick Preset' : 'Custom Coords'}
        </button>
      </div>

      {!isCustom ? (
        <div>
          <select
            value={value?.name || ''}
            onChange={(e) => handlePresetSelect(e.target.value)}
            className="w-full bg-white border border-bhima-border rounded-md px-3 py-2 text-xs font-medium text-bhima-text focus:outline-none focus:ring-1 focus:ring-bhima-primary cursor-pointer"
          >
            {Object.keys(REGION_PRESETS).map((presetName) => (
              <option key={presetName} value={presetName}>
                {presetName}
              </option>
            ))}
          </select>
          {value && (
            <div className="mt-2 text-[11px] font-mono text-bhima-muted flex items-center justify-between bg-bhima-subtle/70 px-2.5 py-1.5 rounded border border-bhima-border">
              <span>LON: [{value.min_lon}°, {value.max_lon}°]</span>
              <span>LAT: [{value.min_lat}°, {value.max_lat}°]</span>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-bhima-subtle/50 p-3 rounded-md border border-bhima-border space-y-2.5">
          <div>
            <label className="text-[11px] font-medium text-bhima-muted block mb-1">
              Region Label
            </label>
            <input
              type="text"
              value={customForm.name}
              onChange={(e) => handleCustomFieldChange('name', e.target.value)}
              className="w-full bg-white border border-bhima-border rounded px-2.5 py-1 text-xs text-bhima-text focus:ring-1 focus:ring-bhima-primary focus:outline-none"
              placeholder="e.g. Nile Delta, Egypt"
            />
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px]">
            <div>
              <label className="text-bhima-muted block mb-0.5">Min Lon (°)</label>
              <input
                type="number"
                step="0.1"
                min="-180"
                max="180"
                value={customForm.min_lon}
                onChange={(e) => handleCustomFieldChange('min_lon', e.target.value)}
                className="w-full bg-white border border-bhima-border rounded px-2 py-1 text-xs font-mono"
              />
            </div>
            <div>
              <label className="text-bhima-muted block mb-0.5">Max Lon (°)</label>
              <input
                type="number"
                step="0.1"
                min="-180"
                max="180"
                value={customForm.max_lon}
                onChange={(e) => handleCustomFieldChange('max_lon', e.target.value)}
                className="w-full bg-white border border-bhima-border rounded px-2 py-1 text-xs font-mono"
              />
            </div>
            <div>
              <label className="text-bhima-muted block mb-0.5">Min Lat (°)</label>
              <input
                type="number"
                step="0.1"
                min="-90"
                max="90"
                value={customForm.min_lat}
                onChange={(e) => handleCustomFieldChange('min_lat', e.target.value)}
                className="w-full bg-white border border-bhima-border rounded px-2 py-1 text-xs font-mono"
              />
            </div>
            <div>
              <label className="text-bhima-muted block mb-0.5">Max Lat (°)</label>
              <input
                type="number"
                step="0.1"
                min="-90"
                max="90"
                value={customForm.max_lat}
                onChange={(e) => handleCustomFieldChange('max_lat', e.target.value)}
                className="w-full bg-white border border-bhima-border rounded px-2 py-1 text-xs font-mono"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

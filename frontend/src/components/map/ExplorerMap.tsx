import React, { useEffect, useRef, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import { RegionRequest } from '../../types';
import { Maximize2, ZoomIn, ZoomOut } from 'lucide-react';
import { LoadingSpinner } from '../ui/LoadingSpinner';

export interface ExplorerMapProps {
  region: RegionRequest | null;
  onRegionChange?: (region: RegionRequest) => void;
  className?: string;
  interactive?: boolean;
}

export const ExplorerMap: React.FC<ExplorerMapProps> = ({
  region,
  onRegionChange,
  className = '',
  interactive = true,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const sourceLoadedRef = useRef(false);
  const [isMapLoading, setIsMapLoading] = useState(true);

  // Initialize MapLibre
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: [
              'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            ],
            tileSize: 256,
            attribution:
              '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors',
          },
        },
        layers: [
          {
            id: 'osm-tiles',
            type: 'raster',
            source: 'osm',
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: region
        ? [(region.min_lon + region.max_lon) / 2, (region.min_lat + region.max_lat) / 2]
        : [71.3, 22.4], // Gujarat default
      zoom: 3.5,
      attributionControl: false,
    });

    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');

    map.on('load', () => {
      sourceLoadedRef.current = true;
      setIsMapLoading(false);

      // Add GeoJSON source for bounding box rectangle
      map.addSource('selected-region', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: [],
        },
      });

      // Fill layer
      map.addLayer({
        id: 'selected-region-fill',
        type: 'fill',
        source: 'selected-region',
        paint: {
          'fill-color': '#31594B',
          'fill-opacity': 0.18,
        },
      });

      // Outline layer
      map.addLayer({
        id: 'selected-region-line',
        type: 'line',
        source: 'selected-region',
        paint: {
          'line-color': '#31594B',
          'line-width': 2,
          'line-dasharray': [2, 1],
        },
      });

      if (region) {
        updateBoundingBox(region);
      }
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      sourceLoadedRef.current = false;
    };
  }, []);

  // Update region box whenever region prop changes
  useEffect(() => {
    if (mapRef.current && sourceLoadedRef.current) {
      updateBoundingBox(region);
    }
  }, [region]);

  const updateBoundingBox = (r: RegionRequest | null) => {
    const map = mapRef.current;
    if (!map) return;

    const source = map.getSource('selected-region') as maplibregl.GeoJSONSource | undefined;
    if (!source) return;

    if (!r) {
      source.setData({
        type: 'FeatureCollection',
        features: [],
      });
      return;
    }

    const coordinates = [
      [
        [r.min_lon, r.min_lat],
        [r.max_lon, r.min_lat],
        [r.max_lon, r.max_lat],
        [r.min_lon, r.max_lat],
        [r.min_lon, r.min_lat],
      ],
    ];

    source.setData({
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          properties: { name: r.name },
          geometry: {
            type: 'Polygon',
            coordinates,
          },
        },
      ],
    });

    try {
      map.fitBounds(
        [
          [r.min_lon, r.min_lat],
          [r.max_lon, r.max_lat],
        ],
        {
          padding: 40,
          maxZoom: 7,
          duration: 900,
        }
      );
    } catch {
      // ignore
    }
  };

  const handleZoomIn = () => mapRef.current?.zoomIn();
  const handleZoomOut = () => mapRef.current?.zoomOut();
  const handleFit = () => {
    if (region && mapRef.current) {
      updateBoundingBox(region);
    } else {
      mapRef.current?.flyTo({ center: [0, 20], zoom: 1.5 });
    }
  };

  return (
    <div className={`relative w-full h-full min-h-[380px] bg-bhima-subtle rounded-lg overflow-hidden border border-bhima-border ${className}`}>
      <div ref={mapContainerRef} className="w-full h-full min-h-[380px]" />
      
      {/* Basemap Loading Overlay */}
      {isMapLoading && (
        <div className="absolute inset-0 bg-bhima-subtle/50 backdrop-blur-[1px] flex items-center justify-center z-10 pointer-events-none">
          <div className="bg-white/95 border border-bhima-border rounded-md px-3.5 py-2 text-xs font-medium text-bhima-text shadow-xs flex items-center gap-2">
            <LoadingSpinner size="sm" variant="accent" />
            <span>Loading Cartographic Basemap...</span>
          </div>
        </div>
      )}

      {/* Floating Controls */}
      <div className="absolute top-3 right-3 flex flex-col gap-1 z-10">
        <button
          onClick={handleZoomIn}
          className="w-8 h-8 bg-white border border-bhima-border rounded shadow-xs flex items-center justify-center text-bhima-text hover:bg-bhima-subtle"
          title="Zoom in"
          aria-label="Zoom in"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={handleZoomOut}
          className="w-8 h-8 bg-white border border-bhima-border rounded shadow-xs flex items-center justify-center text-bhima-text hover:bg-bhima-subtle"
          title="Zoom out"
          aria-label="Zoom out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={handleFit}
          className="w-8 h-8 bg-white border border-bhima-border rounded shadow-xs flex items-center justify-center text-bhima-text hover:bg-bhima-subtle"
          title="Fit to bounding box"
          aria-label="Fit to region"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>

      {/* Coordinate HUD overlay */}
      {region && (
        <div className="absolute bottom-3 left-3 bg-white/95 backdrop-blur-xs border border-bhima-border rounded px-3 py-1.5 text-[11px] font-mono text-bhima-muted shadow-xs z-10 pointer-events-none">
          <span className="font-semibold text-bhima-text">{region.name}: </span>
          [{region.min_lon.toFixed(2)}°, {region.min_lat.toFixed(2)}°] → [
          {region.max_lon.toFixed(2)}°, {region.max_lat.toFixed(2)}°]
        </div>
      )}
    </div>
  );
};

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
  cachedObservationsCount?: number;
}

export const ExplorerMap: React.FC<ExplorerMapProps> = ({
  region,
  onRegionChange,
  className = '',
  interactive = true,
  cachedObservationsCount,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const isLoadedRef = useRef(false);
  const regionRef = useRef<RegionRequest | null>(region);
  const [isMapLoading, setIsMapLoading] = useState(true);

  // Keep latest region in ref to prevent stale closures
  useEffect(() => {
    regionRef.current = region;
  }, [region]);

  /**
   * Helper to ensure GeoJSON sources and rendering layers exist on the map.
   * Uses high-contrast multi-layer styling:
   * 1. Translucent fill (#0284C7, opacity 0.20)
   * 2. High-contrast white casing/halo (width 6px) to ensure visibility over green vegetation / dark satellite
   * 3. Vivid foreground border (#0284C7, width 3px)
   * 4. Corner vertex anchor circles (radius 5px, white with border)
   */
  const ensureSourcesAndLayers = (map: maplibregl.Map) => {
    // 1. Polygon source
    if (!map.getSource('selected-region')) {
      map.addSource('selected-region', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: [],
        },
      });
    }

    // 2. Corner vertices source
    if (!map.getSource('selected-region-corners')) {
      map.addSource('selected-region-corners', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: [],
        },
      });
    }

    // 3. Fill layer
    if (!map.getLayer('selected-region-fill')) {
      map.addLayer({
        id: 'selected-region-fill',
        type: 'fill',
        source: 'selected-region',
        paint: {
          'fill-color': '#0284C7',
          'fill-opacity': 0.20,
        },
      });
    }

    // 4. White halo / casing line (ensures clear visibility on green terrain, oceans, and deserts)
    if (!map.getLayer('selected-region-casing')) {
      map.addLayer({
        id: 'selected-region-casing',
        type: 'line',
        source: 'selected-region',
        paint: {
          'line-color': '#FFFFFF',
          'line-width': 6,
          'line-opacity': 0.9,
        },
      });
    }

    // 5. Vivid scientific primary line
    if (!map.getLayer('selected-region-line')) {
      map.addLayer({
        id: 'selected-region-line',
        type: 'line',
        source: 'selected-region',
        paint: {
          'line-color': '#0284C7',
          'line-width': 3,
        },
      });
    }

    // 6. Corner vertex markers
    if (!map.getLayer('selected-region-corners')) {
      map.addLayer({
        id: 'selected-region-corners',
        type: 'circle',
        source: 'selected-region-corners',
        paint: {
          'circle-radius': 5,
          'circle-color': '#FFFFFF',
          'circle-stroke-width': 2.5,
          'circle-stroke-color': '#0284C7',
        },
      });
    }
  };

  /**
   * Constructs GeoJSON features for the bounding box, correctly handling:
   * - standard bounding boxes (min_lon <= max_lon)
   * - antimeridian-crossing bounding boxes (min_lon > max_lon)
   * - corner vertex points
   */
  const buildRegionFeatures = (r: RegionRequest) => {
    const min_lon = Number(r.min_lon);
    const max_lon = Number(r.max_lon);
    const min_lat = Number(r.min_lat);
    const max_lat = Number(r.max_lat);

    // Corner points
    const cornerFeatures: any[] = [
      {
        type: 'Feature',
        properties: { corner: 'sw' },
        geometry: { type: 'Point', coordinates: [min_lon, min_lat] },
      },
      {
        type: 'Feature',
        properties: { corner: 'se' },
        geometry: { type: 'Point', coordinates: [max_lon, min_lat] },
      },
      {
        type: 'Feature',
        properties: { corner: 'ne' },
        geometry: { type: 'Point', coordinates: [max_lon, max_lat] },
      },
      {
        type: 'Feature',
        properties: { corner: 'nw' },
        geometry: { type: 'Point', coordinates: [min_lon, max_lat] },
      },
    ];

    let polygonFeature: any;

    if (min_lon > max_lon) {
      // Crosses antimeridian: create MultiPolygon split at 180 / -180
      polygonFeature = {
        type: 'Feature',
        properties: { name: r.name },
        geometry: {
          type: 'MultiPolygon',
          coordinates: [
            [
              [
                [min_lon, min_lat],
                [180, min_lat],
                [180, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat],
              ],
            ],
            [
              [
                [-180, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [-180, max_lat],
                [-180, min_lat],
              ],
            ],
          ],
        },
      };
    } else {
      // Standard bounding box (RFC 7946 counter-clockwise exterior ring)
      polygonFeature = {
        type: 'Feature',
        properties: { name: r.name },
        geometry: {
          type: 'Polygon',
          coordinates: [
            [
              [min_lon, min_lat],
              [max_lon, min_lat],
              [max_lon, max_lat],
              [min_lon, max_lat],
              [min_lon, min_lat],
            ],
          ],
        },
      };
    }

    return {
      polygonGeoJson: {
        type: 'FeatureCollection' as const,
        features: [polygonFeature],
      },
      cornersGeoJson: {
        type: 'FeatureCollection' as const,
        features: cornerFeatures,
      },
    };
  };

  const updateBoundingBox = (r: RegionRequest | null, animate = true) => {
    const map = mapRef.current;
    if (!map) return;

    ensureSourcesAndLayers(map);

    const polySource = map.getSource('selected-region') as maplibregl.GeoJSONSource | undefined;
    const cornerSource = map.getSource('selected-region-corners') as maplibregl.GeoJSONSource | undefined;

    if (!r) {
      polySource?.setData({ type: 'FeatureCollection', features: [] });
      cornerSource?.setData({ type: 'FeatureCollection', features: [] });
      return;
    }

    const { polygonGeoJson, cornersGeoJson } = buildRegionFeatures(r);
    polySource?.setData(polygonGeoJson);
    cornerSource?.setData(cornersGeoJson);

    if (animate) {
      try {
        const min_lon = Number(r.min_lon);
        const max_lon = Number(r.max_lon);
        const min_lat = Number(r.min_lat);
        const max_lat = Number(r.max_lat);

        if (min_lon <= max_lon) {
          map.fitBounds(
            [
              [min_lon, min_lat],
              [max_lon, max_lat],
            ],
            {
              padding: 45,
              maxZoom: 7,
              duration: 800,
            }
          );
        } else {
          // Antimeridian crossing center
          const midLat = (min_lat + max_lat) / 2;
          map.flyTo({ center: [180, midLat], zoom: 3, duration: 800 });
        }
      } catch (err) {
        // Safe fallback if coordinates degenerate
        console.warn('[ExplorerMap] fitBounds notice:', err);
      }
    }
  };

  // Initialize MapLibre
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const initialRegion = regionRef.current;
    const initialCenter: [number, number] = initialRegion
      ? [(Number(initialRegion.min_lon) + Number(initialRegion.max_lon)) / 2, (Number(initialRegion.min_lat) + Number(initialRegion.max_lat)) / 2]
      : [71.3, 22.4];

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
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
      center: initialCenter,
      zoom: 3.5,
      attributionControl: false,
    });

    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');

    const handleMapReady = () => {
      isLoadedRef.current = true;
      setIsMapLoading(false);
      ensureSourcesAndLayers(map);
      if (regionRef.current) {
        updateBoundingBox(regionRef.current, false);
      }
    };

    map.on('load', handleMapReady);

    // Catch style reloads or raster refresh
    map.on('styledata', () => {
      if (isLoadedRef.current) {
        ensureSourcesAndLayers(map);
        if (regionRef.current) {
          updateBoundingBox(regionRef.current, false);
        }
      }
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      isLoadedRef.current = false;
    };
  }, []);

  // Update region box whenever region prop changes
  useEffect(() => {
    if (mapRef.current && isLoadedRef.current) {
      updateBoundingBox(region, true);
    }
  }, [region]);

  // Auto-resize map when container layout shifts
  useEffect(() => {
    if (!mapContainerRef.current) return;
    const observer = new ResizeObserver(() => {
      mapRef.current?.resize();
    });
    observer.observe(mapContainerRef.current);
    return () => observer.disconnect();
  }, []);

  const handleZoomIn = () => mapRef.current?.zoomIn();
  const handleZoomOut = () => mapRef.current?.zoomOut();
  const handleFit = () => {
    if (region && mapRef.current) {
      updateBoundingBox(region, true);
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

      {/* Restored High-Visibility Selected-Area Information Box */}
      {region && (
        <div className="absolute bottom-3 left-3 bg-white/95 backdrop-blur-md border border-bhima-border rounded-lg p-3 text-xs shadow-md z-10 max-w-sm pointer-events-auto">
          <div className="flex items-center justify-between gap-2 border-b border-bhima-border pb-1.5 mb-2">
            <div className="flex items-center gap-1.5 font-semibold text-bhima-text">
              <span className="w-2.5 h-2.5 rounded-full bg-[#0284C7] ring-2 ring-white shadow-xs shrink-0" />
              <span className="truncate">{region.name}</span>
            </div>
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-emerald-50 border border-emerald-200 text-emerald-700">
              {cachedObservationsCount !== undefined ? `${cachedObservationsCount} Months` : '72 Months Cached'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] font-mono">
            <div>
              <span className="text-bhima-muted block text-[10px] font-sans uppercase tracking-wider">Latitude</span>
              <span className="text-bhima-text font-medium">
                [{Number(region.min_lat).toFixed(2)}°, {Number(region.max_lat).toFixed(2)}°]
              </span>
            </div>
            <div>
              <span className="text-bhima-muted block text-[10px] font-sans uppercase tracking-wider">Longitude</span>
              <span className="text-bhima-text font-medium">
                [{Number(region.min_lon).toFixed(2)}°, {Number(region.max_lon).toFixed(2)}°]
              </span>
            </div>
          </div>

          <div className="mt-2 pt-1.5 border-t border-bhima-border flex items-center justify-between text-[10px] text-bhima-muted font-mono">
            <span>BBox: [{Number(region.min_lon).toFixed(2)}, {Number(region.min_lat).toFixed(2)}, {Number(region.max_lon).toFixed(2)}, {Number(region.max_lat).toFixed(2)}]</span>
            <span className="text-bhima-secondary font-sans font-medium">
              Δλ: {Math.abs(Number(region.max_lon) - Number(region.min_lon)).toFixed(1)}° · Δφ: {Math.abs(Number(region.max_lat) - Number(region.min_lat)).toFixed(1)}°
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

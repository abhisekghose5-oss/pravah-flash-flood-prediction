import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  Compass,
  Eye,
  EyeOff,
  Layers,
  MapPin,
  Maximize2,
  Minimize2,
  RefreshCw,
  ShieldAlert,
  Zap,
} from 'lucide-react';
import { WESTERN_GHATS_STATIONS } from '../services/api';

/**
 * Tile provider configurations
 */
const TILE_PROVIDERS = {
  cartoDark: {
    name: 'Command Dark',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19,
  },
  satellite: {
    name: 'Satellite Terrain',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri &mdash; Earthstar Geographics',
    maxZoom: 18,
  },
  osm: {
    name: 'Standard OSM',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    subdomains: 'abc',
    maxZoom: 19,
  },
  topo: {
    name: 'Topographic Relief',
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: 'Map: &copy; OpenTopoMap (CC-BY-SA)',
    subdomains: 'abc',
    maxZoom: 17,
  },
};

/**
 * Calculate Risk Level & Theme according to requirements:
 * - Green: NORMAL (< 25%)
 * - Yellow: ADVISORY (25% - 50%)
 * - Orange: WARNING (50% - 75%)
 * - Red: EMERGENCY (> 75%)
 */
export function getRiskLevelInfo(prob) {
  const probability = prob <= 1 ? prob * 100 : prob;

  if (probability > 75) {
    return {
      tier: 'EMERGENCY',
      label: 'Emergency',
      color: '#ef4444', // Red
      border: '#b91c1c',
      badgeClass: 'bg-red-500/20 text-red-400 border-red-500/40',
      dotClass: 'bg-red-500',
      pulseColor: 'rgba(239, 68, 68, 0.45)',
      hazardRadiusMeters: 14000,
      fillOpacity: 0.25,
    };
  }
  if (probability >= 50) {
    return {
      tier: 'WARNING',
      label: 'Warning',
      color: '#f97316', // Orange
      border: '#c2410c',
      badgeClass: 'bg-orange-500/20 text-orange-400 border-orange-500/40',
      dotClass: 'bg-orange-500',
      pulseColor: 'rgba(249, 115, 22, 0.35)',
      hazardRadiusMeters: 10000,
      fillOpacity: 0.20,
    };
  }
  if (probability >= 25) {
    return {
      tier: 'ADVISORY',
      label: 'Advisory',
      color: '#eab308', // Yellow
      border: '#a16207',
      badgeClass: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40',
      dotClass: 'bg-yellow-400',
      pulseColor: 'rgba(234, 179, 8, 0.25)',
      hazardRadiusMeters: 7500,
      fillOpacity: 0.15,
    };
  }
  return {
    tier: 'NORMAL',
    label: 'Normal',
    color: '#10b981', // Green
    border: '#047857',
    badgeClass: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40',
    dotClass: 'bg-emerald-500',
    pulseColor: 'rgba(16, 185, 129, 0.15)',
    hazardRadiusMeters: 5500,
    fillOpacity: 0.10,
  };
}

/**
 * Ensures Leaflet CSS and JS are loaded into the document runtime.
 */
function loadLeafletAssets() {
  return new Promise((resolve, reject) => {
    if (typeof window !== 'undefined' && window.L) {
      resolve(window.L);
      return;
    }

    // Check if stylesheet is already attached
    if (!document.getElementById('leaflet-css')) {
      const link = document.createElement('link');
      link.id = 'leaflet-css';
      link.rel = 'stylesheet';
      link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      link.crossOrigin = '';
      document.head.appendChild(link);
    }

    // Check if script is already loading
    const existingScript = document.getElementById('leaflet-js');
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(window.L));
      existingScript.addEventListener('error', (e) => reject(e));
      return;
    }

    const script = document.createElement('script');
    script.id = 'leaflet-js';
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    script.crossOrigin = '';
    script.async = true;
    script.onload = () => resolve(window.L);
    script.onerror = (err) => reject(err);
    document.head.appendChild(script);
  });
}

/**
 * Interactive Flood Map Component for Western Ghats, Maharashtra
 *
 * @param {Object} props
 * @param {Array} [props.stations] Array of station objects (defaults to WESTERN_GHATS_STATIONS)
 * @param {string} [props.selectedStationId] Active selected station identifier
 * @param {(stationId: string) => void} [props.onSelectStation] Callback when a station marker is clicked
 * @param {number} [props.centerLat=18.5204] Initial map center latitude (Maharashtra Western Ghats)
 * @param {number} [props.centerLng=73.8567] Initial map center longitude
 * @param {number} [props.zoom=8] Initial zoom level
 * @param {string} [props.className] Container class override
 */
export default function FloodMap({
  stations = WESTERN_GHATS_STATIONS,
  selectedStationId = 'MH_GAK_12',
  onSelectStation,
  centerLat = 18.5204,
  centerLng = 73.8567,
  zoom = 8,
  className = '',
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const tileLayerRef = useRef(null);
  const markersLayerRef = useRef(null);
  const radiiLayerRef = useRef(null);

  // Component UI State
  const [activeTileKey, setActiveTileKey] = useState('cartoDark');
  const [showHazardRadii, setShowHazardRadii] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isTileMenuOpen, setIsTileMenuOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Track station risk counts for legend
  const tierCounts = useMemo(() => {
    const counts = { EMERGENCY: 0, WARNING: 0, ADVISORY: 0, NORMAL: 0 };
    stations.forEach((st) => {
      const info = getRiskLevelInfo(st.probability ?? st.default_probability ?? 0.15);
      counts[info.tier]++;
    });
    return counts;
  }, [stations]);

  // 1. Initialize Map Instance with Leaflet
  useEffect(() => {
    let isCancelled = false;

    setIsLoading(true);
    setError(null);

    loadLeafletAssets()
      .then((L) => {
        if (isCancelled || !mapContainerRef.current) return;

        // Clean up previous instance if any
        if (mapInstanceRef.current) {
          mapInstanceRef.current.remove();
          mapInstanceRef.current = null;
        }

        // Initialize Map
        const map = L.map(mapContainerRef.current, {
          center: [centerLat, centerLng],
          zoom,
          minZoom: 6,
          maxZoom: 17,
          zoomControl: false,
          attributionControl: false,
        });

        // Add custom styled zoom control in top-left
        L.control
          .zoom({
            position: 'topleft',
          })
          .addTo(map);

        // Add Base Tile Layer
        const tileConfig = TILE_PROVIDERS[activeTileKey] || TILE_PROVIDERS.cartoDark;
        const tileLayer = L.tileLayer(tileConfig.url, {
          attribution: tileConfig.attribution,
          subdomains: tileConfig.subdomains || 'abc',
          maxZoom: tileConfig.maxZoom || 19,
        }).addTo(map);

        // Feature Layers
        const radiiGroup = L.layerGroup().addTo(map);
        const markersGroup = L.layerGroup().addTo(map);

        mapInstanceRef.current = map;
        tileLayerRef.current = tileLayer;
        radiiLayerRef.current = radiiGroup;
        markersLayerRef.current = markersGroup;

        setIsLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load Leaflet resources:', err);
        if (!isCancelled) {
          setError('Failed to initialize GIS Map engine. Check internet connectivity for map tiles.');
          setIsLoading(false);
        }
      });

    return () => {
      isCancelled = true;
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [centerLat, centerLng, zoom]);

  // 2. Handle Tile Provider Switching
  useEffect(() => {
    if (!mapInstanceRef.current || typeof window === 'undefined' || !window.L) return;
    const L = window.L;
    const map = mapInstanceRef.current;

    if (tileLayerRef.current) {
      map.removeLayer(tileLayerRef.current);
    }

    const tileConfig = TILE_PROVIDERS[activeTileKey] || TILE_PROVIDERS.cartoDark;
    tileLayerRef.current = L.tileLayer(tileConfig.url, {
      attribution: tileConfig.attribution,
      subdomains: tileConfig.subdomains || 'abc',
      maxZoom: tileConfig.maxZoom || 19,
    }).addTo(map);
  }, [activeTileKey]);

  // 3. Render Stations Markers & Circular Hazard Radii
  useEffect(() => {
    if (
      !mapInstanceRef.current ||
      !markersLayerRef.current ||
      !radiiLayerRef.current ||
      typeof window === 'undefined' ||
      !window.L
    ) {
      return;
    }

    const L = window.L;
    const markersGroup = markersLayerRef.current;
    const radiiGroup = radiiLayerRef.current;

    markersGroup.clearLayers();
    radiiGroup.clearLayers();

    stations.forEach((station) => {
      const prob = station.probability ?? station.default_probability ?? 0.2;
      const risk = getRiskLevelInfo(prob);
      const isSelected = station.station_id === selectedStationId;
      const probDisplay = Math.round((prob <= 1 ? prob * 100 : prob));

      // 3A. Circular Hazard Radius Overlay
      if (showHazardRadii) {
        const circle = L.circle([station.lat, station.lng], {
          radius: risk.hazardRadiusMeters,
          color: isSelected ? '#38bdf8' : risk.color,
          weight: isSelected ? 2.5 : 1.5,
          opacity: isSelected ? 0.9 : 0.6,
          fillColor: risk.color,
          fillOpacity: isSelected ? risk.fillOpacity * 1.5 : risk.fillOpacity,
          dashArray: isSelected ? '4, 4' : null,
        });

        circle.bindTooltip(
          `<div class="font-sans text-xs">
            <span class="font-bold">${station.name} Hazard Radius</span>
            <span class="text-slate-400 block">${(risk.hazardRadiusMeters / 1000).toFixed(0)} km Catchment Influence</span>
          </div>`,
          { className: 'leaflet-dark-tooltip', direction: 'top' }
        );

        circle.addTo(radiiGroup);
      }

      // 3B. High-Contrast Interactive Station Marker (Custom HTML DivIcon)
      const markerHtml = `
        <div class="relative flex items-center justify-center cursor-pointer group" style="width: 36px; height: 36px;">
          ${
            isSelected || risk.tier === 'EMERGENCY'
              ? `<div class="absolute inset-0 rounded-full animate-ping opacity-70" style="background-color: ${
                  isSelected ? '#38bdf8' : risk.color
                };"></div>`
              : ''
          }
          <div class="relative flex items-center justify-center rounded-full border-2 transition-transform duration-200 group-hover:scale-125 shadow-xl ${
            isSelected
              ? 'ring-4 ring-cyan-400/50 scale-110'
              : 'ring-1 ring-black/40'
          }" style="
            width: ${isSelected ? '32px' : '26px'};
            height: ${isSelected ? '32px' : '26px'};
            background-color: ${risk.color};
            border-color: ${isSelected ? '#ffffff' : '#0f172a'};
          ">
            <span class="text-[10px] font-black text-slate-950 font-mono select-none">
              ${probDisplay}%
            </span>
          </div>
        </div>
      `;

      const customIcon = L.divIcon({
        html: markerHtml,
        className: 'pravah-station-icon',
        iconSize: [36, 36],
        iconAnchor: [18, 18],
        popupAnchor: [0, -18],
      });

      const marker = L.marker([station.lat, station.lng], { icon: customIcon });

      // Rich Station Inspection Popup
      const popupHtml = `
        <div class="p-1 font-sans text-slate-100 min-w-[210px]">
          <div class="flex items-center justify-between gap-2 pb-2 border-b border-slate-700">
            <div>
              <h4 class="text-sm font-bold text-white leading-tight">${station.name}</h4>
              <span class="text-[10px] font-mono text-cyan-400">${station.station_id}</span>
            </div>
            <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border" style="
              background-color: ${risk.color}20;
              color: ${risk.color};
              border-color: ${risk.color}60;
            ">
              ${risk.tier}
            </span>
          </div>

          <div class="py-2 space-y-1 text-xs text-slate-300">
            <div class="flex justify-between">
              <span class="text-slate-400">River Basin:</span>
              <span class="font-medium text-slate-200">${station.river || 'N/A'}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">District:</span>
              <span class="font-medium text-slate-200">${station.district || 'Maharashtra'}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-400">Flood Probability:</span>
              <span class="font-mono font-bold" style="color: ${risk.color};">${probDisplay}%</span>
            </div>
            ${
              station.warning_level_m
                ? `<div class="flex justify-between">
                    <span class="text-slate-400">Warning Stage:</span>
                    <span class="font-mono text-amber-300">${station.warning_level_m} m</span>
                   </div>`
                : ''
            }
          </div>

          <button
            id="btn-select-${station.station_id}"
            class="w-full mt-1.5 py-1.5 px-3 rounded bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold text-center tracking-wide transition flex items-center justify-center gap-1 shadow"
          >
            Inspect Telemetry &rarr;
          </button>
        </div>
      `;

      marker.bindPopup(popupHtml, {
        className: 'pravah-dark-popup',
        maxWidth: 280,
      });

      marker.on('popupopen', () => {
        const btn = document.getElementById(`btn-select-${station.station_id}`);
        if (btn) {
          btn.onclick = () => {
            if (onSelectStation) onSelectStation(station.station_id);
            marker.closePopup();
          };
        }
      });

      marker.on('click', () => {
        if (onSelectStation) onSelectStation(station.station_id);
      });

      marker.addTo(markersGroup);
    });
  }, [stations, selectedStationId, showHazardRadii, onSelectStation]);

  // 4. Center map smoothly on selected station
  useEffect(() => {
    if (!mapInstanceRef.current || !selectedStationId) return;
    const selected = stations.find((s) => s.station_id === selectedStationId);
    if (selected && selected.lat && selected.lng) {
      mapInstanceRef.current.flyTo([selected.lat, selected.lng], Math.max(9, mapInstanceRef.current.getZoom()), {
        duration: 1.1,
        easeLinearity: 0.25,
      });
    }
  }, [selectedStationId, stations]);

  // Reset to default Western Ghats overview view
  const handleResetView = useCallback(() => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.flyTo([centerLat, centerLng], zoom, { duration: 1.0 });
    }
  }, [centerLat, centerLng, zoom]);

  return (
    <div
      className={`relative w-full h-full min-h-[420px] rounded-2xl overflow-hidden bg-slate-950 border border-slate-800 shadow-2xl flex flex-col select-none ${
        isFullscreen ? 'fixed inset-0 z-50 rounded-none' : ''
      } ${className}`}
    >
      {/* 1. Top Controls Overlay */}
      <div className="absolute top-3 left-3 right-3 z-[400] flex items-center justify-between pointer-events-none gap-2">
        {/* Region & Telemetry Info Pill */}
        <div className="pointer-events-auto bg-slate-950/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-slate-800 text-xs font-medium text-slate-200 shadow-lg flex items-center gap-2">
          <Compass className="w-4 h-4 text-cyan-400" />
          <span className="hidden sm:inline">Maharashtra Western Ghats</span>
          <span className="text-slate-500 hidden sm:inline">•</span>
          <span className="text-cyan-300 font-mono text-[11px] font-bold">
            {stations.length} Gauges Active
          </span>
        </div>

        {/* Action Controls & Tile Switcher */}
        <div className="pointer-events-auto flex items-center space-x-1.5 bg-slate-950/90 backdrop-blur-md p-1 rounded-xl border border-slate-800 shadow-lg">
          {/* Toggle Hazard Radii Overlay */}
          <button
            type="button"
            onClick={() => setShowHazardRadii((prev) => !prev)}
            title={showHazardRadii ? 'Hide Catchment Hazard Radii' : 'Show Catchment Hazard Radii'}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
              showHazardRadii
                ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/40'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            {showHazardRadii ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            <span className="hidden md:inline">Hazard Radii</span>
          </button>

          {/* Reset Overview Camera */}
          <button
            type="button"
            onClick={handleResetView}
            title="Reset Western Ghats Overview"
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800/80 transition"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          {/* Toggle Fullscreen */}
          <button
            type="button"
            onClick={() => setIsFullscreen((prev) => !prev)}
            title={isFullscreen ? 'Exit Fullscreen' : 'Expand Fullscreen'}
            className="p-1.5 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800/80 transition"
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>

          {/* Tile Menu Toggle */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsTileMenuOpen((prev) => !prev)}
              title="Change Map Tiles"
              className={`p-1.5 rounded-lg transition flex items-center gap-1 text-xs font-semibold ${
                isTileMenuOpen
                  ? 'bg-cyan-600 text-white'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800/80'
              }`}
            >
              <Layers className="w-4 h-4" />
            </button>

            {/* Tile Provider Popover */}
            {isTileMenuOpen && (
              <div className="absolute right-0 mt-2 w-44 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl py-1.5 z-50 text-xs font-medium">
                <div className="px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800">
                  Select Base Map
                </div>
                {Object.entries(TILE_PROVIDERS).map(([key, config]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => {
                      setActiveTileKey(key);
                      setIsTileMenuOpen(false);
                    }}
                    className={`w-full px-3 py-2 text-left flex items-center justify-between hover:bg-slate-800 transition ${
                      activeTileKey === key ? 'text-cyan-400 font-bold bg-slate-800/50' : 'text-slate-300'
                    }`}
                  >
                    <span>{config.name}</span>
                    {activeTileKey === key && <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 2. Primary Leaflet Map Viewport */}
      <div ref={mapContainerRef} className="w-full h-full flex-1 z-0 relative outline-none bg-slate-950" />

      {/* 3. Loading Skeleton Overlay */}
      {isLoading && (
        <div className="absolute inset-0 z-[500] bg-slate-950/80 backdrop-blur-sm flex flex-col items-center justify-center text-slate-200">
          <div className="relative flex items-center justify-center w-16 h-16 mb-4">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-500 opacity-40" />
            <div className="relative p-3.5 rounded-full bg-slate-900 border border-cyan-500/60 shadow-xl">
              <RefreshCw className="w-7 h-7 text-cyan-400 animate-spin" />
            </div>
          </div>
          <p className="text-sm font-semibold tracking-wide text-slate-100">
            Initializing PRAVAH GIS Map Engine...
          </p>
          <span className="text-xs text-slate-400 mt-1 font-mono">
            Calibrating Western Ghats Catchment Topology
          </span>
        </div>
      )}

      {/* 4. Error State Overlay */}
      {error && !isLoading && (
        <div className="absolute inset-0 z-[500] bg-slate-950/90 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center">
          <div className="p-3.5 rounded-full bg-red-950/80 border border-red-800/80 text-red-400 mb-3 shadow-xl">
            <AlertOctagon className="w-8 h-8" />
          </div>
          <h4 className="text-base font-bold text-white">GIS Map Telemetry Unavailable</h4>
          <p className="text-xs text-slate-400 max-w-sm mt-1.5">{error}</p>
          <button
            type="button"
            onClick={() => {
              setIsLoading(true);
              setError(null);
              loadLeafletAssets()
                .then(() => setIsLoading(false))
                .catch((e) => {
                  setError('Retry failed: ' + e.message);
                  setIsLoading(false);
                });
            }}
            className="mt-4 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-xs font-bold transition shadow-lg flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Connection</span>
          </button>
        </div>
      )}

      {/* 5. Bottom-Right Risk Scale Legend Overlay */}
      <div className="absolute bottom-3 right-3 z-[400] bg-slate-950/90 backdrop-blur-md border border-slate-800/90 rounded-2xl p-3 shadow-2xl text-xs max-w-[240px]">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-[11px] font-bold uppercase tracking-wider text-slate-300">
          <span className="flex items-center gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5 text-cyan-400" />
            <span>Flash Flood Risk Scale</span>
          </span>
        </div>

        <div className="space-y-1.5 mt-2">
          {/* Emergency */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500 ring-2 ring-red-500/30" />
              <span className="text-slate-300 font-medium text-[11px]">Emergency (&gt; 75%)</span>
            </div>
            <span className="font-mono text-[10px] text-red-400 font-bold bg-red-950/60 px-1.5 py-0.5 rounded border border-red-900/60">
              {tierCounts.EMERGENCY}
            </span>
          </div>

          {/* Warning */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-orange-500 ring-2 ring-orange-500/30" />
              <span className="text-slate-300 font-medium text-[11px]">Warning (50% - 75%)</span>
            </div>
            <span className="font-mono text-[10px] text-orange-400 font-bold bg-orange-950/60 px-1.5 py-0.5 rounded border border-orange-900/60">
              {tierCounts.WARNING}
            </span>
          </div>

          {/* Advisory */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-yellow-400 ring-2 ring-yellow-400/30" />
              <span className="text-slate-300 font-medium text-[11px]">Advisory (25% - 50%)</span>
            </div>
            <span className="font-mono text-[10px] text-yellow-300 font-bold bg-yellow-950/60 px-1.5 py-0.5 rounded border border-yellow-900/60">
              {tierCounts.ADVISORY}
            </span>
          </div>

          {/* Normal */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-emerald-500/30" />
              <span className="text-slate-300 font-medium text-[11px]">Normal (&lt; 25%)</span>
            </div>
            <span className="font-mono text-[10px] text-emerald-400 font-bold bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-900/60">
              {tierCounts.NORMAL}
            </span>
          </div>
        </div>
      </div>

      {/* Inline Leaflet dark mode & popup CSS override */}
      <style>{`
        .leaflet-container {
          background-color: #020617 !important;
          font-family: inherit;
        }
        .leaflet-bar {
          border: 1px solid rgba(51, 65, 85, 0.8) !important;
          border-radius: 12px !important;
          overflow: hidden !important;
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4) !important;
        }
        .leaflet-bar a {
          background-color: rgba(15, 23, 42, 0.95) !important;
          color: #94a3b8 !important;
          border-bottom: 1px solid rgba(51, 65, 85, 0.6) !important;
          transition: all 0.15s ease-in-out;
        }
        .leaflet-bar a:hover {
          background-color: #1e293b !important;
          color: #38bdf8 !important;
        }
        .pravah-dark-popup .leaflet-popup-content-wrapper {
          background-color: rgba(15, 23, 42, 0.96) !important;
          border: 1px solid rgba(51, 65, 85, 0.9) !important;
          border-radius: 16px !important;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.6) !important;
          backdrop-filter: blur(8px);
        }
        .pravah-dark-popup .leaflet-popup-tip {
          background-color: #0f172a !important;
        }
        .leaflet-dark-tooltip {
          background-color: rgba(15, 23, 42, 0.95) !important;
          color: #e2e8f0 !important;
          border: 1px solid #334155 !important;
          border-radius: 8px !important;
          padding: 4px 8px !important;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3) !important;
        }
      `}</style>
    </div>
  );
}

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  BarChart2,
  CheckCircle2,
  Compass,
  Database,
  Eye,
  Filter,
  Layers,
  MapPin,
  RefreshCw,
  Search,
  ShieldCheck,
  Sliders,
  Sparkles,
  Waves,
  Wifi,
  WifiOff,
} from 'lucide-react';
import Header from './components/Header';
import ControlPanel from './components/ControlPanel';
import FloodMap from './components/FloodMap';
import AlertBanner from './components/AlertBanner';
import RiskCard from './components/RiskCard';
import RainfallChart from './components/RainfallChart';
import {
  fetchFloodPrediction,
  fetchLiveOpenMeteoRainfall,
  WESTERN_GHATS_STATIONS,
  calculateRiskTier,
} from './services/api';

/**
 * Tier styling helper for Left Station Cards
 */
const TIER_CHIP_STYLES = {
  EMERGENCY: {
    badge: 'bg-red-500/15 border-red-500/50 text-red-400',
    dot: 'bg-red-500',
    ring: 'ring-red-500/30',
    progress: 'bg-red-500',
  },
  WARNING: {
    badge: 'bg-amber-500/15 border-amber-500/50 text-amber-400',
    dot: 'bg-amber-500',
    ring: 'ring-amber-500/30',
    progress: 'bg-amber-500',
  },
  ADVISORY: {
    badge: 'bg-yellow-500/15 border-yellow-500/50 text-yellow-300',
    dot: 'bg-yellow-400',
    ring: 'ring-yellow-500/30',
    progress: 'bg-yellow-400',
  },
  NORMAL: {
    badge: 'bg-emerald-500/15 border-emerald-500/50 text-emerald-400',
    dot: 'bg-emerald-400',
    ring: 'ring-emerald-500/30',
    progress: 'bg-emerald-400',
  },
};

/**
 * Master Application Shell for PRAVAH Flash Flood Early Warning System
 *
 * Implements:
 * - Master state management for selectedStation, riskData, isLoading, and activeMode
 * - Complete offline resilience with seamless fallback to static mock layer
 * - Integration of Header, ControlPanel, FloodMap, AlertBanner, RiskCard, and RainfallChart
 */
export default function App() {
  // 1. Master State Management
  const [selectedStationId, setSelectedStationId] = useState('MH_GAK_12'); // Karad default
  const [riskData, setRiskData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeMode, setActiveMode] = useState('live'); // 'live' | 'simulation'
  const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().split('T')[0]);

  // Provenance & Offline Resilience
  const [lastFetched, setLastFetched] = useState(() => new Date().toISOString());
  const [isOfflineMode, setIsOfflineMode] = useState(false);

  // Filter & Mobile Navigation
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilterTier, setSelectedFilterTier] = useState('ALL');
  const [mobileTab, setMobileTab] = useState('intelligence'); // 'controls' | 'intelligence'

  // Selected Station Record from Catalog
  const selectedStation = useMemo(() => {
    return (
      WESTERN_GHATS_STATIONS.find((s) => s.station_id === selectedStationId) ||
      WESTERN_GHATS_STATIONS[0]
    );
  }, [selectedStationId]);

  // Filtered station cards for Left Sidebar
  const filteredStations = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return WESTERN_GHATS_STATIONS.filter((s) => {
      const matchQuery =
        s.name.toLowerCase().includes(q) ||
        s.station_id.toLowerCase().includes(q) ||
        s.river.toLowerCase().includes(q) ||
        s.district.toLowerCase().includes(q) ||
        s.basin.toLowerCase().includes(q);

      const matchTier =
        selectedFilterTier === 'ALL' || s.default_tier === selectedFilterTier;

      return matchQuery && matchTier;
    });
  }, [searchQuery, selectedFilterTier]);

  // Overall Statistics for Navigation Header
  const stats = useMemo(() => {
    const counts = { emergency: 0, warning: 0, advisory: 0, normal: 0 };
    WESTERN_GHATS_STATIONS.forEach((s) => {
      if (s.default_tier === 'EMERGENCY') counts.emergency++;
      else if (s.default_tier === 'WARNING') counts.warning++;
      else if (s.default_tier === 'ADVISORY') counts.advisory++;
      else counts.normal++;
    });
    return counts;
  }, []);

  // Synchronized dynamic stations reflecting in-flight simulation on the map
  const dynamicStations = useMemo(() => {
    return WESTERN_GHATS_STATIONS.map((st) => {
      if (st.station_id === selectedStationId && riskData) {
        return {
          ...st,
          probability: riskData.prediction.probability,
          risk_tier: riskData.prediction.risk_tier,
        };
      }
      return st;
    });
  }, [selectedStationId, riskData]);

  // 2. Resilient Risk Inference Runner (Offline-Safe)
  const runRiskInference = useCallback(
    async (options = {}) => {
      setIsLoading(true);

      const stationId = options.stationId || selectedStationId;
      const targetDate = options.date || selectedDate;
      const mode = options.mode || activeMode;
      const targetStation =
        WESTERN_GHATS_STATIONS.find((s) => s.station_id === stationId) ||
        WESTERN_GHATS_STATIONS[0];

      let inputs = options.rainfallInputs;
      let provenanceSource =
        mode === 'live'
          ? 'Open-Meteo Live API'
          : 'Synthetic Simulation (Manual Override)';

      // When in Live Mode, attempt real-time Open-Meteo observation query with offline fallback
      if (mode === 'live' && !inputs) {
        try {
          const liveMeteo = await fetchLiveOpenMeteoRainfall(targetStation.lat, targetStation.lng);
          if (liveMeteo?.success && liveMeteo.rainfall) {
            inputs = liveMeteo.rainfall;
            provenanceSource = 'Open-Meteo Live API';
            setIsOfflineMode(false);
          } else {
            // Live fetch failed, use calibrated fallback gracefully
            provenanceSource = 'Open-Meteo Live API (Offline Telemetry)';
            setIsOfflineMode(true);
          }
        } catch (err) {
          console.warn('Network unavailable, falling back to local benchmark telemetry:', err);
          provenanceSource = 'Open-Meteo Live API (Offline Telemetry)';
          setIsOfflineMode(true);
        }
      }

      // Execute prediction through API service layer
      try {
        const result = await fetchFloodPrediction({
          station_id: stationId,
          date: targetDate,
          rainfall_inputs: inputs,
          data_source: provenanceSource,
        });
        setRiskData(result);
        setLastFetched(new Date().toISOString());
      } catch (err) {
        console.error('Inference error encountered, generating resilient fallback prediction:', err);
        // Absolute fallback guarantees zero dashboard crash
        const fallbackTier = targetStation.default_tier;
        setRiskData({
          station_id: targetStation.station_id,
          catchment_name: `${targetStation.name} (${targetStation.river} / ${targetStation.basin})`,
          lat: targetStation.lat,
          lng: targetStation.lng,
          timestamp: new Date().toISOString(),
          data_source: 'Local Emergency Offline Benchmark',
          rainfall: {
            day_1: targetStation.base_rainfall.day_1,
            day_3_cum: targetStation.base_rainfall.day_3_cum,
            day_7_cum: targetStation.base_rainfall.day_7_cum,
            series: [],
          },
          prediction: {
            probability: targetStation.default_probability,
            risk_tier: fallbackTier,
          },
          alert: {
            title: `Advisory Watch — ${targetStation.name} Station`,
            recommendation: 'Operate in offline disaster protocol until network telemetry reconnects.',
            issued_at: new Date().toISOString(),
          },
        });
        setIsOfflineMode(true);
      } finally {
        setIsLoading(false);
      }
    },
    [selectedStationId, selectedDate, activeMode]
  );

  // Initial load and station/date sync
  useEffect(() => {
    let isMounted = true;
    runRiskInference().then(() => {
      if (!isMounted) return;
    });
    return () => {
      isMounted = false;
    };
  }, [selectedStationId, selectedDate, activeMode]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-white">
      
      {/* 1. Global Navigation Header */}
      <Header
        mode={activeMode}
        onModeChange={(m) => {
          setActiveMode(m);
          runRiskInference({ mode: m });
        }}
        selectedDate={selectedDate}
        onDateChange={setSelectedDate}
        stats={stats}
        isLoading={isLoading}
        onRefresh={() => runRiskInference({ mode: activeMode })}
      />

      {/* Offline Status Alert Banner (Shown if telemetry falls back to local cache) */}
      {isOfflineMode && (
        <div className="bg-amber-950/80 border-b border-amber-800/80 px-4 py-1.5 text-xs text-amber-300 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <WifiOff className="w-3.5 h-3.5 text-amber-400" />
            <span className="font-semibold">
              Live Network Disconnected: Operating with Calibrated Maharashtra Offline Hydrological Cache.
            </span>
          </div>
          <button
            type="button"
            onClick={() => runRiskInference({ mode: activeMode })}
            className="text-[11px] underline font-bold hover:text-white"
          >
            Retry Live Sync
          </button>
        </div>
      )}

      {/* Mobile Tab Switcher */}
      <div className="lg:hidden flex border-b border-slate-800 bg-slate-900 px-4 py-2 gap-2">
        <button
          type="button"
          onClick={() => setMobileTab('intelligence')}
          className={`flex-1 py-2 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition ${
            mobileTab === 'intelligence'
              ? 'bg-cyan-600 text-white shadow'
              : 'bg-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Map & Intelligence</span>
        </button>
        <button
          type="button"
          onClick={() => setMobileTab('controls')}
          className={`flex-1 py-2 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition ${
            mobileTab === 'controls'
              ? 'bg-cyan-600 text-white shadow'
              : 'bg-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          <Sliders className="w-4 h-4" />
          <span>Control Panel ({filteredStations.length})</span>
        </button>
      </div>

      {/* 2. Primary 2-Column Responsive Dashboard Viewport */}
      <main className="flex-1 max-w-[1920px] w-full mx-auto p-3 sm:p-4 lg:p-6 grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        {/* ========================================================================= */}
        {/* LEFT COLUMN: Controls & Station Selection Feed (Cols 1 to 5 on Desktop)    */}
        {/* ========================================================================= */}
        <section
          className={`lg:col-span-5 xl:col-span-4 flex flex-col gap-4 ${
            mobileTab === 'controls' ? 'flex' : 'hidden lg:flex'
          }`}
        >
          {/* Component: Control & Input Panel */}
          <ControlPanel
            selectedStationId={selectedStationId}
            onSelectStation={(id) => {
              setSelectedStationId(id);
              runRiskInference({ stationId: id });
              setMobileTab('intelligence');
            }}
            selectedDate={selectedDate}
            onDateChange={setSelectedDate}
            mode={activeMode}
            onModeChange={(m) => {
              setActiveMode(m);
              runRiskInference({ mode: m });
            }}
            isLoading={isLoading}
            lastFetchedTimestamp={lastFetched}
            dataSource={riskData?.data_source}
            stations={WESTERN_GHATS_STATIONS}
            onCheckRisk={(params) => runRiskInference(params)}
          />

          {/* Station Quick Search & Filter Panel */}
          <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-3.5 shadow-lg flex flex-col gap-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Filter 20 Western Ghats gauges..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3.5 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition"
              />
            </div>

            {/* Risk Tier Filter Chips */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
              {['ALL', 'EMERGENCY', 'WARNING', 'ADVISORY', 'NORMAL'].map((tier) => (
                <button
                  key={tier}
                  type="button"
                  onClick={() => setSelectedFilterTier(tier)}
                  className={`px-2.5 py-1 rounded-lg border text-[11px] font-semibold whitespace-nowrap transition ${
                    selectedFilterTier === tier
                      ? 'bg-slate-700 border-slate-600 text-white shadow-sm'
                      : 'bg-slate-950/60 border-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  {tier}
                </button>
              ))}
            </div>
          </div>

          {/* Scrollable Catchments Station List Feed */}
          <div className="flex-1 bg-slate-900/70 border border-slate-800 rounded-2xl p-3 flex flex-col overflow-hidden max-h-[calc(100vh-320px)] min-h-[360px]">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 px-1 text-xs text-slate-400 font-medium">
              <span>Registered River Gauges</span>
              <span className="font-mono text-[11px] text-cyan-400">
                {filteredStations.length} / 20 Monitoring
              </span>
            </div>

            <div className="overflow-y-auto space-y-2 mt-2.5 pr-1 custom-scrollbar">
              {filteredStations.map((station) => {
                const isSelected = station.station_id === selectedStationId;
                const sTier = station.default_tier;
                const style = TIER_CHIP_STYLES[sTier] || TIER_CHIP_STYLES.NORMAL;

                return (
                  <div
                    key={station.station_id}
                    onClick={() => {
                      setSelectedStationId(station.station_id);
                      runRiskInference({ stationId: station.station_id });
                      setMobileTab('intelligence');
                    }}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        setSelectedStationId(station.station_id);
                        runRiskInference({ stationId: station.station_id });
                        setMobileTab('intelligence');
                      }
                    }}
                    className={`p-3 rounded-xl border text-left cursor-pointer transition-all duration-200 ${
                      isSelected
                        ? 'bg-slate-800/90 border-cyan-500 shadow-md shadow-cyan-950/40 ring-1 ring-cyan-500/50'
                        : 'bg-slate-950/60 border-slate-800/80 hover:bg-slate-850 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center space-x-2">
                        <span className={`w-2.5 h-2.5 rounded-full ${style.dot} ring-2 ${style.ring}`} />
                        <h4 className="text-sm font-bold text-slate-200 leading-none">
                          {station.name}
                        </h4>
                        <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
                          {station.station_id}
                        </span>
                      </div>

                      <span
                        className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${style.badge}`}
                      >
                        {sTier}
                      </span>
                    </div>

                    <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                      <span>
                        {station.river} • {station.district}
                      </span>
                      <span className="font-mono text-slate-300 font-medium">
                        {station.base_rainfall.day_1} mm/24h
                      </span>
                    </div>

                    {/* Mini Probability Gauge Bar */}
                    <div className="mt-2 w-full bg-slate-800/80 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${style.progress}`}
                        style={{ width: `${Math.round(station.default_probability * 100)}%` }}
                      />
                    </div>
                  </div>
                );
              })}

              {filteredStations.length === 0 && (
                <div className="text-center py-10 text-slate-500 text-xs">
                  No monitoring stations match your search or tier filter.
                </div>
              )}
            </div>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* RIGHT COLUMN: Map, Alert Banner, Risk Card & Rainfall Chart (Cols 6-12)    */}
        {/* ========================================================================= */}
        <section
          className={`lg:col-span-7 xl:col-span-8 flex flex-col gap-4 ${
            mobileTab === 'intelligence' ? 'flex' : 'hidden lg:flex'
          }`}
        >
          {/* 1. Component: High-Priority Actionable Alert Banner */}
          {riskData && (
            <AlertBanner
              prediction={riskData}
              station={selectedStation}
            />
          )}

          {/* 2. Component: Interactive GIS Flood Map (Leaflet / Satellite / OSM) */}
          <div className="min-h-[440px] lg:min-h-[480px] w-full flex flex-col">
            <FloodMap
              stations={dynamicStations}
              selectedStationId={selectedStationId}
              onSelectStation={(id) => {
                setSelectedStationId(id);
                runRiskInference({ stationId: id });
              }}
              centerLat={18.5204}
              centerLng={73.8567}
              zoom={8}
            />
          </div>

          {/* 3. Component: Flash-Flood Risk Card & Rainfall Breakdown */}
          {riskData && (
            <RiskCard
              prediction={riskData}
              station={selectedStation}
              modelProvenance="Model: LightGBM Calibrated v2.1 | Daily Resolution Engine"
            />
          )}

          {/* 4. Component: Rainfall Time-Series Chart (7-Day Past + 1-Day Forecast) */}
          {riskData && (
            <RainfallChart
              rainfall={riskData.rainfall}
              threshold={120}
              stationName={selectedStation.name}
            />
          )}

          {/* 5. Hydrological Characteristics Footer */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-md grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div>
              <span className="text-slate-500 text-[11px] block">River / Basin</span>
              <span className="font-semibold text-slate-200">
                {selectedStation.river} ({selectedStation.basin})
              </span>
            </div>
            <div>
              <span className="text-slate-500 text-[11px] block">Coordinates</span>
              <span className="font-semibold text-slate-200 font-mono">
                {selectedStation.lat.toFixed(3)}°N, {selectedStation.lng.toFixed(3)}°E
              </span>
            </div>
            <div>
              <span className="text-slate-500 text-[11px] block">Warning Stage</span>
              <span className="font-mono font-semibold text-amber-400">
                {selectedStation.warning_level_m} m
              </span>
            </div>
            <div>
              <span className="text-slate-500 text-[11px] block">Danger Stage</span>
              <span className="font-mono font-semibold text-red-400">
                {selectedStation.danger_level_m} m
              </span>
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}

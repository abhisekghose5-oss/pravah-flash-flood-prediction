import React, { useState, useEffect, useMemo } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  ArrowUpRight,
  BarChart2,
  Calendar,
  CheckCircle2,
  ChevronRight,
  Compass,
  Droplets,
  ExternalLink,
  Filter,
  Info,
  Layers,
  MapPin,
  RefreshCw,
  Search,
  Sliders,
  Sparkles,
  TrendingUp,
  Waves,
} from 'lucide-react';
import Header from './Header';
import FloodMap from './FloodMap';
import ControlPanel from './ControlPanel';
import AlertBanner from './AlertBanner';
import RiskCard from './RiskCard';
import RainfallChart from './RainfallChart';
import {
  fetchFloodPrediction,
  fetchLiveOpenMeteoRainfall,
  WESTERN_GHATS_STATIONS,
  calculateRiskTier,
} from '../services/api';

/**
 * Styling helpers for Risk Tiers
 */
const TIER_STYLES = {
  EMERGENCY: {
    badge: 'bg-red-500/15 border-red-500/50 text-red-400',
    dot: 'bg-red-500',
    ring: 'ring-red-500/30',
    card: 'border-red-900/60 bg-red-950/20',
    progress: 'bg-red-500',
    text: 'text-red-400',
  },
  WARNING: {
    badge: 'bg-amber-500/15 border-amber-500/50 text-amber-400',
    dot: 'bg-amber-500',
    ring: 'ring-amber-500/30',
    card: 'border-amber-900/60 bg-amber-950/20',
    progress: 'bg-amber-500',
    text: 'text-amber-400',
  },
  ADVISORY: {
    badge: 'bg-yellow-500/15 border-yellow-500/50 text-yellow-300',
    dot: 'bg-yellow-400',
    ring: 'ring-yellow-500/30',
    card: 'border-yellow-900/60 bg-yellow-950/20',
    progress: 'bg-yellow-400',
    text: 'text-yellow-300',
  },
  NORMAL: {
    badge: 'bg-emerald-500/15 border-emerald-500/50 text-emerald-400',
    dot: 'bg-emerald-400',
    ring: 'ring-emerald-500/30',
    card: 'border-emerald-900/60 bg-emerald-950/20',
    progress: 'bg-emerald-400',
    text: 'text-emerald-400',
  },
};

export default function DashboardLayout() {
  // Operational State
  const [mode, setMode] = useState('live'); // 'live' | 'simulation'
  const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [selectedStationId, setSelectedStationId] = useState('MH_GAK_12'); // Karad default
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(true);

  // Search & Filtering
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilterTier, setSelectedFilterTier] = useState('ALL');

  // Mobile View Toggle
  const [mobileTab, setMobileTab] = useState('map'); // 'stations' | 'map'

  // Provenance timestamp
  const [lastFetched, setLastFetched] = useState(() => new Date().toISOString());

  // Unified Risk Check Action triggered by ControlPanel or Refresh
  const handleCheckRisk = async (params = {}) => {
    setLoading(true);
    const targetStationId = params.stationId || selectedStationId;
    const targetDate = params.date || selectedDate;
    const targetMode = params.mode || mode;
    const st = WESTERN_GHATS_STATIONS.find((s) => s.station_id === targetStationId) || WESTERN_GHATS_STATIONS[0];

    let inputs = params.rainfallInputs;
    let provSource = targetMode === 'live' ? 'Open-Meteo Live API' : 'Synthetic Simulation (Manual Override)';

    if (targetMode === 'live' && !inputs) {
      const liveData = await fetchLiveOpenMeteoRainfall(st.lat, st.lng);
      if (liveData?.rainfall) {
        inputs = liveData.rainfall;
      }
    }

    try {
      const res = await fetchFloodPrediction({
        station_id: targetStationId,
        date: targetDate,
        rainfall_inputs: inputs,
        data_source: provSource,
      });
      setPrediction(res);
      setLastFetched(new Date().toISOString());
    } catch (err) {
      console.error('Failed to run flood risk prediction:', err);
    } finally {
      setLoading(false);
    }
  };

  // Load prediction when station or date changes
  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    fetchFloodPrediction({
      station_id: selectedStationId,
      date: selectedDate,
      data_source: mode === 'live' ? 'Open-Meteo Live API' : 'Synthetic Simulation',
    })
      .then((data) => {
        if (isMounted) {
          setPrediction(data);
          setLastFetched(new Date().toISOString());
          setLoading(false);
        }
      })
      .catch((err) => {
        console.error('Failed to fetch flood prediction:', err);
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedStationId, selectedDate, mode]);

  // Selected Station Details from Catalog
  const currentStation = useMemo(() => {
    return (
      WESTERN_GHATS_STATIONS.find((s) => s.station_id === selectedStationId) ||
      WESTERN_GHATS_STATIONS[0]
    );
  }, [selectedStationId]);

  // Filtered stations for left sidebar
  const filteredStations = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return WESTERN_GHATS_STATIONS.filter((s) => {
      const matchesSearch =
        s.name.toLowerCase().includes(query) ||
        s.station_id.toLowerCase().includes(query) ||
        s.river.toLowerCase().includes(query) ||
        s.district.toLowerCase().includes(query) ||
        s.basin.toLowerCase().includes(query);

      const matchesTier =
        selectedFilterTier === 'ALL' || s.default_tier === selectedFilterTier;

      return matchesSearch && matchesTier;
    });
  }, [searchQuery, selectedFilterTier]);

  // Synchronize stations with simulated prediction results
  const dynamicStations = useMemo(() => {
    return WESTERN_GHATS_STATIONS.map((st) => {
      if (st.station_id === selectedStationId && prediction) {
        return {
          ...st,
          probability: prediction.prediction.probability,
          risk_tier: prediction.prediction.risk_tier,
        };
      }
      return st;
    });
  }, [selectedStationId, prediction]);

  // Overall Statistics for Header counters
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

  const activeTier = prediction?.prediction?.risk_tier || 'NORMAL';
  const tierStyle = TIER_STYLES[activeTier] || TIER_STYLES.NORMAL;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-white">
      {/* 1. Global Navigation Header */}
      <Header
        mode={mode}
        onModeChange={setMode}
        selectedDate={selectedDate}
        onDateChange={setSelectedDate}
        stats={stats}
        isLoading={loading}
        onRefresh={() => {
          setLoading(true);
          fetchFloodPrediction({
            station_id: selectedStationId,
            date: selectedDate,
          }).then((res) => {
            setPrediction(res);
            setLoading(false);
          });
        }}
      />

      {/* Mobile Tab Switcher */}
      <div className="lg:hidden flex border-b border-slate-800 bg-slate-900 px-4 py-2 gap-2">
        <button
          type="button"
          onClick={() => setMobileTab('map')}
          className={`flex-1 py-2 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition ${
            mobileTab === 'map'
              ? 'bg-cyan-600 text-white shadow'
              : 'bg-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Map & Intelligence</span>
        </button>
        <button
          type="button"
          onClick={() => setMobileTab('stations')}
          className={`flex-1 py-2 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition ${
            mobileTab === 'stations'
              ? 'bg-cyan-600 text-white shadow'
              : 'bg-slate-800 text-slate-400 hover:text-white'
          }`}
        >
          <MapPin className="w-4 h-4" />
          <span>Stations List ({filteredStations.length})</span>
        </button>
      </div>

      {/* 2. Main Dashboard Viewport: 2-Column Desktop Grid / Stacked Mobile */}
      <main className="flex-1 max-w-[1920px] w-full mx-auto p-3 sm:p-4 lg:p-6 grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        {/* ========================================================================= */}
        {/* LEFT COLUMN: Catchments / Stations Telemetry Feed (Col 1 to 5 on Desktop)  */}
        {/* ========================================================================= */}
        <section
          className={`lg:col-span-5 xl:col-span-4 flex flex-col gap-4 ${
            mobileTab === 'stations' ? 'flex' : 'hidden lg:flex'
          }`}
        >
          {/* Unified Hydrological Control & Input Panel */}
          <ControlPanel
            selectedStationId={selectedStationId}
            onSelectStation={(id) => {
              setSelectedStationId(id);
              handleCheckRisk({ stationId: id, mode });
            }}
            selectedDate={selectedDate}
            onDateChange={setSelectedDate}
            mode={mode}
            onModeChange={setMode}
            isLoading={loading}
            lastFetchedTimestamp={lastFetched}
            dataSource={prediction?.data_source}
            stations={WESTERN_GHATS_STATIONS}
            onCheckRisk={handleCheckRisk}
          />

          {/* Station Search & Filter Panel */}
          <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-3.5 shadow-lg flex flex-col gap-3">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search station, river, or district..."
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

          {/* Scrollable Catchments Station Cards List */}
          <div className="flex-1 bg-slate-900/70 border border-slate-800 rounded-2xl p-3 flex flex-col overflow-hidden max-h-[calc(100vh-280px)] min-h-[420px]">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800/80 px-1 text-xs text-slate-400 font-medium">
              <span>Western Ghats Catchments</span>
              <span className="font-mono text-[11px] text-cyan-400">
                {filteredStations.length} / 20 Registered
              </span>
            </div>

            <div className="overflow-y-auto space-y-2 mt-2.5 pr-1 custom-scrollbar">
              {filteredStations.map((station) => {
                const isSelected = station.station_id === selectedStationId;
                const sTier = station.default_tier;
                const style = TIER_STYLES[sTier] || TIER_STYLES.NORMAL;

                return (
                  <div
                    key={station.station_id}
                    onClick={() => {
                      setSelectedStationId(station.station_id);
                      setMobileTab('map');
                    }}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        setSelectedStationId(station.station_id);
                        setMobileTab('map');
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

                    {/* Probability Progress Bar */}
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

        {/* ========================================================================== */}
        {/* RIGHT COLUMN: Map & Real-time Predictive Intelligence (Col 6 to 12)        */}
        {/* ========================================================================== */}
        <section
          className={`lg:col-span-7 xl:col-span-8 flex flex-col gap-4 ${
            mobileTab === 'map' ? 'flex' : 'hidden lg:flex'
          }`}
        >
          {/* 1. Critical Early Warning Actionable Alert Banner */}
          {prediction && (
            <AlertBanner
              prediction={prediction}
              station={currentStation}
            />
          )}

          {/* 2. Interactive GIS Flood Map Component (Leaflet / OpenStreetMap / Satellite) */}
          <div className="min-h-[440px] lg:min-h-[480px] w-full flex flex-col">
            <FloodMap
              stations={dynamicStations}
              selectedStationId={selectedStationId}
              onSelectStation={(id) => setSelectedStationId(id)}
              centerLat={18.5204}
              centerLng={73.8567}
              zoom={8}
            />
          </div>

          {/* 3. Flash-Flood Risk Gauge & Rainfall Metrics Breakdown */}
          {prediction && (
            <RiskCard
              prediction={prediction}
              station={currentStation}
              modelProvenance="Model: LightGBM Calibrated v2.1 | Daily Resolution Engine"
            />
          )}

          {/* 4. Rainfall Time-Series Chart (7-Day Past + 1-Day Forecast) */}
          {prediction && (
            <RainfallChart
              rainfall={prediction.rainfall}
              threshold={120}
              stationName={currentStation.name}
            />
          )}

          {/* 5. Hydrological Characteristics Footer */}
          {prediction && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-md grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div>
                <span className="text-slate-500 text-[11px] block">River / Basin</span>
                <span className="font-semibold text-slate-300">
                  {currentStation.river} ({currentStation.basin})
                </span>
              </div>
              <div>
                <span className="text-slate-500 text-[11px] block">Location</span>
                <span className="font-semibold text-slate-300 font-mono">
                  {currentStation.lat.toFixed(3)}°N, {currentStation.lng.toFixed(3)}°E
                </span>
              </div>
              <div>
                <span className="text-slate-500 text-[11px] block">Warning Stage</span>
                <span className="font-mono font-semibold text-amber-400">
                  {currentStation.warning_level_m} m
                </span>
              </div>
              <div>
                <span className="text-slate-500 text-[11px] block">Danger Stage</span>
                <span className="font-mono font-semibold text-red-400">
                  {currentStation.danger_level_m} m
                </span>
              </div>
            </div>
          )}
        </section>

      </main>
    </div>
  );
}

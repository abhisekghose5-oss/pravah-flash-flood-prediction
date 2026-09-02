import React, { useState, useEffect, useMemo } from 'react';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  Calendar,
  CheckCircle2,
  Clock,
  CloudRain,
  Database,
  Droplets,
  Layers,
  MapPin,
  RefreshCw,
  Sliders,
  Sparkles,
  TrendingUp,
  Zap,
} from 'lucide-react';
import { WESTERN_GHATS_STATIONS } from '../services/api';

/**
 * Control & Input Panel Component for PRAVAH Early Warning System
 *
 * @param {Object} props
 * @param {string} [props.selectedStationId='MH_GAK_12'] Active station code
 * @param {(stationId: string) => void} props.onSelectStation Callback on station change
 * @param {string} [props.selectedDate] Selected date (YYYY-MM-DD)
 * @param {(date: string) => void} props.onDateChange Callback on date change
 * @param {'live' | 'simulation'} [props.mode='live'] Active operational mode
 * @param {(mode: 'live' | 'simulation') => void} props.onModeChange Callback on mode change
 * @param {(payload: Object) => Promise<void> | void} props.onCheckRisk Primary CTA callback
 * @param {boolean} [props.isLoading=false] Whether API inference request is in-flight
 * @param {string} [props.lastFetchedTimestamp] ISO string or formatted timestamp of last data fetch
 * @param {string} [props.dataSource] Custom data source label override
 * @param {Array} [props.stations=WESTERN_GHATS_STATIONS] Catalog of 20 Western Ghats stations
 * @param {string} [props.className] Additional CSS classes
 */
export default function ControlPanel({
  selectedStationId = 'MH_GAK_12',
  onSelectStation,
  selectedDate = new Date().toISOString().split('T')[0],
  onDateChange,
  mode = 'live',
  onModeChange,
  onCheckRisk,
  isLoading = false,
  lastFetchedTimestamp,
  dataSource,
  stations = WESTERN_GHATS_STATIONS,
  className = '',
}) {
  const isLive = mode === 'live';

  // Manual Simulation Rainfall Inputs (mm)
  const [rainfallInputs, setRainfallInputs] = useState({
    day_1: 45,
    day_3_cum: 125,
    day_7_cum: 240,
  });

  // Validation state
  const [validationError, setValidationError] = useState('');
  const [activePreset, setActivePreset] = useState('moderate');

  // Find currently selected station record
  const currentStation = useMemo(() => {
    return (
      stations.find((s) => s.station_id === selectedStationId) ||
      stations[0]
    );
  }, [stations, selectedStationId]);

  // Synchronize initial simulation inputs when station changes
  useEffect(() => {
    if (currentStation && currentStation.base_rainfall) {
      setRainfallInputs({
        day_1: currentStation.base_rainfall.day_1 || 35,
        day_3_cum: currentStation.base_rainfall.day_3_cum || 90,
        day_7_cum: currentStation.base_rainfall.day_7_cum || 180,
      });
    }
  }, [currentStation?.station_id]);

  // Validate numerical rainfall inputs
  const validateInputs = (inputs) => {
    const { day_1, day_3_cum, day_7_cum } = inputs;

    if (isNaN(day_1) || isNaN(day_3_cum) || isNaN(day_7_cum)) {
      return 'Rainfall amounts must be valid numerical values.';
    }
    if (day_1 < 0 || day_3_cum < 0 || day_7_cum < 0) {
      return 'Non-physical negative rainfall values are not permitted (≥ 0 mm).';
    }
    if (day_1 > 1000 || day_3_cum > 1000 || day_7_cum > 1000) {
      return 'Rainfall values exceed meteorological upper boundary (max 1000 mm).';
    }
    if (day_1 > day_3_cum) {
      return '1-Day precipitation cannot exceed 3-Day cumulative sum.';
    }
    if (day_3_cum > day_7_cum) {
      return '3-Day cumulative sum cannot exceed 7-Day cumulative total.';
    }
    return '';
  };

  // Handle manual input change with validation
  const handleInputChange = (field, rawValue) => {
    const value = Math.max(0, Number(rawValue) || 0);
    const updated = { ...rainfallInputs, [field]: value };

    // Sensible auto-adjustment to maintain physical consistency: day_1 <= day_3_cum <= day_7_cum
    if (field === 'day_1' && value > updated.day_3_cum) {
      updated.day_3_cum = value;
      if (value > updated.day_7_cum) updated.day_7_cum = Math.round(value * 1.5);
    }
    if (field === 'day_3_cum' && value > updated.day_7_cum) {
      updated.day_7_cum = value;
    }

    setRainfallInputs(updated);
    setActivePreset('custom');
    setValidationError(validateInputs(updated));
  };

  // Quick Simulation Preset Handler
  const handleApplyPreset = (preset) => {
    setActivePreset(preset);
    let vals;
    switch (preset) {
      case 'lull':
        vals = { day_1: 8, day_3_cum: 22, day_7_cum: 48 };
        break;
      case 'moderate':
        vals = { day_1: 45, day_3_cum: 110, day_7_cum: 195 };
        break;
      case 'heavy':
        vals = { day_1: 85, day_3_cum: 185, day_7_cum: 320 };
        break;
      case 'cloudburst':
        vals = { day_1: 155, day_3_cum: 290, day_7_cum: 480 };
        break;
      default:
        vals = { day_1: 45, day_3_cum: 110, day_7_cum: 195 };
    }
    setRainfallInputs(vals);
    setValidationError(validateInputs(vals));
  };

  // Form submission / Primary CTA execution
  const handleSubmit = async (e) => {
    e?.preventDefault();

    if (!isLive) {
      const err = validateInputs(rainfallInputs);
      if (err) {
        setValidationError(err);
        return;
      }
    }

    setValidationError('');
    if (onCheckRisk) {
      await onCheckRisk({
        stationId: selectedStationId,
        date: selectedDate,
        mode,
        rainfallInputs: !isLive ? rainfallInputs : undefined,
      });
    }
  };

  // Format Provenance Display
  const currentProvenance =
    dataSource ||
    (isLive
      ? 'Source: Open-Meteo Live API'
      : 'Source: Synthetic Simulation');

  const displayTimestamp = useMemo(() => {
    if (lastFetchedTimestamp) {
      try {
        const d = new Date(lastFetchedTimestamp);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' IST';
      } catch {
        return lastFetchedTimestamp;
      }
    }
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' IST';
  }, [lastFetchedTimestamp]);

  return (
    <div
      className={`bg-slate-900/95 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-2xl flex flex-col gap-4 text-slate-200 select-none ${className}`}
    >
      {/* 1. Header & Data Provenance Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2.5 pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <div className="p-2 rounded-xl bg-cyan-950/60 border border-cyan-800/60 text-cyan-400">
            <Sliders className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              Control & Inference Settings
            </h3>
            <span className="text-[11px] text-slate-400 font-medium">
              Hydrological Observation & Simulation Engine
            </span>
          </div>
        </div>

        {/* Data Provenance Indicator Pill & Timestamp */}
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`text-[10px] font-bold tracking-wider uppercase px-2.5 py-1 rounded-full border flex items-center gap-1.5 shadow-sm ${
              isLive
                ? 'bg-blue-500/15 border-blue-500/40 text-blue-300 shadow-blue-950/40'
                : 'bg-amber-500/15 border-amber-500/40 text-amber-300 shadow-amber-950/40'
            }`}
          >
            <Database className="w-3 h-3" />
            <span>{currentProvenance}</span>
          </span>

          <span className="text-[10px] text-slate-400 font-mono flex items-center gap-1 bg-slate-950/60 px-2 py-1 rounded border border-slate-800">
            <Clock className="w-3 h-3 text-slate-500" />
            <span>{displayTimestamp}</span>
          </span>
        </div>
      </div>

      {/* 2. Operational Mode Selector Segmented Toggle */}
      <div className="flex flex-col gap-1.5">
        <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Telemetry Operational Mode
        </label>
        <div className="grid grid-cols-2 bg-slate-950 p-1 rounded-xl border border-slate-800 gap-1">
          {/* Mode A: Live Weather */}
          <button
            type="button"
            onClick={() => {
              if (onModeChange) onModeChange('live');
              setValidationError('');
            }}
            className={`py-2 px-3 rounded-lg text-xs font-bold transition flex items-center justify-center gap-2 ${
              isLive
                ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-md shadow-blue-950/50 ring-1 ring-white/10'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <CloudRain className="w-4 h-4" />
            <span>Mode A: Live Weather</span>
          </button>

          {/* Mode B: Manual Simulation */}
          <button
            type="button"
            onClick={() => {
              if (onModeChange) onModeChange('simulation');
              setValidationError(validateInputs(rainfallInputs));
            }}
            className={`py-2 px-3 rounded-lg text-xs font-bold transition flex items-center justify-center gap-2 ${
              !isLive
                ? 'bg-gradient-to-r from-amber-600 to-orange-600 text-white shadow-md shadow-amber-950/50 ring-1 ring-white/10'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Zap className="w-4 h-4" />
            <span>Mode B: Manual Simulation</span>
          </button>
        </div>
      </div>

      {/* 3. Primary Input Form Grid: Station Selector + Date Picker */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {/* Station Selector Dropdown */}
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="station-select"
            className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5"
          >
            <MapPin className="w-3.5 h-3.5 text-cyan-400" />
            <span>Target Gauge Station (20 Western Ghats)</span>
          </label>
          <select
            id="station-select"
            value={selectedStationId}
            onChange={(e) => onSelectStation && onSelectStation(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 font-medium focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition cursor-pointer"
          >
            {stations.map((s) => (
              <option key={s.station_id} value={s.station_id} className="bg-slate-900 text-slate-200">
                {s.name} ({s.station_id}) — {s.river} River, {s.district}
              </option>
            ))}
          </select>
          <span className="text-[10px] text-slate-500 font-mono px-1">
            Lat: {currentStation.lat?.toFixed(3)}°N • Lng: {currentStation.lng?.toFixed(3)}°E • Basin: {currentStation.basin}
          </span>
        </div>

        {/* Date Picker */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <label
              htmlFor="date-input"
              className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5"
            >
              <Calendar className="w-3.5 h-3.5 text-cyan-400" />
              <span>Observation Target Date</span>
            </label>
            <button
              type="button"
              onClick={() => onDateChange && onDateChange(new Date().toISOString().split('T')[0])}
              className="text-[10px] font-mono text-cyan-400 hover:underline"
            >
              Today
            </button>
          </div>
          <input
            id="date-input"
            type="date"
            value={selectedDate}
            onChange={(e) => onDateChange && onDateChange(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition cursor-pointer"
          />
          <span className="text-[10px] text-slate-500 px-1">
            {isLive ? 'Live satellite & gauge alignment' : 'Historical replay & synthetic date marker'}
          </span>
        </div>
      </div>

      {/* 4. Mode-Dependent Settings Section */}
      {isLive ? (
        /* Mode A: Live Weather Status Card */
        <div className="p-3.5 rounded-xl bg-blue-950/20 border border-blue-800/40 text-xs text-slate-300 flex items-start gap-3">
          <div className="p-2 rounded-lg bg-blue-900/40 text-blue-400 shrink-0">
            <CloudRain className="w-4 h-4" />
          </div>
          <div className="space-y-1">
            <h4 className="font-bold text-white flex items-center gap-1.5">
              <span>Open-Meteo Telemetry Stream Synchronized</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            </h4>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Retrieving high-resolution 10-day rainfall observations via open-meteo.com API for coordinate{' '}
              <span className="font-mono text-cyan-300">
                ({currentStation.lat?.toFixed(2)}, {currentStation.lng?.toFixed(2)})
              </span>
              . Predictions calibrate against antecedent catchment moisture.
            </p>
          </div>
        </div>
      ) : (
        /* Mode B: Manual Simulation Rainfall Sliders & Number Inputs */
        <div className="p-4 rounded-xl bg-slate-950/80 border border-amber-800/50 flex flex-col gap-3.5">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800">
            <span className="text-xs font-bold text-amber-300 flex items-center gap-1.5">
              <Droplets className="w-4 h-4 text-amber-400" />
              <span>Antecedent Rainfall Injection (0–1000 mm)</span>
            </span>

            {/* Quick Presets */}
            <div className="flex items-center gap-1">
              {[
                { id: 'lull', label: 'Dry/Lull' },
                { id: 'moderate', label: 'Moderate' },
                { id: 'heavy', label: 'Heavy' },
                { id: 'cloudburst', label: 'Cloudburst' },
              ].map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handleApplyPreset(p.id)}
                  className={`text-[10px] font-semibold px-2 py-0.5 rounded border transition ${
                    activePreset === p.id
                      ? 'bg-amber-600 border-amber-500 text-white shadow'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Rainfall Sliders Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Input 1: 1-Day Rainfall */}
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-400">1-Day (T-1):</span>
                <span className="text-cyan-400 font-bold">{rainfallInputs.day_1} mm</span>
              </div>
              <input
                type="range"
                min="0"
                max="300"
                step="1"
                value={rainfallInputs.day_1}
                onChange={(e) => handleInputChange('day_1', e.target.value)}
                className="w-full accent-cyan-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
              />
              <input
                type="number"
                min="0"
                max="1000"
                value={rainfallInputs.day_1}
                onChange={(e) => handleInputChange('day_1', e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500"
              />
            </div>

            {/* Input 2: 3-Day Cumulative */}
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-400">3-Day Cum:</span>
                <span className="text-blue-400 font-bold">{rainfallInputs.day_3_cum} mm</span>
              </div>
              <input
                type="range"
                min="0"
                max="600"
                step="2"
                value={rainfallInputs.day_3_cum}
                onChange={(e) => handleInputChange('day_3_cum', e.target.value)}
                className="w-full accent-blue-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
              />
              <input
                type="number"
                min="0"
                max="1000"
                value={rainfallInputs.day_3_cum}
                onChange={(e) => handleInputChange('day_3_cum', e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs font-mono text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>

            {/* Input 3: 7-Day Cumulative */}
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-slate-400">7-Day Cum:</span>
                <span className="text-indigo-400 font-bold">{rainfallInputs.day_7_cum} mm</span>
              </div>
              <input
                type="range"
                min="0"
                max="1000"
                step="5"
                value={rainfallInputs.day_7_cum}
                onChange={(e) => handleInputChange('day_7_cum', e.target.value)}
                className="w-full accent-indigo-500 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
              />
              <input
                type="number"
                min="0"
                max="1000"
                value={rainfallInputs.day_7_cum}
                onChange={(e) => handleInputChange('day_7_cum', e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
        </div>
      )}

      {/* 5. Validation Error Banner */}
      {validationError && (
        <div className="p-3 rounded-xl bg-red-950/40 border border-red-800/60 text-xs text-red-300 flex items-center gap-2 shadow-md">
          <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
          <span>{validationError}</span>
        </div>
      )}

      {/* 6. Primary Action Button (CTA) */}
      <button
        type="button"
        onClick={handleSubmit}
        disabled={isLoading || Boolean(validationError)}
        className="w-full py-3 px-5 rounded-xl bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-bold text-sm tracking-wide transition shadow-lg shadow-cyan-950/50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 active:scale-[0.99]"
      >
        {isLoading ? (
          <>
            <RefreshCw className="w-4 h-4 animate-spin text-cyan-200" />
            <span>Running PRAVAH Hydro-Predictive Inference...</span>
          </>
        ) : (
          <>
            <Zap className="w-4 h-4 text-cyan-200" />
            <span>Check Flood Risk</span>
          </>
        )}
      </button>
    </div>
  );
}

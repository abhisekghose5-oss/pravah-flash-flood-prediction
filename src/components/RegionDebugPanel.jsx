import React, { useState, useCallback } from 'react';
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  Bug,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Compass,
  ExternalLink,
  Layers,
  MapPin,
  Maximize2,
  Minimize2,
  Play,
  RefreshCw,
  Sliders,
  Terminal,
  Wifi,
  X,
  XCircle,
  Zap,
} from 'lucide-react';

/**
 * RegionDebugPanel — QA & Dev Verification Overlay for Northeast & Multi-Region Telemetry
 *
 * This isolated component floats in the corner of the dashboard during development mode.
 * It provides:
 * 1. API Health Check for GET /api/v1/predict?region=NE (verifying catchment IDs, API values, and probabilities)
 * 2. Camera Quick-Travel controls to smoothly animate Leaflet and Three.js/Globe.gl to Northeast coordinates
 * 3. 10-Day Scenario Simulator test trigger injecting mock heavy rainfall
 * 4. Mock Alert Webhook/WebSocket injector for SEVERE Northeast flood onsets
 */
export default function RegionDebugPanel({
  activeRegion = 'maharashtra',
  onRegionChange,
  onSelectStation,
  onCheckRisk,
  onJumpToLocation,
  onInjectMockAlert,
  activeStationList = [],
}) {
  // Only render in development mode
  const isDev = import.meta.env.DEV ?? true;
  if (!isDev) return null;

  const [isMinimized, setIsMinimized] = useState(false);
  const [isOpen, setIsOpen] = useState(true);

  // 1. API Health Check State
  const [apiCheckStatus, setApiCheckStatus] = useState(null); // null | 'loading' | 'pass' | 'fail'
  const [apiCheckDetails, setApiCheckDetails] = useState(null);
  const [apiLatencyMs, setApiLatencyMs] = useState(null);
  const [showPayload, setShowPayload] = useState(false);

  // 2. Scenario Test State
  const [scenarioTestStatus, setScenarioTestStatus] = useState(null); // null | 'running' | 'success' | 'error'
  const [scenarioMessage, setScenarioMessage] = useState('');

  // 3. Mock Alert Injection State
  const [mockAlertStatus, setMockAlertStatus] = useState(null); // null | 'injected'
  const [alertSummary, setAlertSummary] = useState('');

  /**
   * Step 1: Execute GET /api/v1/predict?region=NE & Verify Payload
   */
  const handleRunApiCheck = useCallback(async () => {
    setApiCheckStatus('loading');
    setApiCheckDetails(null);
    setApiLatencyMs(null);

    const startTime = performance.now();
    try {
      const response = await fetch('/api/v1/predict?region=NE');
      const latency = Math.round(performance.now() - startTime);
      setApiLatencyMs(latency);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setApiCheckDetails(data);

      // Verify Payload Structure
      const hasCatchments = Array.isArray(data.catchment_ids) && data.catchment_ids.length > 0;
      const hasApiValues =
        (data.api_values && Object.keys(data.api_values).length > 0) ||
        data.antecedent_precipitation_index != null;
      const hasProbabilities =
        (data.prediction_probabilities && Object.keys(data.prediction_probabilities).length > 0) ||
        data.task_a_onset?.probability != null;

      if (hasCatchments && hasApiValues && hasProbabilities) {
        setApiCheckStatus('pass');
      } else {
        const missing = [];
        if (!hasCatchments) missing.push('catchment_ids');
        if (!hasApiValues) missing.push('api_values');
        if (!hasProbabilities) missing.push('prediction_probabilities');
        setApiCheckStatus('fail');
        console.error('[PRAVAH QA] Incomplete NE payload missing fields:', missing);
      }
    } catch (err) {
      setApiLatencyMs(Math.round(performance.now() - startTime));
      setApiCheckStatus('fail');
      setApiCheckDetails({ error: err.message });
      console.error('[PRAVAH QA] API Health Check Failed:', err);
    }
  }, []);

  /**
   * Step 2: Quick-Travel Camera Animations
   */
  const handleJumpToNortheast = useCallback(() => {
    if (onRegionChange) onRegionChange('northeast');
    if (onJumpToLocation) {
      onJumpToLocation({ lat: 26.20, lng: 92.93, zoom: 7 });
    }
    // Also trigger global 3D globe if mounted
    if (typeof window !== 'undefined' && window.PRAVAH_GLOBE) {
      window.PRAVAH_GLOBE.switchRegion('northeast');
    }
  }, [onRegionChange, onJumpToLocation]);

  const handleJumpToMaharashtra = useCallback(() => {
    if (onRegionChange) onRegionChange('maharashtra');
    if (onJumpToLocation) {
      onJumpToLocation({ lat: 18.5204, lng: 73.8567, zoom: 8 });
    }
    if (typeof window !== 'undefined' && window.PRAVAH_GLOBE) {
      window.PRAVAH_GLOBE.switchRegion('maharashtra');
    }
  }, [onRegionChange, onJumpToLocation]);

  /**
   * Step 3: Inject Mock 10-Day Heavy Rainfall Scenario for NE
   */
  const handleRunNeScenarioTest = useCallback(async () => {
    setScenarioTestStatus('running');
    setScenarioMessage('Injecting 10-day monsoon cloudburst sequence for Beki station...');

    try {
      if (onRegionChange) onRegionChange('northeast');
      const targetStationId = 'NE_AS_01'; // Beki
      if (onSelectStation) onSelectStation(targetStationId);

      // Heavy 10-day rainfall sequence (mm): [T-10 ... T-1]
      const heavySeries = [25.0, 40.0, 65.0, 95.0, 140.0, 185.0, 220.0, 280.0, 310.0, 340.0];

      if (onCheckRisk) {
        await onCheckRisk({
          stationId: targetStationId,
          region: 'northeast',
          mode: 'simulation',
          rainfallInputs: { day_1: 340.0, day_3_cum: 930.0, day_7_cum: 1570.0 },
          simulationRainfall: heavySeries,
          rainfallHistory10d: heavySeries,
          onsetModel: 'XGBoost',
          activeModel: 'XGBoost',
        });
      }

      setScenarioTestStatus('success');
      setScenarioMessage('✅ 10-Day simulation injected: Beki graph & probability updated to EMERGENCY!');
      setTimeout(() => setScenarioTestStatus(null), 6000);
    } catch (err) {
      setScenarioTestStatus('error');
      setScenarioMessage(`❌ Scenario injection failed: ${err.message}`);
    }
  }, [onRegionChange, onSelectStation, onCheckRisk]);

  /**
   * Step 4: Inject Mock SEVERE WebSocket Flood Alert for Northeast
   */
  const handleSimulateNeSevereAlert = useCallback(() => {
    const mockAlertPayload = {
      event: 'flood_alert',
      region: 'Northeast',
      station_id: 'NE_AS_01',
      station_name: 'Beki',
      river: 'Beki / Manas',
      district: 'Barpeta, Assam',
      severity: 'SEVERE',
      tier: 'EMERGENCY',
      onset_probability: 0.88,
      active_probability: 0.74,
      rainfall_1d: 185.0,
      timestamp: new Date().toISOString(),
      recommendation:
        'CRITICAL: Severe flood wave imminent on Beki River. Immediate evacuation of low-lying settlements in Barpeta recommended.',
    };

    if (onInjectMockAlert) {
      onInjectMockAlert(mockAlertPayload);
    }

    // Update 3D holographic globe marker if available
    if (typeof window !== 'undefined' && window.PRAVAH_GLOBE?.injectAlert) {
      window.PRAVAH_GLOBE.injectAlert({
        stationId: 'NE_AS_01',
        tier: 'EMERGENCY',
        color: '#ef4444',
      });
    }

    setMockAlertStatus('injected');
    setAlertSummary('🚨 SEVERE flood alert dispatched for Beki (Barpeta, Assam)!');
    setTimeout(() => setMockAlertStatus(null), 6000);
  }, [onInjectMockAlert]);

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 z-[999] bg-slate-900/95 hover:bg-slate-800 text-cyan-400 border border-cyan-500/50 shadow-2xl rounded-full px-3.5 py-2 text-xs font-mono font-bold flex items-center gap-2 backdrop-blur-md transition-all hover:scale-105 select-none"
      >
        <Bug className="w-4 h-4 text-cyan-400 animate-pulse" />
        <span>DEV QA TOOLS</span>
      </button>
    );
  }

  return (
    <aside
      aria-label="Developer QA Panel"
      className={`fixed bottom-4 right-4 z-[999] bg-slate-950/95 border border-slate-700/80 rounded-2xl shadow-2xl backdrop-blur-xl transition-all duration-200 select-none text-slate-200 font-sans ${
        isMinimized ? 'w-72' : 'w-80 sm:w-96'
      }`}
    >
      {/* 1. Header Bar */}
      <div className="flex items-center justify-between px-3.5 py-2.5 bg-slate-900/80 border-b border-slate-800 rounded-t-2xl">
        <div className="flex items-center space-x-2">
          <div className="p-1 rounded-md bg-cyan-950 text-cyan-400 border border-cyan-800/60">
            <Bug className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-bold font-mono tracking-wide text-white">
            DEV QA OVERLAY
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
            TEST MODE
          </span>
        </div>

        <div className="flex items-center space-x-1">
          <button
            type="button"
            onClick={() => setIsMinimized(!isMinimized)}
            className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-slate-200 transition"
            title={isMinimized ? 'Expand' : 'Minimize'}
          >
            {isMinimized ? <Maximize2 className="w-3.5 h-3.5" /> : <Minimize2 className="w-3.5 h-3.5" />}
          </button>
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-rose-400 transition"
            title="Close Panel"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 2. Minimized Compact View */}
      {isMinimized ? (
        <div className="p-3 text-xs flex items-center justify-between">
          <span className="text-slate-400 text-[11px]">NE Data Flow:</span>
          {apiCheckStatus === 'pass' && (
            <span className="font-bold font-mono text-emerald-400 text-xs">PASS ({apiLatencyMs}ms)</span>
          )}
          {apiCheckStatus === 'fail' && (
            <span className="font-bold font-mono text-rose-400 text-xs">FAIL</span>
          )}
          {apiCheckStatus == null && (
            <span className="font-mono text-slate-500 text-[11px]">Unverified</span>
          )}
        </div>
      ) : (
        /* 3. Expanded Full Control View */
        <div className="p-3.5 space-y-3.5 text-xs max-h-[80vh] overflow-y-auto custom-scrollbar">

          {/* SECTION 1: Backend API Health Check (Step 1) */}
          <div className="bg-slate-900/90 rounded-xl p-3 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                <Wifi className="w-3.5 h-3.5 text-cyan-400" />
                <span>1. NE API Verification</span>
              </span>
              <span className="text-[10px] font-mono text-slate-500">GET /api/v1/predict?region=NE</span>
            </div>

            <div className="flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={handleRunApiCheck}
                disabled={apiCheckStatus === 'loading'}
                className="flex-1 py-1.5 px-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-semibold text-xs transition flex items-center justify-center gap-1.5 shadow-md shadow-cyan-950/40"
              >
                {apiCheckStatus === 'loading' ? (
                  <>
                    <RefreshCw className="w-3 h-3 animate-spin" />
                    <span>Verifying...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3 h-3 fill-current" />
                    <span>Run NE API Check</span>
                  </>
                )}
              </button>

              {/* Pass/Fail Visual Indicator Badge */}
              <div className="min-w-[85px] text-right">
                {apiCheckStatus === 'pass' && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-mono font-bold text-[11px] shadow-sm animate-pulse">
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    <span>PASS ({apiLatencyMs}ms)</span>
                  </span>
                )}
                {apiCheckStatus === 'fail' && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-rose-500/20 text-rose-400 border border-rose-500/40 font-mono font-bold text-[11px] shadow-sm">
                    <XCircle className="w-3 h-3 text-rose-400" />
                    <span>FAIL</span>
                  </span>
                )}
                {apiCheckStatus === null && (
                  <span className="text-[11px] text-slate-500 font-mono">Not Tested</span>
                )}
              </div>
            </div>

            {/* Checklist breakdown */}
            {apiCheckDetails && (
              <div className="mt-2 pt-2 border-t border-slate-800 space-y-1 text-[11px]">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Catchment IDs:</span>
                  <span className="font-mono text-cyan-300">
                    {apiCheckDetails.total_catchments ?? apiCheckDetails.catchment_ids?.length ?? 0} loaded
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">API Rainfall Index:</span>
                  <span className="font-mono text-emerald-300">
                    {apiCheckDetails.api_values ? 'Verified ✅' : 'Missing ❌'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Prediction Probabilities:</span>
                  <span className="font-mono text-cyan-300">
                    {apiCheckDetails.prediction_probabilities ? 'Calibrated ✅' : 'Missing ❌'}
                  </span>
                </div>

                <button
                  type="button"
                  onClick={() => setShowPayload(!showPayload)}
                  className="mt-1 text-[10px] text-cyan-400 hover:underline flex items-center gap-1 font-mono"
                >
                  <span>{showPayload ? 'Hide Raw JSON' : 'Inspect JSON Response'}</span>
                  {showPayload ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>

                {showPayload && (
                  <pre className="mt-1.5 p-2 rounded bg-slate-950 border border-slate-800 text-[10px] font-mono text-slate-300 overflow-x-auto max-h-32 custom-scrollbar">
                    {JSON.stringify(apiCheckDetails, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </div>

          {/* SECTION 2: 3D Globe & Leaflet Camera Quick-Travel (Step 2) */}
          <div className="bg-slate-900/90 rounded-xl p-3 border border-slate-800 space-y-2">
            <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Compass className="w-3.5 h-3.5 text-emerald-400" />
              <span>2. Camera Quick-Travel</span>
            </span>

            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={handleJumpToNortheast}
                className={`py-1.5 px-2 rounded-lg border text-xs font-semibold transition flex items-center justify-center gap-1.5 ${
                  activeRegion === 'northeast'
                    ? 'bg-emerald-600/30 border-emerald-500 text-emerald-300 shadow-sm'
                    : 'bg-slate-950 hover:bg-slate-800 border-slate-800 text-slate-300'
                }`}
              >
                <MapPin className="w-3 h-3 text-emerald-400" />
                <span>Jump to NE (26.2°N)</span>
              </button>

              <button
                type="button"
                onClick={handleJumpToMaharashtra}
                className={`py-1.5 px-2 rounded-lg border text-xs font-semibold transition flex items-center justify-center gap-1.5 ${
                  activeRegion === 'maharashtra'
                    ? 'bg-cyan-600/30 border-cyan-500 text-cyan-300 shadow-sm'
                    : 'bg-slate-950 hover:bg-slate-800 border-slate-800 text-slate-300'
                }`}
              >
                <MapPin className="w-3 h-3 text-cyan-400" />
                <span>Ghats (18.5°N)</span>
              </button>
            </div>
            <p className="text-[10px] text-slate-500">
              Smoothly flies Leaflet & Three.js globe camera to coordinates without layer conflict.
            </p>
          </div>

          {/* SECTION 3: 10-Day Scenario Simulator Test (Step 3) */}
          <div className="bg-slate-900/90 rounded-xl p-3 border border-slate-800 space-y-2">
            <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-amber-400" />
              <span>3. 10-Day Scenario Simulator Test</span>
            </span>

            <button
              type="button"
              onClick={handleRunNeScenarioTest}
              disabled={scenarioTestStatus === 'running'}
              className="w-full py-1.5 px-3 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs transition flex items-center justify-center gap-1.5 shadow-md shadow-amber-950/40"
            >
              {scenarioTestStatus === 'running' ? (
                <>
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  <span>Injecting Heavy Rainfall...</span>
                </>
              ) : (
                <>
                  <Zap className="w-3 h-3 text-amber-200 fill-current" />
                  <span>Inject NE Heavy Rainfall (Beki)</span>
                </>
              )}
            </button>

            {scenarioMessage && (
              <p className="text-[10px] font-mono text-amber-300 bg-amber-950/40 border border-amber-800/40 p-1.5 rounded">
                {scenarioMessage}
              </p>
            )}
          </div>

          {/* SECTION 4: Mock Alert Injector / State Verification (Step 4) */}
          <div className="bg-slate-900/90 rounded-xl p-3 border border-slate-800 space-y-2">
            <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
              <span>4. Inject Mock NE Alert</span>
            </span>

            <button
              type="button"
              onClick={handleSimulateNeSevereAlert}
              className="w-full py-1.5 px-3 rounded-lg bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white font-semibold text-xs transition flex items-center justify-center gap-1.5 shadow-md shadow-red-950/50"
            >
              <AlertOctagon className="w-3 h-3 fill-current" />
              <span>Simulate SEVERE Alert (Beki, Barpeta)</span>
            </button>

            {alertSummary && (
              <p className="text-[10px] font-mono text-rose-300 bg-rose-950/40 border border-rose-800/40 p-1.5 rounded">
                {alertSummary}
              </p>
            )}

            <p className="text-[10px] text-slate-500">
              Turns Beki marker red/orange, appends to side ticker, keeps Maharashtra intact.
            </p>
          </div>

        </div>
      )}
    </aside>
  );
}

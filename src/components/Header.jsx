import React from 'react';
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  Calendar,
  CheckCircle2,
  Clock,
  Radio,
  RefreshCw,
  SlidersHorizontal,
  Waves,
} from 'lucide-react';

/**
 * Header Component for PRAVAH Flash Flood Early Warning Dashboard
 *
 * @param {Object} props
 * @param {'live' | 'simulation'} [props.mode='live'] Current operating mode
 * @param {(mode: 'live' | 'simulation') => void} props.onModeChange Callback when mode changes
 * @param {string} [props.selectedDate] Current date (used in simulation mode)
 * @param {(date: string) => void} [props.onDateChange] Callback when date changes in simulation mode
 * @param {{ emergency?: number, warning?: number, advisory?: number, normal?: number }} [props.stats]
 * @param {() => void} [props.onRefresh] Trigger telemetry refresh
 * @param {boolean} [props.isLoading=false] Loading state during refresh
 */
export default function Header({
  mode = 'live',
  onModeChange,
  selectedDate = new Date().toISOString().split('T')[0],
  onDateChange,
  stats = { emergency: 2, warning: 5, advisory: 6, normal: 7 },
  onRefresh,
  isLoading = false,
}) {
  const isLive = mode === 'live';

  return (
    <header className="w-full bg-slate-950 border-b border-slate-800 text-slate-100 sticky top-0 z-50 shadow-md">
      {/* Top Banner / Ticker */}
      <div className="max-w-[1920px] mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-4">
        
        {/* Brand & Region Identification */}
        <div className="flex items-center space-x-3.5">
          <div className="relative flex items-center justify-center w-11 h-11 rounded-xl bg-gradient-to-tr from-cyan-600 via-blue-600 to-indigo-700 shadow-lg shadow-blue-500/20 ring-1 ring-white/20">
            <Waves className="w-6 h-6 text-white animate-pulse" />
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isLive ? 'bg-emerald-400' : 'bg-amber-400'}`} />
              <span className={`relative inline-flex rounded-full h-3 w-3 ${isLive ? 'bg-emerald-500' : 'bg-amber-500'}`} />
            </span>
          </div>

          <div>
            <div className="flex items-center space-x-2.5">
              <h1 className="text-xl font-black tracking-wider uppercase bg-gradient-to-r from-cyan-400 via-blue-200 to-white bg-clip-text text-transparent font-mono">
                PRAVAH
              </h1>
              <span className="text-[10px] uppercase font-bold tracking-widest px-2 py-0.5 rounded bg-blue-950/80 text-blue-300 border border-blue-800/60">
                v1.0 EOC
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium flex items-center gap-1.5">
              <span>Flash-Flood Early Warning System</span>
              <span className="text-slate-600">•</span>
              <span className="text-slate-300">Maharashtra Western Ghats</span>
            </p>
          </div>
        </div>

        {/* Center: Real-time Telemetry Status & Stats Pills */}
        <div className="hidden xl:flex items-center space-x-3">
          {/* Telemetry Status Badge */}
          <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full border text-xs font-semibold tracking-wide uppercase transition-colors ${
            isLive
              ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-400 shadow-sm shadow-emerald-900/30'
              : 'bg-amber-950/40 border-amber-500/30 text-amber-400 shadow-sm shadow-amber-900/30'
          }`}>
            <Radio className={`w-3.5 h-3.5 ${isLive ? 'animate-pulse text-emerald-400' : 'text-amber-400'}`} />
            <span>{isLive ? 'Live Sensor Telemetry: Active' : 'Simulation Sandbox: Offline Replay'}</span>
          </div>

          {/* Quick Risk Tier Counters */}
          <div className="flex items-center space-x-1.5 bg-slate-900/80 px-2.5 py-1 rounded-full border border-slate-800 text-xs">
            <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-red-950/60 border border-red-800/60 text-red-400 font-mono font-semibold" title="Emergency Catchments">
              <AlertOctagon className="w-3 h-3 text-red-500" />
              <span>{stats.emergency || 0}</span>
            </span>
            <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-amber-950/60 border border-amber-800/60 text-amber-400 font-mono font-semibold" title="Warning Catchments">
              <AlertTriangle className="w-3 h-3 text-amber-500" />
              <span>{stats.warning || 0}</span>
            </span>
            <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-yellow-950/60 border border-yellow-800/60 text-yellow-300 font-mono font-semibold" title="Advisory Catchments">
              <Activity className="w-3 h-3 text-yellow-400" />
              <span>{stats.advisory || 0}</span>
            </span>
            <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/60 text-emerald-400 font-mono font-semibold" title="Normal Catchments">
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              <span>{stats.normal || 0}</span>
            </span>
          </div>
        </div>

        {/* Right: Operational Mode Switcher & Controls */}
        <div className="flex items-center space-x-3">
          
          {/* Mode Switcher Segmented Control */}
          <div className="bg-slate-900/90 p-1 rounded-xl border border-slate-800 flex items-center space-x-1">
            <button
              type="button"
              onClick={() => onModeChange && onModeChange('live')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                isLive
                  ? 'bg-cyan-600 text-white shadow-md shadow-cyan-900/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Radio className="w-3.5 h-3.5" />
              <span>Live Mode</span>
            </button>

            <button
              type="button"
              onClick={() => onModeChange && onModeChange('simulation')}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                !isLive
                  ? 'bg-amber-600 text-white shadow-md shadow-amber-900/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Simulation / Historical</span>
            </button>
          </div>

          {/* Date Picker (in Simulation Mode) */}
          {!isLive && (
            <div className="flex items-center space-x-1.5 bg-slate-900 px-2.5 py-1.5 rounded-lg border border-amber-700/60 text-xs">
              <Calendar className="w-3.5 h-3.5 text-amber-400" />
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => onDateChange && onDateChange(e.target.value)}
                className="bg-transparent text-slate-200 outline-none font-mono text-xs cursor-pointer"
              />
            </div>
          )}

          {/* Refresh Action Button */}
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              disabled={isLoading}
              title="Refresh telemetry"
              className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          )}

          {/* Clock Display */}
          <div className="hidden sm:flex items-center space-x-1.5 text-xs text-slate-400 bg-slate-900/60 px-3 py-1.5 rounded-lg border border-slate-800/80 font-mono">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span>IST / UTC</span>
          </div>
        </div>

      </div>

      {/* Mobile Sub-Header Ticker */}
      <div className="xl:hidden px-4 py-1.5 bg-slate-900/90 border-t border-slate-800/70 flex items-center justify-between text-xs text-slate-400">
        <div className="flex items-center space-x-2">
          <span className={`inline-block w-2 h-2 rounded-full ${isLive ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
          <span className="font-medium text-[11px]">
            {isLive ? 'Live Telemetry' : 'Simulation Mode'}
          </span>
        </div>
        <div className="flex items-center space-x-2 font-mono text-[11px]">
          <span className="text-red-400 font-bold">{stats.emergency} Emer</span>
          <span className="text-amber-400 font-bold">{stats.warning} Warn</span>
          <span className="text-yellow-300 font-bold">{stats.advisory} Adv</span>
          <span className="text-emerald-400 font-bold">{stats.normal} Norm</span>
        </div>
      </div>
    </header>
  );
}

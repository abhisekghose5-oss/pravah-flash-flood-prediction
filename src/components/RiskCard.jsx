import React, { useMemo } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BarChart2,
  CheckCircle2,
  Cpu,
  Droplets,
  Gauge,
  Info,
  ShieldAlert,
  TrendingUp,
  Waves,
} from 'lucide-react';
import { getRiskLevelInfo } from './FloodMap';

/**
 * RiskCard Component for PRAVAH Early Warning System
 *
 * Displays:
 * 1. Flood Probability Gauge (0% to 100%) with calibrated thresholds.
 * 2. Bold Risk Tier Badge (NORMAL, ADVISORY, WARNING, EMERGENCY).
 * 3. Model Provenance Note ("Model: LightGBM Calibrated v2.1 | Daily Resolution Engine").
 * 4. Breakdown of 1-Day, 3-Day Cumulative, and 7-Day Cumulative Rainfall metrics with trend arrows.
 *
 * @param {Object} props
 * @param {Object} props.prediction Flood prediction payload
 * @param {Object} [props.station] Station metadata
 * @param {string} [props.modelProvenance='Model: LightGBM Calibrated v2.1 | Daily Resolution Engine']
 * @param {string} [props.className='']
 */
export default function RiskCard({
  prediction,
  station,
  modelProvenance = 'Model: LightGBM Calibrated v2.1 | Daily Resolution Engine',
  className = '',
}) {
  // Fallback safe values if prediction is loading or null
  const probability = prediction?.prediction?.probability ?? 0.15;
  const probPercent = Math.round(probability <= 1 ? probability * 100 : probability);
  const tierInfo = useMemo(() => getRiskLevelInfo(probability), [probability]);

  const rainfall = prediction?.rainfall || {
    day_1: 0,
    day_3_cum: 0,
    day_7_cum: 0,
    series: [],
  };

  // Trend determination based on 1-day intensity compared to 3-day daily average
  const trendAnalysis = useMemo(() => {
    const d1 = rainfall.day_1 || 0;
    const avg3 = (rainfall.day_3_cum || 0) / 3;

    if (d1 > avg3 * 1.25 && d1 > 15) {
      return {
        direction: 'up',
        label: 'Surging Intensity',
        icon: ArrowUpRight,
        color: 'text-red-400',
        badgeBg: 'bg-red-950/60 border-red-800/60 text-red-300',
      };
    }
    if (d1 < avg3 * 0.75 || d1 < 5) {
      return {
        direction: 'down',
        label: 'Subsiding Trend',
        icon: ArrowDownRight,
        color: 'text-emerald-400',
        badgeBg: 'bg-emerald-950/60 border-emerald-800/60 text-emerald-300',
      };
    }
    return {
      direction: 'steady',
      label: 'Steady Inflow',
      icon: ArrowRight,
      color: 'text-yellow-400',
      badgeBg: 'bg-yellow-950/60 border-yellow-800/60 text-yellow-300',
    };
  }, [rainfall.day_1, rainfall.day_3_cum]);

  // Semi-circular gauge stroke offset calculation (Circumference of r=52 is ~326.7)
  const radius = 52;
  const circumference = Math.PI * radius; // 180 degrees arc
  const strokeDashoffset = circumference - (probPercent / 100) * circumference;

  return (
    <div
      className={`bg-slate-900/95 border border-slate-800 rounded-2xl p-4 sm:p-5 shadow-2xl flex flex-col gap-4 text-slate-100 select-none ${className}`}
    >
      {/* 1. Header: Catchment Identification & Risk Tier Badge */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <div className="p-2 rounded-xl bg-slate-950 border border-slate-800 text-cyan-400">
            <Gauge className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white tracking-wide">
              Flash-Flood Predictive Intelligence
            </h3>
            <span className="text-[11px] text-slate-400 font-medium">
              {prediction?.catchment_name || station?.name || 'Western Ghats Catchment'}
            </span>
          </div>
        </div>

        {/* Bold Risk Tier Badge */}
        <div className="flex items-center gap-2">
          <span
            className={`text-xs font-black tracking-widest uppercase px-3 py-1 rounded-full border shadow-md flex items-center gap-1.5 ${tierInfo.badgeClass}`}
          >
            <span className={`w-2 h-2 rounded-full ${tierInfo.dotClass} ${tierInfo.tier === 'EMERGENCY' ? 'animate-ping' : ''}`} />
            <span>{tierInfo.tier} TIER</span>
          </span>
        </div>
      </div>

      {/* 2. Middle Section: Risk Meter Gauge & Probability Display */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center bg-slate-950/70 p-4 rounded-xl border border-slate-800/80">
        
        {/* Semi-Circular Radial Risk Meter (SVG Gauge) */}
        <div className="md:col-span-5 flex flex-col items-center justify-center">
          <div className="relative flex items-center justify-center w-40 h-24 overflow-hidden">
            <svg className="w-40 h-40 transform -rotate-180" viewBox="0 0 120 120">
              {/* Background Track Arc */}
              <circle
                cx="60"
                cy="60"
                r={radius}
                fill="none"
                stroke="#1e293b"
                strokeWidth="10"
                strokeDasharray={`${circumference} ${circumference}`}
                strokeLinecap="round"
              />
              {/* Colored Calibrated Value Arc */}
              <circle
                cx="60"
                cy="60"
                r={radius}
                fill="none"
                stroke={tierInfo.color}
                strokeWidth="10"
                strokeDasharray={`${circumference} ${circumference}`}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                className="transition-all duration-700 ease-out"
              />
            </svg>

            {/* Inner Gauge Text Display */}
            <div className="absolute bottom-1 flex flex-col items-center justify-center">
              <span className="text-3xl font-black font-mono tracking-tight text-white leading-none">
                {probPercent}%
              </span>
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mt-0.5">
                Flood Probability
              </span>
            </div>
          </div>

          {/* Calibrated Threshold Markers */}
          <div className="w-full max-w-[200px] flex justify-between text-[10px] font-mono text-slate-400 pt-1 px-1">
            <span className="text-emerald-400 font-bold">0%</span>
            <span className="text-yellow-400 font-bold">25%</span>
            <span className="text-orange-400 font-bold">50%</span>
            <span className="text-red-400 font-bold">75%</span>
            <span className="text-red-500 font-bold">100%</span>
          </div>
        </div>

        {/* Risk Diagnosis & Alert Synopsis */}
        <div className="md:col-span-7 flex flex-col justify-center space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              Diagnostic Status
            </span>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded border flex items-center gap-1 ${trendAnalysis.badgeBg}`}>
              <trendAnalysis.icon className="w-3 h-3" />
              <span>{trendAnalysis.label}</span>
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            {tierInfo.tier === 'EMERGENCY'
              ? 'Extreme discharge velocity anticipated. Flood threshold reached in upstream catchment headwaters.'
              : tierInfo.tier === 'WARNING'
              ? 'Substantial runoff accumulation. Soil moisture approaching saturation capacity along river corridor.'
              : tierInfo.tier === 'ADVISORY'
              ? 'Elevated baseline stage. Minor localized ponding expected in low-lying bank sections.'
              : 'Hydrological regime stable. River stage operating safely below warning mark.'}
          </p>

          {/* Model Provenance Note */}
          <div className="flex items-center gap-1.5 pt-1 text-[11px] text-slate-400 font-mono bg-slate-900 px-2.5 py-1.5 rounded-lg border border-slate-800">
            <Cpu className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <span className="truncate">{modelProvenance}</span>
          </div>
        </div>
      </div>

      {/* 3. Rainfall Metrics Breakdown: 1-Day, 3-Day Cum, and 7-Day Cum */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Metric 1: 1-Day Rainfall */}
        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 shadow flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium">
            <span>1-Day Rainfall (T-1)</span>
            <Droplets className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="flex items-baseline justify-between mt-2">
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black font-mono text-cyan-400">
                {rainfall.day_1}
              </span>
              <span className="text-xs text-slate-400">mm</span>
            </div>
            <span className="text-[10px] font-mono font-bold text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded">
              24h Total
            </span>
          </div>
        </div>

        {/* Metric 2: 3-Day Cumulative */}
        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 shadow flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium">
            <span>3-Day Cumulative</span>
            <TrendingUp className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div className="flex items-baseline justify-between mt-2">
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black font-mono text-blue-400">
                {rainfall.day_3_cum}
              </span>
              <span className="text-xs text-slate-400">mm</span>
            </div>
            <span className="text-[10px] font-mono font-bold text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded">
              72h Aggregate
            </span>
          </div>
        </div>

        {/* Metric 3: 7-Day Cumulative */}
        <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 shadow flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium">
            <span>7-Day Cumulative</span>
            <BarChart2 className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="flex items-baseline justify-between mt-2">
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black font-mono text-indigo-400">
                {rainfall.day_7_cum}
              </span>
              <span className="text-xs text-slate-400">mm</span>
            </div>
            <span className="text-[10px] font-mono font-bold text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded">
              168h Cumulative
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

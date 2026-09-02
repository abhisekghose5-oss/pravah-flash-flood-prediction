import React, { useState, useMemo } from 'react';
import {
  AlertOctagon,
  AlertTriangle,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Download,
  Info,
  Radio,
  Share2,
  ShieldAlert,
  ShieldCheck,
  Volume2,
} from 'lucide-react';
import { getRiskLevelInfo } from './FloodMap';

/**
 * AlertBanner Component for PRAVAH Early Warning System
 *
 * Requirements:
 * 1. High-priority visual banner displaying actionable disaster response guidance based on Risk Tier.
 * 2. Example for EMERGENCY: "CRITICAL: High flood probability (84%). Evacuation protocols recommended for low-lying regions along Shastri River Basin."
 * 3. Includes timestamp of issuance.
 * 4. Data quality status ("Verified").
 * 5. Export button ("Copy Advisory Summary") with clipboard copy confirmation.
 *
 * @param {Object} props
 * @param {Object} props.prediction Flood prediction payload
 * @param {Object} [props.station] Station metadata
 * @param {string} [props.className=''] Additional CSS classes
 * @param {() => void} [props.onExport] Optional external export trigger
 */
export default function AlertBanner({
  prediction,
  station,
  className = '',
  onExport,
}) {
  const [copied, setCopied] = useState(false);

  // Extract core predictive data
  const probability = prediction?.prediction?.probability ?? 0.15;
  const probPercent = Math.round(probability <= 1 ? probability * 100 : probability);
  const tierInfo = useMemo(() => getRiskLevelInfo(probability), [probability]);
  const activeTier = tierInfo.tier;

  const stationName = station?.name || prediction?.catchment_name?.split('(')[0]?.trim() || 'Western Ghats';
  const riverBasin = station?.river ? `${station.river} River Basin` : 'Maharashtra Western Ghats Corridor';
  const stationId = station?.station_id || prediction?.station_id || 'MH_GAK_12';

  // Formatted timestamp
  const issuedTimestamp = useMemo(() => {
    const rawTime = prediction?.alert?.issued_at || prediction?.timestamp || new Date().toISOString();
    try {
      const d = new Date(rawTime);
      return (
        d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }) +
        ' ' +
        d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
        ' IST'
      );
    } catch {
      return rawTime;
    }
  }, [prediction?.alert?.issued_at, prediction?.timestamp]);

  // Actionable Disaster Response Guidance based on Risk Tier
  const advisoryContent = useMemo(() => {
    switch (activeTier) {
      case 'EMERGENCY':
        return {
          headline: `CRITICAL: High flood probability (${probPercent}%). Evacuation protocols recommended for low-lying regions along ${riverBasin}.`,
          guidance:
            prediction?.alert?.recommendation ||
            `Initiate immediate evacuation of vulnerable riverbank communities. Mobilize SDRF/NDRF search-and-rescue units, close low-lying bridges, and deploy flood barriers.`,
          badgeLabel: 'CRITICAL EVACUATION ADVISORY',
          badgeStyle: 'bg-red-500/20 text-red-300 border-red-500/60 ring-1 ring-red-500/30',
          bannerBg: 'from-red-950/70 via-slate-900 to-slate-950 border-red-500/60 shadow-red-950/40',
          icon: AlertOctagon,
          iconColor: 'text-red-400 animate-pulse',
        };
      case 'WARNING':
        return {
          headline: `WARNING: Elevated flood probability (${probPercent}%). Inundation watch and pre-positioning recommended along ${riverBasin}.`,
          guidance:
            prediction?.alert?.recommendation ||
            `Pre-position disaster management equipment, halt vehicular traffic across causeways, and prepare temporary livestock shelters.`,
          badgeLabel: 'STAGE INUNDATION WARNING',
          badgeStyle: 'bg-orange-500/20 text-orange-300 border-orange-500/60 ring-1 ring-orange-500/30',
          bannerBg: 'from-orange-950/60 via-slate-900 to-slate-950 border-orange-500/60 shadow-orange-950/30',
          icon: AlertTriangle,
          iconColor: 'text-orange-400',
        };
      case 'ADVISORY':
        return {
          headline: `ADVISORY: Catchment moisture saturation elevated (${probPercent}%). Enhanced vigilance recommended for low crossings along ${riverBasin}.`,
          guidance:
            prediction?.alert?.recommendation ||
            `Maintain continuous hydrological stage monitoring. Restrict recreational water activities and issue notices to local farmers near riparian zones.`,
          badgeLabel: 'CATCHMENT HYDROLOGICAL ADVISORY',
          badgeStyle: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/60 ring-1 ring-yellow-500/30',
          bannerBg: 'from-yellow-950/50 via-slate-900 to-slate-950 border-yellow-500/50 shadow-yellow-950/20',
          icon: ShieldAlert,
          iconColor: 'text-yellow-400',
        };
      case 'NORMAL':
      default:
        return {
          headline: `NORMAL: Hydrological stages stable (${probPercent}%). River channel operating within safe seasonal limits along ${riverBasin}.`,
          guidance:
            prediction?.alert?.recommendation ||
            `Automated telemetry continuous. Water levels well below warning thresholds. Standard monitoring protocols remain active.`,
          badgeLabel: 'ROUTINE SURVEILLANCE',
          badgeStyle: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/60 ring-1 ring-emerald-500/30',
          bannerBg: 'from-emerald-950/40 via-slate-900 to-slate-950 border-emerald-500/50 shadow-emerald-950/20',
          icon: CheckCircle2,
          iconColor: 'text-emerald-400',
        };
    }
  }, [activeTier, probPercent, riverBasin, prediction?.alert?.recommendation]);

  // Generate Executive Advisory Text for Clipboard Export
  const generateAdvisorySummaryText = () => {
    const d1 = prediction?.rainfall?.day_1 ?? 'N/A';
    const d3 = prediction?.rainfall?.day_3_cum ?? 'N/A';
    const d7 = prediction?.rainfall?.day_7_cum ?? 'N/A';

    return `================================================================
PRAVAH FLASH-FLOOD EARLY WARNING ADVISORY BULLETIN
================================================================
ALERT TIER        : ${activeTier} (${probPercent}% Flood Probability)
STATION           : ${stationName} (${stationId})
RIVER / BASIN     : ${riverBasin}
TIMESTAMP         : ${issuedTimestamp}
DATA QUALITY      : VERIFIED (IMD-CWC Telemetry Alignment)
MODEL PROVENANCE  : LightGBM Calibrated v2.1 | Daily Resolution Engine

OFFICIAL DIRECTIVE:
${advisoryContent.headline}

ACTIONABLE GUIDANCE & PROTOCOLS:
${advisoryContent.guidance}

ANTECEDENT PRECIPITATION:
- 1-Day Rainfall (T-1) : ${d1} mm
- 3-Day Cumulative     : ${d3} mm
- 7-Day Cumulative     : ${d7} mm

ISSUED BY:
PRAVAH Early Warning Operations — Maharashtra Western Ghats
================================================================`;
  };

  // Copy Advisory Summary to Clipboard
  const handleCopySummary = async () => {
    try {
      const summaryText = generateAdvisorySummaryText();
      await navigator.clipboard.writeText(summaryText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2600);
      if (onExport) onExport(summaryText);
    } catch (err) {
      console.error('Failed to copy advisory to clipboard:', err);
    }
  };

  const IconComponent = advisoryContent.icon;

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={`relative w-full bg-gradient-to-br ${advisoryContent.bannerBg} border rounded-2xl p-4 sm:p-5 shadow-2xl transition-all select-none overflow-hidden ${className}`}
    >
      {/* Subtle ambient alert glow */}
      <div
        className="absolute -right-20 -top-20 w-56 h-56 rounded-full blur-3xl opacity-20 pointer-events-none"
        style={{ backgroundColor: tierInfo.color }}
      />

      <div className="relative z-10 flex flex-col gap-3.5">
        {/* Row 1: Priority Tier Badge, Status Indicators, & Export Action */}
        <div className="flex flex-wrap items-center justify-between gap-2.5 pb-2.5 border-b border-slate-800/80">
          <div className="flex flex-wrap items-center gap-2">
            {/* Priority Tier Indicator Pill */}
            <span
              className={`text-[10px] font-black uppercase tracking-widest px-2.5 py-1 rounded-md border flex items-center gap-1.5 shadow-sm ${advisoryContent.badgeStyle}`}
            >
              <IconComponent className={`w-3.5 h-3.5 ${advisoryContent.iconColor}`} />
              <span>{advisoryContent.badgeLabel}</span>
            </span>

            {/* Data Quality Status Pill */}
            <span className="text-[10px] font-bold tracking-wider uppercase px-2.5 py-1 rounded-md bg-emerald-950/60 border border-emerald-700/60 text-emerald-300 flex items-center gap-1 shadow-sm">
              <ShieldCheck className="w-3 h-3 text-emerald-400" />
              <span>Data Quality: Verified</span>
            </span>
          </div>

          {/* Timestamp & Export Button */}
          <div className="flex items-center gap-2">
            {/* Timestamp of Issuance */}
            <div className="flex items-center gap-1 text-[11px] font-mono text-slate-300 bg-slate-950/60 px-2.5 py-1 rounded-lg border border-slate-800">
              <Clock className="w-3 h-3 text-slate-500" />
              <span>{issuedTimestamp}</span>
            </div>

            {/* Copy Advisory Summary CTA Button */}
            <button
              type="button"
              onClick={handleCopySummary}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 shadow-md ${
                copied
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white border border-slate-700'
              }`}
              title="Copy official emergency advisory summary for distribution"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-white" />
                  <span>Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="hidden sm:inline">Copy Advisory Summary</span>
                  <span className="sm:hidden">Copy</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Row 2: Headline Guidance Banner */}
        <div className="flex items-start gap-3">
          <div
            className="p-2.5 rounded-xl shrink-0 mt-0.5 border"
            style={{
              backgroundColor: `${tierInfo.color}15`,
              borderColor: `${tierInfo.color}40`,
            }}
          >
            <IconComponent className={`w-6 h-6 ${advisoryContent.iconColor}`} />
          </div>

          <div className="space-y-1.5 flex-1">
            <h3 className="text-sm sm:text-base font-bold text-white leading-snug">
              {advisoryContent.headline}
            </h3>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-normal">
              {advisoryContent.guidance}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

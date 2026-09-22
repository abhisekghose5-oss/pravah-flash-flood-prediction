import React from 'react';

/**
 * SHAPSummary Component
 * Displays global SHAP beeswarm / distribution plot overview.
 */
export default function SHAPSummary({ summaryData }) {
  if (!summaryData || !summaryData.top_features) return null;

  const { top_features = [], model_used, sample_size } = summaryData;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <h3 className="text-base font-bold text-white tracking-wide">SHAP Summary Distribution</h3>
          <p className="text-xs text-slate-400 font-mono">
            Feature Value vs Impact Direction across {sample_size} Catchment Profiles
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono">
          <span className="flex items-center gap-1.5 text-slate-400">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span> Low Feature Value
          </span>
          <span className="flex items-center gap-1.5 text-slate-400">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span> High Feature Value
          </span>
        </div>
      </div>

      <div className="space-y-3 pt-2">
        {top_features.slice(0, 8).map((feat, i) => (
          <div key={i} className="flex items-center gap-4 text-xs">
            <div className="w-44 text-right truncate font-medium text-slate-300 shrink-0" title={feat.feature_name}>
              {feat.feature_name}
            </div>
            {/* Swarm Track */}
            <div className="flex-1 h-6 bg-slate-950/80 rounded-lg relative flex items-center px-4 border border-slate-800/80">
              <div className="w-0.5 h-full bg-slate-700 absolute left-1/2 -translate-x-1/2"></div>
              {/* Sample Swarm Dots */}
              <div className="w-full flex justify-between items-center z-10 px-2">
                <span className="w-2 h-2 rounded-full bg-blue-400/90 shadow-sm" title="Low value: Negative SHAP"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-blue-500/80 shadow-sm"></span>
                <span className="w-2 h-2 rounded-full bg-slate-500/70"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-rose-400/80 shadow-sm"></span>
                <span className="w-3 h-3 rounded-full bg-rose-500 shadow-sm" title="High value: Positive SHAP"></span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-between items-center text-[10px] font-mono text-slate-500 mt-4 px-48">
        <span>&larr; Reduces Flood Risk</span>
        <span>Zero Impact</span>
        <span>Increases Flood Risk &rarr;</span>
      </div>
    </div>
  );
}

import React from 'react';

/**
 * WhyHighRisk Component
 * Displays dynamic natural-language explanation and top contributing factors
 * calculated directly from SHAP values.
 */
export default function WhyHighRisk({ explanation, loading }) {
  if (loading) {
    return (
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 animate-pulse">
        <div className="h-6 bg-slate-800 rounded w-1/3 mb-3"></div>
        <div className="h-4 bg-slate-800 rounded w-full mb-2"></div>
        <div className="h-4 bg-slate-800 rounded w-2/3"></div>
      </div>
    );
  }

  if (!explanation) return null;

  const {
    headline_title,
    headline_narrative,
    risk_level,
    prediction_probability,
    top_contributing_factors = [],
    top_reducing_factors = [],
  } = explanation;

  const isHighRisk = risk_level === 'EMERGENCY' || risk_level === 'WARNING';
  const headerColor = isHighRisk
    ? 'text-rose-400 border-rose-500/30 bg-rose-500/10'
    : risk_level === 'ADVISORY'
    ? 'text-amber-400 border-amber-500/30 bg-amber-500/10'
    : 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl backdrop-blur-md">
      {/* Header Badge */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div className="flex items-center gap-2.5">
          <span className={`px-3 py-1 text-xs font-bold font-mono uppercase tracking-wider rounded-full border ${headerColor}`}>
            {headline_title}
          </span>
          <span className="text-xs font-mono text-slate-400">
            Flood Risk: <strong className="text-white">{(prediction_probability * 100).toFixed(1)}%</strong>
          </span>
        </div>
        <div className="text-xs font-mono text-cyan-400 bg-cyan-950/40 border border-cyan-800/40 px-2.5 py-0.5 rounded">
          SHAP Calibrated
        </div>
      </div>

      {/* Synthesis Narrative */}
      <p className="text-sm text-slate-200 leading-relaxed mb-6 font-sans">
        {headline_narrative}
      </p>

      {/* Contributing Factors Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Risk Increasing (+) */}
        <div className="bg-slate-950/60 border border-rose-950/40 rounded-xl p-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-rose-400 mb-3 flex items-center gap-1.5">
            <span>▲ Factors Increasing Risk</span>
          </h4>
          {top_contributing_factors.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No significant risk-elevating factors detected.</p>
          ) : (
            <div className="space-y-2.5">
              {top_contributing_factors.slice(0, 4).map((factor, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 truncate pr-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shrink-0"></span>
                    <span className="text-slate-300 truncate" title={factor.feature_name}>
                      {factor.feature_name}
                    </span>
                  </div>
                  <span className="font-mono font-bold text-rose-400 shrink-0">
                    +{factor.relative_contribution.toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Risk Mitigating (-) */}
        <div className="bg-slate-950/60 border border-sky-950/40 rounded-xl p-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-sky-400 mb-3 flex items-center gap-1.5">
            <span>▼ Factors Mitigating Risk</span>
          </h4>
          {top_reducing_factors.length === 0 ? (
            <p className="text-xs text-slate-500 italic">No significant risk-suppressing factors detected.</p>
          ) : (
            <div className="space-y-2.5">
              {top_reducing_factors.slice(0, 4).map((factor, idx) => (
                <div key={idx} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 truncate pr-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-sky-400 shrink-0"></span>
                    <span className="text-slate-300 truncate" title={factor.feature_name}>
                      {factor.feature_name}
                    </span>
                  </div>
                  <span className="font-mono font-bold text-sky-400 shrink-0">
                    -{factor.relative_contribution.toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Causal Notice */}
      <div className="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-slate-500 flex items-center gap-1.5">
        <span>ℹ️</span>
        <span>{explanation.disclaimer}</span>
      </div>
    </div>
  );
}

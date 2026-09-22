import React from 'react';

/**
 * PredictionExplanation Component
 * Complete tabular breakdown of all input features, values, SHAP attributions,
 * and direction indicators.
 */
export default function PredictionExplanation({ contributions = [] }) {
  if (!contributions || contributions.length === 0) return null;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-bold text-white tracking-wide">Feature Attribution Inventory</h3>
          <p className="text-xs text-slate-400 font-mono">Ranked by absolute Shapley magnitude | \(\sum |\phi_i| \rightarrow 100\%\)</p>
        </div>
        <span className="text-xs font-mono text-slate-400 bg-slate-800/80 px-2.5 py-1 rounded">
          {contributions.length} Inputs Evaluated
        </span>
      </div>

      <div className="overflow-x-auto max-h-96 overflow-y-auto rounded-lg border border-slate-800">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950/80 uppercase text-[11px] font-mono text-slate-400 sticky top-0 backdrop-blur-sm border-b border-slate-800">
            <tr>
              <th className="py-2.5 px-3">Input Feature</th>
              <th className="py-2.5 px-3">Observed Value</th>
              <th className="py-2.5 px-3">SHAP (\(\phi_i\))</th>
              <th className="py-2.5 px-3">Share (%)</th>
              <th className="py-2.5 px-3">Direction</th>
              <th className="py-2.5 px-3">Domain</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-sans">
            {contributions.map((c, i) => {
              const isPos = c.shap_value > 0;
              return (
                <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-2 px-3 font-semibold text-slate-200">
                    {c.feature_name}
                  </td>
                  <td className="py-2 px-3 font-mono text-slate-300">
                    {c.feature_value}{c.unit ? ` ${c.unit}` : ''}
                  </td>
                  <td className={`py-2 px-3 font-mono font-bold ${isPos ? 'text-rose-400' : 'text-sky-400'}`}>
                    {isPos ? '+' : ''}{c.shap_value.toFixed(4)}
                  </td>
                  <td className="py-2 px-3 font-mono">
                    <div className="flex items-center gap-2">
                      <span>{c.relative_contribution.toFixed(1)}%</span>
                      <div className="w-12 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                        <div
                          className={`h-full ${isPos ? 'bg-rose-500' : 'bg-sky-400'}`}
                          style={{ width: `${Math.min(100, c.relative_contribution * 2)}%` }}
                        ></div>
                      </div>
                    </div>
                  </td>
                  <td className="py-2 px-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                      isPos ? 'bg-rose-950/60 text-rose-300 border border-rose-800/40' : 'bg-sky-950/60 text-sky-300 border border-sky-800/40'
                    }`}>
                      {isPos ? '▲ INCREASES' : '▼ DECREASES'}
                    </span>
                  </td>
                  <td className="py-2 px-3 capitalize text-slate-400 font-mono text-[11px]">
                    {c.domain_category}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

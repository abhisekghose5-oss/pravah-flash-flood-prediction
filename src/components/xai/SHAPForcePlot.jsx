import React from 'react';

/**
 * SHAPForcePlot Component
 * Renders an interactive force plot illustrating baseline E[f(x)], positive pushing
 * forces, negative pushing forces, and the predicted probability output.
 */
export default function SHAPForcePlot({ forcePlotData }) {
  if (!forcePlotData) return null;

  const {
    base_value,
    output_value,
    total_positive_force,
    total_negative_force,
    positive_features = [],
    negative_features = [],
    svg_markup,
  } = forcePlotData;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <h3 className="text-base font-bold text-white tracking-wide">SHAP Force Plot Dynamics</h3>
          <p className="text-xs text-slate-400 font-mono">
            Baseline \(E[f(x)] = {(base_value * 100).toFixed(1)}\%\) &rarr; Final Output \(\hat{{y}} = {(output_value * 100).toFixed(1)}\%\)
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className="flex items-center gap-1.5 text-rose-400">
            <span className="w-2.5 h-2.5 rounded-sm bg-rose-500"></span>
            Forces +{(total_positive_force * 100).toFixed(1)}%
          </span>
          <span className="flex items-center gap-1.5 text-sky-400">
            <span className="w-2.5 h-2.5 rounded-sm bg-sky-400"></span>
            Forces -{(Math.abs(total_negative_force) * 100).toFixed(1)}%
          </span>
        </div>
      </div>

      {/* SVG Container */}
      {svg_markup ? (
        <div
          className="w-full overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/80 p-2 shadow-inner"
          dangerouslySetInnerHTML={{ __html: svg_markup }}
        />
      ) : (
        <div className="w-full bg-slate-950 p-6 rounded-xl border border-slate-800 text-center text-slate-400 text-xs">
          Interactive force plot visualization rendering...
        </div>
      )}

      {/* Primary Force Drivers */}
      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
        <div className="p-3 bg-slate-950/60 border border-rose-950/30 rounded-lg">
          <span className="text-rose-400 font-bold block mb-1.5">Primary Positive Push Drivers:</span>
          <div className="flex flex-wrap gap-1.5">
            {positive_features.slice(0, 3).map((f, i) => (
              <span key={i} className="px-2 py-0.5 rounded bg-rose-900/30 border border-rose-800/40 text-rose-300">
                {f.feature_name}: +{f.shap_value.toFixed(3)}
              </span>
            ))}
          </div>
        </div>

        <div className="p-3 bg-slate-950/60 border border-sky-950/30 rounded-lg">
          <span className="text-sky-400 font-bold block mb-1.5">Primary Negative Push Drivers:</span>
          <div className="flex flex-wrap gap-1.5">
            {negative_features.slice(0, 3).map((f, i) => (
              <span key={i} className="px-2 py-0.5 rounded bg-sky-900/30 border border-sky-800/40 text-sky-300">
                {f.feature_name}: {f.shap_value.toFixed(3)}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

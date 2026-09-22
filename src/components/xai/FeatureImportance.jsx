import React from 'react';

/**
 * FeatureImportance Component
 * Horizontal bar chart displaying ranked global feature attributions.
 */
export default function FeatureImportance({ features = [], modelName = 'RandomForest' }) {
  const top10 = features.slice(0, 10);
  const maxScore = Math.max(...top10.map(f => f.importance_score), 0.001);

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-bold text-white tracking-wide">Global Feature Importance</h3>
          <p className="text-xs text-slate-400 font-mono">
            Model: <span className="text-cyan-400">{modelName}</span> | Mean Absolute Shapley Attribution
          </p>
        </div>
        <span className="text-xs font-mono text-cyan-400 bg-cyan-950/40 border border-cyan-800/40 px-2 py-0.5 rounded">
          Top 10 Drivers
        </span>
      </div>

      <div className="space-y-3 pt-2">
        {top10.map((f, idx) => {
          const barWidth = Math.min(100, Math.max(4, (f.importance_score / maxScore) * 100));
          return (
            <div key={idx} className="text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="text-slate-300 font-medium truncate pr-2" title={f.feature_name}>
                  <span className="font-mono text-slate-500 mr-1.5">#{f.rank}</span>
                  {f.feature_name}
                </span>
                <span className="font-mono text-cyan-400 shrink-0 font-bold">
                  {f.relative_importance_percent.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800/60">
                <div
                  className="bg-gradient-to-r from-cyan-500 to-sky-400 h-full rounded-full transition-all duration-500"
                  style={{ width: `${barWidth}%` }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

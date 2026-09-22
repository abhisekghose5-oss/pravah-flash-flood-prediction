from __future__ import annotations

from typing import List
from src.xai.models.explanation import FeatureImportanceItem, ForcePlotData


def render_force_plot_svg(force_data: ForcePlotData, width: int = 720, height: int = 140) -> str:
    """
    Generate clean, responsive inline SVG markup representing the SHAP Force Plot.
    Visualizes:
      - Baseline expected value E[f(x)]
      - Red bars: Positive forces driving risk higher
      - Blue bars: Negative forces mitigating risk
      - Final predicted output probability
    """
    base = max(0.0, min(1.0, force_data.base_value))
    out = max(0.0, min(1.0, force_data.output_value))

    # Margin and plotting dimensions
    pad_x = 40
    pad_y = 35
    plot_w = width - 2 * pad_x
    bar_h = 32
    y_bar = pad_y + 15

    # Pixel coordinate for base and output
    x_base = pad_x + base * plot_w
    x_out = pad_x + out * plot_w

    svg_parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg" style="font-family: \'JetBrains Mono\', monospace;">',
        '<!-- Background & Axis -->',
        f'<rect width="{width}" height="{height}" fill="#0b1329" rx="10" />',
        f'<line x1="{pad_x}" y1="{y_bar + bar_h + 12}" x2="{pad_x + plot_w}" y2="{y_bar + bar_h + 12}" stroke="#334155" stroke-width="1.5" stroke-dasharray="4 4" />',
        # Axis labels
        f'<text x="{pad_x}" y="{y_bar + bar_h + 28}" fill="#64748b" font-size="11">0.0 (No Risk)</text>',
        f'<text x="{pad_x + plot_w * 0.5}" y="{y_bar + bar_h + 28}" fill="#64748b" font-size="11" text-anchor="middle">0.50 (Median)</text>',
        f'<text x="{pad_x + plot_w}" y="{y_bar + bar_h + 28}" fill="#64748b" font-size="11" text-anchor="end">1.0 (Critical Flood)</text>',
    ]

    # Draw directional force block
    if x_out >= x_base:
        # Net positive force (Red / Rose gradient)
        w_force = max(4.0, x_out - x_base)
        svg_parts.append(
            f'<rect x="{x_base}" y="{y_bar}" width="{w_force}" height="{bar_h}" fill="url(#posGrad)" rx="4" />'
        )
        # Top positive label
        if force_data.positive_features:
            top_f = force_data.positive_features[0]
            val_txt = f"{top_f.feature_name} ({top_f.feature_value}{top_f.unit})"
            svg_parts.append(
                f'<text x="{x_out - 6}" y="{y_bar - 8}" fill="#fb7185" font-size="11" font-weight="700" text-anchor="end">▲ {val_txt}</text>'
            )
    else:
        # Net negative force (Cyan / Blue gradient)
        w_force = max(4.0, x_base - x_out)
        svg_parts.append(
            f'<rect x="{x_out}" y="{y_bar}" width="{w_force}" height="{bar_h}" fill="url(#negGrad)" rx="4" />'
        )
        # Top negative label
        if force_data.negative_features:
            top_f = force_data.negative_features[0]
            val_txt = f"{top_f.feature_name} ({top_f.feature_value}{top_f.unit})"
            svg_parts.append(
                f'<text x="{x_out + 6}" y="{y_bar - 8}" fill="#38bdf8" font-size="11" font-weight="700" text-anchor="start">▼ {val_txt}</text>'
            )

    # Base Value Marker
    svg_parts.append(
        f'<line x1="{x_base}" y1="{y_bar - 6}" x2="{x_base}" y2="{y_bar + bar_h + 6}" stroke="#94a3b8" stroke-width="2" />'
    )
    svg_parts.append(
        f'<text x="{x_base}" y="{y_bar - 10}" fill="#94a3b8" font-size="10" text-anchor="middle">Base {base:.2f}</text>'
    )

    # Output Value Marker
    svg_parts.append(
        f'<line x1="{x_out}" y1="{y_bar - 10}" x2="{x_out}" y2="{y_bar + bar_h + 10}" stroke="#38bdf8" stroke-width="2.5" />'
    )
    svg_parts.append(
        f'<polygon points="{x_out-6},{y_bar+bar_h+10} {x_out+6},{y_bar+bar_h+10} {x_out},{y_bar+bar_h+3}" fill="#38bdf8" />'
    )
    svg_parts.append(
        f'<text x="{x_out}" y="{y_bar + bar_h + 24}" fill="#38bdf8" font-size="12" font-weight="800" text-anchor="middle">{out*100:.1f}%</text>'
    )

    # Gradient Definitions
    svg_parts.append("""
      <defs>
        <linearGradient id="posGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#f43f5e" stop-opacity="0.8" />
          <stop offset="100%" stop-color="#fb7185" stop-opacity="1" />
        </linearGradient>
        <linearGradient id="negGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#0284c7" stop-opacity="0.9" />
          <stop offset="100%" stop-color="#38bdf8" stop-opacity="0.75" />
        </linearGradient>
      </defs>
    </svg>
    """)

    return "".join(svg_parts)


def render_feature_importance_svg(
    features: List[FeatureImportanceItem], width: int = 580, bar_height: int = 24
) -> str:
    """
    Generate responsive inline SVG markup representing the Global Feature Importance Bar Chart.
    """
    top_items = features[:10]
    if not top_items:
        return ""

    height = len(top_items) * (bar_height + 12) + 30
    pad_left = 180
    pad_right = 70
    plot_w = width - pad_left - pad_right
    max_pct = max((f.relative_importance_percent for f in top_items), default=100.0)
    if max_pct <= 0:
        max_pct = 1.0

    svg_parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" xmlns="http://www.w3.org/2000/svg" style="font-family: \'Inter\', sans-serif;">',
        f'<rect width="{width}" height="{height}" fill="#0b1329" rx="8" />',
    ]

    for i, f in enumerate(top_items):
        y = 18 + i * (bar_height + 12)
        w_bar = max(4.0, (f.relative_importance_percent / max_pct) * plot_w)

        # Label
        name_trunc = f.feature_name[:24] + "…" if len(f.feature_name) > 25 else f.feature_name
        svg_parts.append(
            f'<text x="{pad_left - 10}" y="{y + bar_height * 0.7}" fill="#94a3b8" font-size="11" font-weight="600" text-anchor="end">{name_trunc}</text>'
        )
        # Bar track
        svg_parts.append(
            f'<rect x="{pad_left}" y="{y}" width="{plot_w}" height="{bar_height}" fill="#1e293b" rx="4" opacity="0.5" />'
        )
        # Active bar
        svg_parts.append(
            f'<rect x="{pad_left}" y="{y}" width="{w_bar}" height="{bar_height}" fill="#06b6d4" rx="4" />'
        )
        # Percentage readout
        svg_parts.append(
            f'<text x="{pad_left + w_bar + 8}" y="{y + bar_height * 0.7}" fill="#38bdf8" font-size="11" font-weight="700">{f.relative_importance_percent:.1f}%</text>'
        )

    svg_parts.append("</svg>")
    return "".join(svg_parts)

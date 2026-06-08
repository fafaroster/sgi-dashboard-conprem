"""
Maturity Radar Chart visualization for the SGI Audit Dashboard.

Renders a radar (spider/polar) chart showing the Maturity Index for each
of the 10 process zones, using Plotly Scatterpolar with filled area and
dark-mode compatible styling.

Requirements: 7.3, 7.5
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.metrics import calculate_maturity_index
from src.models import PROCESS_ZONES


def render_maturity_radar(df: pd.DataFrame, metrics: dict) -> None:
    """
    Render radar chart comparing Maturity Index across process zones.

    Displays a Plotly Scatterpolar chart with:
    - One axis per process zone (10 axes total)
    - Scale 0–100 where 100 = fully mature (no findings)
    - Filled area for visual impact
    - Zone name labels on each axis
    - Dark mode compatible colors (plotly_dark template)

    Recalculates maturity from the filtered DataFrame on each call,
    ensuring filter changes are reflected immediately.

    Args:
        df: Currently filtered findings DataFrame with columns including
            'finding_type', 'finding_id', and 'process_zone'.
        metrics: Dict containing pre-computed metrics (used as fallback context;
            maturity is recalculated from filtered df for accuracy).

    Returns:
        None. Renders directly into the Streamlit app via st.plotly_chart.
    """
    # Handle empty DataFrame: show informative empty-state message
    if df.empty:
        st.info(
            "No hay hallazgos que coincidan con los filtros seleccionados "
            "para el radar de madurez."
        )
        return

    # Recalculate maturity index from the filtered DataFrame
    maturity = calculate_maturity_index(df)

    # Build values list following PROCESS_ZONES order.
    # Zones not present in the filtered data have 100.0 maturity (no findings).
    values = [maturity.get(zone, 100.0) for zone in PROCESS_ZONES]

    # Close the polygon by repeating the first value
    radar_values = values + [values[0]]
    radar_zones = PROCESS_ZONES + [PROCESS_ZONES[0]]

    # Create Scatterpolar figure
    fig = go.Figure(
        data=go.Scatterpolar(
            r=radar_values,
            theta=radar_zones,
            fill="toself",
            fillcolor="rgba(99, 110, 250, 0.25)",
            line=dict(color="rgba(99, 110, 250, 0.9)", width=2),
            marker=dict(size=6, color="rgba(99, 110, 250, 1.0)"),
            name="Índice de Madurez",
            hovertemplate=(
                "<b>%{theta}</b><br>"
                "Madurez: %{r:.1f}%<br>"
                "<extra></extra>"
            ),
        )
    )

    # Configure polar layout with dark theme + transparent backgrounds
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(10, 15, 30, 0.4)",
        title=dict(
            text="Radar de Madurez SGI — Índice por Zona de Proceso",
            font=dict(size=16, color="#e2e8f0"),
        ),
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[0, 25, 50, 75, 100],
                ticktext=["0", "25", "50", "75", "100"],
                tickfont=dict(size=9),
                gridcolor="rgba(99, 102, 241, 0.15)",
            ),
            angularaxis=dict(
                tickfont=dict(size=10),
                gridcolor="rgba(99, 102, 241, 0.15)",
                linecolor="rgba(99, 102, 241, 0.2)",
            ),
            bgcolor="rgba(0, 0, 0, 0)",
        ),
        font=dict(color="#e2e8f0"),
        showlegend=False,
        height=550,
        margin=dict(l=80, r=80, t=60, b=40),
    )

    # Render in Streamlit
    st.plotly_chart(fig, use_container_width=True, key="maturity_radar")

"""
Pareto Chart visualization for the SGI Audit Dashboard.

Renders a primary Pareto chart showing process zones ordered by descending
Risk_Load_Score, with a cumulative percentage line and 80% threshold highlight.

Also renders a secondary Pareto chart showing ISO clause references ordered
by descending finding count, with cumulative percentage and 80% threshold.

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.metrics import calculate_risk_load_score, calculate_pareto_threshold, WEIGHTS
from src.models import PROCESS_ZONES


def render_pareto_chart(
    df: pd.DataFrame,
    metrics: dict,
    filters,
) -> None:
    """
    Render the primary Pareto chart: process zones by descending Risk_Load_Score.

    Displays vertical bars in descending order with a cumulative percentage line
    on a secondary y-axis (0–100%). Zones contributing to the top 80% of risk
    are highlighted with a distinct color from the remaining zones.

    Args:
        df: Currently filtered findings DataFrame with columns including
            'finding_type', 'finding_id', and 'process_zone'.
        metrics: Dict of pre-computed metrics (may contain cached scores).
        filters: Current FilterState (used for context; filtering already applied to df).

    Returns:
        None. Renders directly into the Streamlit app via st.plotly_chart.
    """
    # Handle empty DataFrame (zero-match filter case)
    if df.empty:
        st.info("No hay hallazgos que coincidan con los filtros seleccionados para el diagrama de Pareto.")
        return

    # Calculate Risk_Load_Score per process zone
    scores = calculate_risk_load_score(df, group_by="process_zone")

    # If no scores computed, show empty state
    if scores.empty:
        st.info("No se encontraron datos de carga de riesgo para las zonas de proceso.")
        return

    # Get Pareto threshold split (80/20 boundary)
    critical_zones, remaining_zones, cumulative_pct = calculate_pareto_threshold(scores)

    # Sort scores descending for chart display
    sorted_scores = scores.sort_values(ascending=False)

    # Build color array: critical zones get accent color, remaining get muted color
    color_critical = "#FF6B6B"  # Warm red for critical zones
    color_remaining = "#4ECDC4"  # Teal for remaining zones
    bar_colors = [
        color_critical if zone in critical_zones else color_remaining
        for zone in sorted_scores.index
    ]

    # Compute cumulative percentages for the sorted order
    total = sorted_scores.sum()
    if total > 0:
        cumulative_values = (sorted_scores.cumsum() / total * 100).values
    else:
        cumulative_values = [0.0] * len(sorted_scores)

    # Create figure with secondary y-axis
    fig = go.Figure()

    # Bar trace: Risk_Load_Score per zone
    fig.add_trace(
        go.Bar(
            x=list(sorted_scores.index),
            y=sorted_scores.values,
            name="Risk Load Score",
            marker_color=bar_colors,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Risk Load Score: %{y:.1f}<br>"
                "<extra></extra>"
            ),
            yaxis="y",
        )
    )

    # Line trace: Cumulative percentage on secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=list(sorted_scores.index),
            y=cumulative_values,
            name="% Acumulado",
            mode="lines+markers",
            line=dict(color="#FFD93D", width=2.5),
            marker=dict(size=6, color="#FFD93D"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Acumulado: %{y:.1f}%<br>"
                "<extra></extra>"
            ),
            yaxis="y2",
        )
    )

    # 80% threshold horizontal line on secondary axis
    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color="#FF6B6B",
        line_width=1.5,
        annotation_text="80%",
        annotation_position="top right",
        annotation_font_color="#FF6B6B",
        yref="y2",
    )

    # Layout configuration with dark theme + transparent backgrounds
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(10, 15, 30, 0.4)",
        title=dict(
            text="Análisis de Pareto — Zonas de Proceso por Carga de Riesgo",
            font=dict(size=16, color="#e2e8f0"),
        ),
        xaxis=dict(
            title="Zona de Proceso",
            tickangle=-45,
            tickfont=dict(size=10),
            gridcolor="rgba(99, 102, 241, 0.1)",
        ),
        yaxis=dict(
            title="Risk Load Score",
            side="left",
            showgrid=True,
            gridcolor="rgba(99, 102, 241, 0.1)",
        ),
        yaxis2=dict(
            title="% Acumulado",
            side="right",
            overlaying="y",
            range=[0, 105],
            showgrid=False,
            ticksuffix="%",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        font=dict(color="#e2e8f0"),
        bargap=0.15,
        margin=dict(b=120),
        height=500,
    )

    # Render in Streamlit
    st.plotly_chart(fig, use_container_width=True, key="pareto_chart_primary")


def render_pareto_chart_clauses(
    df: pd.DataFrame,
    filters,
) -> None:
    """
    Render the secondary Pareto chart: clause references by descending finding count.

    Displays vertical bars ordered by the number of findings per ISO clause
    reference, with a cumulative percentage line on a secondary y-axis (0–100%).
    Clause references contributing to the top 80% of findings are highlighted
    with a distinct color from the remaining clauses.

    Null clause_ref values are grouped under "Sin cláusula".

    Args:
        df: Currently filtered findings DataFrame with column 'clause_ref'.
        filters: Current FilterState (used for context; filtering already applied to df).

    Returns:
        None. Renders directly into the Streamlit app via st.plotly_chart.

    Requirements: 4.5
    """
    # Handle empty DataFrame (zero-match filter case)
    if df.empty:
        st.info("No hay hallazgos que coincidan con los filtros seleccionados para el diagrama de Pareto por cláusula.")
        return

    # Group by clause_ref, replacing null values with "Sin cláusula"
    clause_series = df["clause_ref"].fillna("Sin cláusula")
    clause_counts = clause_series.value_counts().sort_values(ascending=False)

    # If no clause counts computed, show empty state
    if clause_counts.empty:
        st.info("No se encontraron datos de cláusulas para el diagrama de Pareto.")
        return

    # Use calculate_pareto_threshold to determine 80/20 boundary
    critical_clauses, remaining_clauses, cumulative_pct = calculate_pareto_threshold(clause_counts)

    # Build color array: critical clauses get accent color, remaining get muted color
    color_critical = "#FF6B6B"  # Warm red for critical clauses
    color_remaining = "#4ECDC4"  # Teal for remaining clauses
    bar_colors = [
        color_critical if clause in critical_clauses else color_remaining
        for clause in clause_counts.index
    ]

    # Compute cumulative percentages for the sorted order
    total = clause_counts.sum()
    if total > 0:
        cumulative_values = (clause_counts.cumsum() / total * 100).values
    else:
        cumulative_values = [0.0] * len(clause_counts)

    # Create figure with secondary y-axis
    fig = go.Figure()

    # Bar trace: Finding count per clause reference
    fig.add_trace(
        go.Bar(
            x=list(clause_counts.index),
            y=clause_counts.values,
            name="Cantidad de Hallazgos",
            marker_color=bar_colors,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Hallazgos: %{y}<br>"
                "<extra></extra>"
            ),
            yaxis="y",
        )
    )

    # Line trace: Cumulative percentage on secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=list(clause_counts.index),
            y=cumulative_values,
            name="% Acumulado",
            mode="lines+markers",
            line=dict(color="#FFD93D", width=2.5),
            marker=dict(size=6, color="#FFD93D"),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Acumulado: %{y:.1f}%<br>"
                "<extra></extra>"
            ),
            yaxis="y2",
        )
    )

    # 80% threshold horizontal line on secondary axis
    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color="#FF6B6B",
        line_width=1.5,
        annotation_text="80%",
        annotation_position="top right",
        annotation_font_color="#FF6B6B",
        yref="y2",
    )

    # Layout configuration with dark theme + transparent backgrounds
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(10, 15, 30, 0.4)",
        title=dict(
            text="Análisis de Pareto — Cláusulas ISO por Cantidad de Hallazgos",
            font=dict(size=16, color="#e2e8f0"),
        ),
        xaxis=dict(
            title="Cláusula ISO",
            tickangle=-45,
            tickfont=dict(size=10),
            gridcolor="rgba(99, 102, 241, 0.1)",
        ),
        yaxis=dict(
            title="Cantidad de Hallazgos",
            side="left",
            showgrid=True,
            gridcolor="rgba(99, 102, 241, 0.1)",
        ),
        yaxis2=dict(
            title="% Acumulado",
            side="right",
            overlaying="y",
            range=[0, 105],
            showgrid=False,
            ticksuffix="%",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        font=dict(color="#e2e8f0"),
        bargap=0.15,
        margin=dict(b=120),
        height=500,
    )

    # Render in Streamlit
    st.plotly_chart(fig, use_container_width=True, key="pareto_chart_clauses")

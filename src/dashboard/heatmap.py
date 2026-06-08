"""
Risk Heatmap visualization for the SGI Audit Dashboard.

Renders a heatmap showing Risk_Load_Score for each combination of
process zone (y-axis) and ISO standard (x-axis), with numeric annotations,
hover tooltips showing per-type breakdown, and dark-theme compatible styling.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.metrics import calculate_risk_load_score, WEIGHTS
from src.models import PROCESS_ZONES, STANDARDS


def render_risk_heatmap(
    df: pd.DataFrame,
    filters,
) -> None:
    """
    Render the Risk Load Score heatmap: process zones × ISO standards.

    Displays a Plotly heatmap with:
    - 10 process zones on the y-axis
    - 3 ISO standards on the x-axis
    - Sequential color scale (Plasma) for dark mode
    - Numeric annotations showing Risk_Load_Score in each cell
    - Zero-finding cells shown in neutral gray with value 0
    - Hover tooltip with Risk_Load_Score and per-type breakdown

    Args:
        df: Currently filtered findings DataFrame with columns including
            'finding_type', 'finding_id', 'process_zone', and 'standards'.
        filters: Current FilterState (used for context; filtering already applied to df).

    Returns:
        None. Renders directly into the Streamlit app via st.plotly_chart.
    """
    # Handle empty DataFrame (zero-match filter case)
    if df.empty:
        st.info("No hay hallazgos que coincidan con los filtros seleccionados para el mapa de calor.")
        return

    # Build the score matrix: zones (rows) × standards (columns)
    score_matrix = np.zeros((len(PROCESS_ZONES), len(STANDARDS)))
    hover_texts = [[None for _ in STANDARDS] for _ in PROCESS_ZONES]

    for i, zone in enumerate(PROCESS_ZONES):
        for j, standard in enumerate(STANDARDS):
            # Filter to this specific (zone, standard) subset
            subset = df[
                (df["process_zone"] == zone) & (df["standards"] == standard)
            ]

            if subset.empty:
                score_matrix[i][j] = 0.0
                hover_texts[i][j] = (
                    f"<b>{zone}</b><br>"
                    f"<b>{standard}</b><br>"
                    f"Risk Load Score: 0.0<br>"
                    f"NCM: 0 | NCm: 0 | ODM: 0 | OBS: 0"
                )
            else:
                # Deduplicate by finding_id within this zone-standard pair
                unique_findings = subset.drop_duplicates(subset=["finding_id"])

                # Calculate score
                score = unique_findings["finding_type"].map(WEIGHTS).fillna(0.0).sum()
                score = round(score, 1)
                score_matrix[i][j] = score

                # Count per finding type for hover
                ncm_count = (unique_findings["finding_type"] == "NCM").sum()
                ncm_count_int = int(ncm_count)
                ncm_minor_count = (unique_findings["finding_type"] == "NCm").sum()
                ncm_minor_count_int = int(ncm_minor_count)
                odm_count = (unique_findings["finding_type"] == "ODM").sum()
                odm_count_int = int(odm_count)
                obs_count = (unique_findings["finding_type"] == "OBS").sum()
                obs_count_int = int(obs_count)

                hover_texts[i][j] = (
                    f"<b>{zone}</b><br>"
                    f"<b>{standard}</b><br>"
                    f"Risk Load Score: {score}<br>"
                    f"NCM: {ncm_count_int} | NCm: {ncm_minor_count_int} | "
                    f"ODM: {odm_count_int} | OBS: {obs_count_int}"
                )

    # Build custom colorscale: neutral gray for 0, then Plasma for >0
    # We use a custom approach: set zero cells to NaN for colorscale separation
    max_score = score_matrix.max() if score_matrix.max() > 0 else 1.0

    # Create a masked version for display: zeros stay as 0 in annotations
    # but use a custom colorscale that maps 0 to gray
    # Build colorscale with gray at 0 and Plasma for the rest
    colorscale = _build_zero_gray_colorscale(max_score)

    # Create annotation text matrix
    annotation_text = [
        [f"{score_matrix[i][j]:.1f}" for j in range(len(STANDARDS))]
        for i in range(len(PROCESS_ZONES))
    ]

    # Create the heatmap figure
    fig = go.Figure(
        data=go.Heatmap(
            z=score_matrix,
            x=STANDARDS,
            y=PROCESS_ZONES,
            colorscale=colorscale,
            zmin=0,
            zmax=max_score,
            text=annotation_text,
            texttemplate="%{text}",
            textfont=dict(size=12, color="white"),
            hovertext=hover_texts,
            hovertemplate="%{hovertext}<extra></extra>",
            colorbar=dict(
                title=dict(text="Risk Load Score", side="right"),
                tickfont=dict(size=10),
            ),
        )
    )

    # Layout configuration with dark theme + transparent backgrounds
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(10, 15, 30, 0.4)",
        title=dict(
            text="Mapa de Calor — Risk Load Score por Zona y Norma",
            font=dict(size=16, color="#e2e8f0"),
        ),
        xaxis=dict(
            title="Norma ISO",
            tickfont=dict(size=11),
            side="bottom",
        ),
        yaxis=dict(
            title="Zona de Proceso",
            tickfont=dict(size=10),
            autorange="reversed",  # First zone at top
        ),
        font=dict(color="#e2e8f0"),
        height=550,
        margin=dict(l=160, r=80, t=60, b=60),
    )

    # Render in Streamlit
    st.plotly_chart(fig, use_container_width=True, key="risk_heatmap")


def _build_zero_gray_colorscale(max_score: float) -> list[list]:
    """
    Build a custom colorscale that maps 0 to neutral gray and uses
    Plasma for all positive values.

    Args:
        max_score: Maximum score in the matrix (used to set boundary).

    Returns:
        List of [position, color] pairs for Plotly colorscale.
    """
    if max_score <= 0:
        # All zeros — just gray
        return [[0.0, "#3D3D3D"], [1.0, "#3D3D3D"]]

    # Gray for exactly 0, then transition quickly to Plasma
    # Use a small epsilon to create the boundary
    epsilon = 0.001

    colorscale = [
        [0.0, "#3D3D3D"],           # Neutral gray for zero
        [epsilon, "#3D3D3D"],       # Keep gray boundary thin
        [epsilon + 0.001, "#0D0887"],  # Plasma start (deep purple)
        [0.25, "#5B02A3"],          # Plasma
        [0.5, "#9C179E"],           # Plasma mid
        [0.75, "#ED7953"],          # Plasma warm
        [1.0, "#F0F921"],           # Plasma end (bright yellow)
    ]

    return colorscale

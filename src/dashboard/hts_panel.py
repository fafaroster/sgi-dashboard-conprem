"""
HTS (Hallazgo Transversal Sistémico) dedicated panel for the SGI Audit Dashboard.

This module renders a visually distinct panel for systemic transversal findings
that affect multiple process zones and standards simultaneously. The panel is
conditionally rendered only when HTS data is present in the dataset.

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from src.models import PROCESS_ZONES


# =============================================================================
# Custom CSS for the HTS panel
# =============================================================================

_HTS_PANEL_CSS = """
<style>
.hts-panel {
    border: 2px solid #8B0000;
    border-radius: 8px;
    background-color: #1a0a0a;
    padding: 1.5rem;
    margin: 1rem 0;
}
.hts-panel h3 {
    color: #FF4444;
    margin-top: 0;
}
.hts-panel .hts-label {
    color: #FF6B6B;
    font-weight: 600;
    margin-bottom: 0.25rem;
}
.hts-panel .hts-content {
    color: #FAFAFA;
    margin-bottom: 1rem;
}
.hts-panel .zone-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 0.5rem;
    margin-top: 0.5rem;
}
.hts-panel .zone-item {
    padding: 0.4rem 0.8rem;
    border-radius: 4px;
    font-size: 0.9rem;
}
.hts-panel .zone-affected {
    background-color: #3d1111;
    border: 1px solid #FF4444;
    color: #FF6B6B;
}
.hts-panel .zone-unaffected {
    background-color: #1a1a2e;
    border: 1px solid #444;
    color: #888;
}
.hts-panel .placeholder {
    color: #888;
    font-style: italic;
}
</style>
"""


# =============================================================================
# Public API
# =============================================================================


def render_hts_panel(df: pd.DataFrame) -> None:
    """Render the dedicated HTS systemic finding panel.

    Conditionally renders a visually distinct panel for transversal findings
    (is_transversal == True). If no HTS findings exist in the dataset,
    nothing is rendered — no panel, no placeholder.

    The panel displays:
    - Finding description
    - All affected process zones
    - All affected standards
    - Systemic nature explanation
    - Process-zone impact diagram (affected ✓ vs unaffected ✗)

    Handles incomplete HTS metadata gracefully by showing available fields
    and "Data not available" placeholders for missing ones.

    Args:
        df: Findings DataFrame with columns including 'is_transversal',
            'description', 'process_zone', 'standards', 'finding_id'.

    Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
    """
    # Requirement 11.4: If HTS absent, don't render anything
    if "is_transversal" not in df.columns:
        return

    hts_df = df[df["is_transversal"] == True]  # noqa: E712

    if hts_df.empty:
        return

    # Inject custom CSS for the panel (Requirement 11.2)
    st.markdown(_HTS_PANEL_CSS, unsafe_allow_html=True)

    # Build the panel content
    panel_html = _build_hts_panel_html(hts_df, df)
    st.markdown(panel_html, unsafe_allow_html=True)


# =============================================================================
# Private Helpers
# =============================================================================


def _build_hts_panel_html(hts_df: pd.DataFrame, full_df: pd.DataFrame) -> str:
    """Build the HTML content for the HTS panel.

    Args:
        hts_df: Subset of findings where is_transversal == True.
        full_df: The complete DataFrame (for context).

    Returns:
        HTML string for the HTS panel.
    """
    # Extract HTS metadata — aggregate across all HTS rows
    finding_ids = _get_unique_values(hts_df, "finding_id")
    descriptions = _get_unique_values(hts_df, "description")
    affected_zones = _get_unique_values(hts_df, "process_zone")
    affected_standards = _get_unique_values(hts_df, "standards")

    # Build the panel
    parts = ['<div class="hts-panel">']
    parts.append('<h3>⚠️ Hallazgo Transversal Sistémico (HTS)</h3>')

    # Finding ID(s)
    if finding_ids:
        ids_text = ", ".join(finding_ids)
        parts.append(f'<div class="hts-label">Hallazgo(s):</div>')
        parts.append(f'<div class="hts-content">{ids_text}</div>')

    # Description (Requirement 11.1)
    if descriptions:
        desc_text = "<br>".join(_escape_html(d) for d in descriptions)
        parts.append(f'<div class="hts-label">Descripción:</div>')
        parts.append(f'<div class="hts-content">{desc_text}</div>')
    else:
        parts.append(f'<div class="hts-label">Descripción:</div>')
        parts.append('<div class="hts-content placeholder">Data not available</div>')

    # Affected Standards (Requirement 11.1)
    if affected_standards:
        standards_text = ", ".join(affected_standards)
        parts.append(f'<div class="hts-label">Normas Afectadas:</div>')
        parts.append(f'<div class="hts-content">{standards_text}</div>')
    else:
        parts.append(f'<div class="hts-label">Normas Afectadas:</div>')
        parts.append('<div class="hts-content placeholder">Data not available</div>')

    # Systemic Explanation (Requirement 11.1)
    parts.append(f'<div class="hts-label">Naturaleza Sistémica:</div>')
    if affected_zones and len(affected_zones) > 1:
        explanation = (
            f"Este hallazgo afecta transversalmente a {len(affected_zones)} "
            f"zonas de proceso, indicando una debilidad sistémica en el SGI "
            f"que requiere intervención a nivel de gestión integral."
        )
        parts.append(f'<div class="hts-content">{explanation}</div>')
    elif affected_zones:
        explanation = (
            "Este hallazgo ha sido clasificado como transversal sistémico, "
            "indicando un impacto que trasciende una única zona de proceso."
        )
        parts.append(f'<div class="hts-content">{explanation}</div>')
    else:
        parts.append('<div class="hts-content placeholder">Data not available</div>')

    # Process-Zone Impact Diagram (Requirement 11.3)
    parts.append(f'<div class="hts-label">Diagrama de Impacto por Zona de Proceso:</div>')
    parts.append(_build_zone_impact_diagram(affected_zones))

    parts.append("</div>")  # Close hts-panel div

    return "\n".join(parts)


def _build_zone_impact_diagram(affected_zones: list[str]) -> str:
    """Build HTML for the process-zone impact diagram.

    Lists all PROCESS_ZONES and indicates affected (✓) vs unaffected (✗).

    Args:
        affected_zones: List of zone names affected by HTS finding(s).

    Returns:
        HTML string for the zone impact grid.
    """
    parts = ['<div class="zone-grid">']

    for zone in PROCESS_ZONES:
        if zone in affected_zones:
            parts.append(
                f'<div class="zone-item zone-affected">✓ {_escape_html(zone)}</div>'
            )
        else:
            parts.append(
                f'<div class="zone-item zone-unaffected">✗ {_escape_html(zone)}</div>'
            )

    parts.append("</div>")
    return "\n".join(parts)


def _get_unique_values(df: pd.DataFrame, column: str) -> list[str]:
    """Extract unique non-null values from a DataFrame column.

    Args:
        df: DataFrame to extract from.
        column: Column name.

    Returns:
        List of unique string values, empty list if column doesn't exist.
    """
    if column not in df.columns:
        return []

    values = df[column].dropna().unique().tolist()
    # Convert to strings and filter empties
    return [str(v) for v in values if str(v).strip()]


def _escape_html(text: str) -> str:
    """Escape HTML special characters in text.

    Args:
        text: Raw text string.

    Returns:
        HTML-safe string.
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )

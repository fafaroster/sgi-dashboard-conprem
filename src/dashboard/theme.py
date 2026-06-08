"""
Theme configuration helper for the SGI Audit Dashboard.

Provides centralized dark theme configuration for Plotly charts and
a collapsible section wrapper for modular layout.

The Streamlit dark theme is configured via .streamlit/config.toml:
- backgroundColor: #0E1117
- secondaryBackgroundColor: #262730
- textColor: #FAFAFA
- primaryColor: #FF6B6B
- headless: true, port: 8501

Individual chart modules already apply template="plotly_dark" directly,
but this module serves as the single source of truth for theme constants
and reusable layout utilities.

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import streamlit as st


# =============================================================================
# Theme Constants
# =============================================================================

DARK_BACKGROUND = "rgba(0,0,0,0)"
SECONDARY_BACKGROUND = "#1a1a2e"
TEXT_COLOR = "#e2e8f0"
PRIMARY_COLOR = "#6366f1"
ACCENT_TEAL = "#22d3ee"
ACCENT_YELLOW = "#f59e0b"
GRID_COLOR = "rgba(99, 102, 241, 0.1)"


# =============================================================================
# Plotly Dark Template Configuration
# =============================================================================


def get_plotly_template() -> dict:
    """Return a reusable Plotly layout configuration for the dark theme.

    This dict can be unpacked into fig.update_layout(**get_plotly_template())
    or used as a reference for consistent chart styling across modules.

    The configuration ensures:
    - Dark backgrounds with luminance <= 0.05
    - High-contrast foreground text with luminance >= 0.75
    - Minimum 4.5:1 contrast ratio for normal text (WCAG AA)
    - SVG-friendly vector rendering (Plotly default)

    Returns:
        Dict with Plotly layout properties for dark theme styling.
    """
    return {
        "template": "plotly_dark",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(10, 15, 30, 0.5)",
        "font": {
            "color": TEXT_COLOR,
            "size": 12,
        },
        "title": {
            "font": {
                "color": TEXT_COLOR,
                "size": 16,
            },
        },
        "xaxis": {
            "gridcolor": GRID_COLOR,
            "zerolinecolor": GRID_COLOR,
        },
        "yaxis": {
            "gridcolor": GRID_COLOR,
            "zerolinecolor": GRID_COLOR,
        },
        "colorway": [
            "#22d3ee",
            "#a855f7",
            "#f43f5e",
            "#10b981",
            "#f59e0b",
            "#6366f1",
            "#ec4899",
        ],
    }


# =============================================================================
# Modular Collapsible Layout
# =============================================================================


@contextmanager
def collapsible_section(
    title: str, expanded: bool = True
) -> Generator[None, None, None]:
    """Context manager wrapping content in a collapsible st.expander section.

    Provides modular layout where each visualization section is independently
    collapsible. All sections are expanded by default per Requirement 13.4.

    Streamlit's st.expander handles:
    - Collapse/expand transitions (within 300ms browser-side)
    - Session-state preservation of expanded/collapsed status

    Args:
        title: Section heading displayed on the expander toggle.
        expanded: Whether the section starts expanded. Defaults to True.

    Yields:
        Control to the caller's with-block; content is rendered inside
        the expander.

    Example:
        with collapsible_section("Risk Heatmap"):
            render_risk_heatmap(df, filters)
    """
    with st.expander(title, expanded=expanded):
        yield

"""
Filter sidebar and filtering logic for the SGI Audit Dashboard.

This module provides:
- FilterState dataclass: captures user filter selections
- render_filters_sidebar(): renders Streamlit sidebar controls
- apply_filters(): pure function that filters a DataFrame based on FilterState

Design decisions:
- apply_filters is a pure function (no Streamlit dependency) for testability
- AND logic between filter categories, OR logic within a category
- Multi-standard findings match if ANY associated standard is selected
- Search requires minimum 2 characters, case-insensitive on descriptions and IDs
- Idempotent: apply_filters(apply_filters(df, f), f) == apply_filters(df, f)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.models import PROCESS_ZONES, STANDARDS


# =============================================================================
# Constants
# =============================================================================

FINDING_TYPES: list[str] = ["NCM", "NCm", "ODM", "OBS"]
"""All valid finding type codes."""


# =============================================================================
# FilterState Dataclass
# =============================================================================


@dataclass
class FilterState:
    """Immutable snapshot of active filter selections.

    Attributes:
        standards: Selected ISO standards (OR logic within).
        finding_types: Selected finding type codes (OR logic within).
        process_zones: Selected process zones (OR logic within).
        search_text: Substring search query (min 2 chars to activate).
    """

    standards: list[str] = field(default_factory=lambda: list(STANDARDS))
    finding_types: list[str] = field(default_factory=lambda: list(FINDING_TYPES))
    process_zones: list[str] = field(default_factory=lambda: list(PROCESS_ZONES))
    search_text: str = ""


# =============================================================================
# Sidebar Renderer (Streamlit-dependent)
# =============================================================================


def render_filters_sidebar() -> FilterState:
    """
    Render filter controls in the Streamlit sidebar.

    Controls:
        - st.multiselect for ISO standards (default: all 3)
        - st.multiselect for finding types (default: all 4)
        - st.multiselect for process zones (default: all 10)
        - st.text_input for substring search

    Returns:
        FilterState capturing current user selections.
    """
    import streamlit as st

    with st.sidebar:
        st.header("Filters")

        standards = st.multiselect(
            "ISO Standards",
            options=STANDARDS,
            default=STANDARDS,
            key="filter_standards",
        )

        finding_types = st.multiselect(
            "Finding Types",
            options=FINDING_TYPES,
            default=FINDING_TYPES,
            key="filter_finding_types",
        )

        process_zones = st.multiselect(
            "Process Zones",
            options=PROCESS_ZONES,
            default=PROCESS_ZONES,
            key="filter_process_zones",
        )

        search_text = st.text_input(
            "Search (descriptions & IDs)",
            value="",
            key="filter_search_text",
        )

        # Display active filter summary
        st.divider()
        st.caption("Active Filters")
        if len(standards) < len(STANDARDS):
            st.caption(f"Standards: {', '.join(standards)}")
        if len(finding_types) < len(FINDING_TYPES):
            st.caption(f"Types: {', '.join(finding_types)}")
        if len(process_zones) < len(PROCESS_ZONES):
            st.caption(f"Zones: {', '.join(process_zones)}")
        if search_text.strip():
            st.caption(f"Search: \"{search_text.strip()}\"")

    return FilterState(
        standards=standards,
        finding_types=finding_types,
        process_zones=process_zones,
        search_text=search_text.strip(),
    )


# =============================================================================
# Pure Filtering Function (no Streamlit dependency)
# =============================================================================


def apply_filters(df: pd.DataFrame, filters: FilterState) -> pd.DataFrame:
    """
    Apply FilterState to a DataFrame using AND between categories, OR within.

    A row passes if:
        1. Its 'standards' value is in filters.standards (OR within), AND
        2. Its 'finding_type' value is in filters.finding_types (OR within), AND
        3. Its 'process_zone' value is in filters.process_zones (OR within), AND
        4. If search_text has >= 2 chars: the search term appears (case-insensitive)
           in either 'description' or 'finding_id'.

    Args:
        df: Findings DataFrame with columns: finding_id, finding_type,
            description, standards, process_zone.
        filters: Current filter selections.

    Returns:
        Filtered DataFrame. Returns empty DataFrame (preserving columns)
        if no rows match.

    Invariant:
        apply_filters(apply_filters(df, f), f) == apply_filters(df, f)
    """
    if df.empty:
        return df.copy()

    mask = pd.Series(True, index=df.index)

    # Filter by standards (OR within)
    if filters.standards:
        mask = mask & df["standards"].isin(filters.standards)
    else:
        # No standards selected means nothing matches
        mask = pd.Series(False, index=df.index)

    # Filter by finding types (OR within)
    if filters.finding_types:
        mask = mask & df["finding_type"].isin(filters.finding_types)
    else:
        mask = pd.Series(False, index=df.index)

    # Filter by process zones (OR within)
    if filters.process_zones:
        mask = mask & df["process_zone"].isin(filters.process_zones)
    else:
        mask = pd.Series(False, index=df.index)

    # Text search (min 2 chars, case-insensitive)
    search = filters.search_text.strip()
    if len(search) >= 2:
        search_lower = search.lower()
        desc_match = df["description"].str.lower().str.contains(
            search_lower, na=False, regex=False
        )
        id_match = df["finding_id"].str.lower().str.contains(
            search_lower, na=False, regex=False
        )
        mask = mask & (desc_match | id_match)

    return df.loc[mask].copy()

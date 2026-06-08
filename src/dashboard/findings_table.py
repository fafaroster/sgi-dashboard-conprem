"""
Interactive findings table with search, sort, and drill-down for the SGI Audit Dashboard.

This module provides:
- render_findings_table(): Streamlit component displaying findings in a sortable,
  searchable table with expander-based drill-down for individual finding details.

Design decisions:
- Deduplicate multi-standard findings by finding_id before display, combining
  standards into a comma-separated string (multi-standard findings shown once).
- Description truncated at 120 chars with "..." for table display.
- Null clause_ref and evidence shown as "—" in detail view.
- Case-insensitive substring search integrated with FilterState.search_text
  (minimum 2 characters to trigger).
- st.dataframe used for sortable table display.
- st.expander used for drill-down detail views.

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6
"""

from __future__ import annotations

import pandas as pd

from src.dashboard.filters import FilterState


# =============================================================================
# Constants
# =============================================================================

_DESCRIPTION_TRUNCATE_LENGTH = 120
"""Maximum characters to display in the table description column."""

_EMPTY_STATE_MESSAGE = "No findings match the current filter criteria"
"""Message displayed when no findings match filters/search."""

_NULL_PLACEHOLDER = "—"
"""Placeholder text for null/empty optional fields in detail view."""


# =============================================================================
# Helper Functions
# =============================================================================


def _truncate_description(text: str | None, max_length: int = _DESCRIPTION_TRUNCATE_LENGTH) -> str:
    """Truncate description text for table display.

    Args:
        text: The description string to truncate.
        max_length: Maximum character length before truncation.

    Returns:
        Original text if length <= max_length, otherwise first max_length
        characters followed by "...".
    """
    if text is None or not isinstance(text, str):
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def _deduplicate_findings(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate multi-standard findings by finding_id.

    Multi-standard findings (expanded into multiple rows in the source DataFrame)
    are combined into a single row with standards joined as comma-separated values.

    Args:
        df: Findings DataFrame potentially containing duplicate finding_ids
            for multi-standard findings.

    Returns:
        DataFrame with one row per unique finding_id, standards column
        containing comma-separated standard names.
    """
    if df.empty:
        return df.copy()

    # Group by finding_id and aggregate standards
    # Keep first occurrence of all other columns
    agg_dict = {}
    for col in df.columns:
        if col == "standards":
            agg_dict[col] = lambda x: ", ".join(sorted(set(x.dropna())))
        elif col == "finding_id":
            continue
        else:
            agg_dict[col] = "first"

    deduped = df.groupby("finding_id", sort=False).agg(agg_dict).reset_index()
    return deduped


def _safe_value(value, placeholder: str = _NULL_PLACEHOLDER) -> str:
    """Return the value as string, or placeholder if null/empty.

    Args:
        value: The value to check.
        placeholder: Text to return if value is null or empty.

    Returns:
        String representation of value, or placeholder.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return placeholder
    text = str(value).strip()
    return text if text else placeholder


# =============================================================================
# Main Renderer (Streamlit-dependent)
# =============================================================================


def render_findings_table(df: pd.DataFrame, filters: FilterState) -> None:
    """
    Render the interactive findings table with search, sort, and drill-down.

    Features:
        - Columns: ID, Type, Standard(s), Process Zone, Clause, Description
        - Description truncated at 120 chars with "..."
        - Sort by any column (default: ID ascending) via st.dataframe
        - Case-insensitive substring search integrated with FilterState.search_text
        - Row drill-down via st.expander showing full description, evidence,
          and affected clauses
        - Empty-state message when no matches
        - Null clause_ref and evidence displayed as "—"

    Args:
        df: Filtered findings DataFrame (already filtered by apply_filters).
        filters: Current FilterState (used for search_text integration).

    Returns:
        None. Renders directly to the Streamlit UI.
    """
    import streamlit as st

    st.subheader("📋 Findings Table")

    # Handle empty state
    if df.empty:
        st.info(_EMPTY_STATE_MESSAGE)
        return

    # Deduplicate multi-standard findings for display
    display_df = _deduplicate_findings(df)

    # Sort by ID ascending (default)
    display_df = display_df.sort_values("finding_id", ascending=True).reset_index(drop=True)

    # Build display table with truncated descriptions
    table_data = pd.DataFrame({
        "ID": display_df["finding_id"],
        "Type": display_df["finding_type"],
        "Standard(s)": display_df["standards"],
        "Process Zone": display_df["process_zone"],
        "Clause": display_df["clause_ref"].apply(
            lambda x: _safe_value(x, placeholder="—")
        ),
        "Description": display_df["description"].apply(_truncate_description),
    })

    # Display sortable table using st.dataframe with column configuration
    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.TextColumn("ID", width="small"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Standard(s)": st.column_config.TextColumn("Standard(s)", width="medium"),
            "Process Zone": st.column_config.TextColumn("Process Zone", width="medium"),
            "Clause": st.column_config.TextColumn("Clause", width="small"),
            "Description": st.column_config.TextColumn("Description", width="large"),
        },
    )

    # Detail drill-down via expanders
    st.subheader("🔍 Finding Details")
    st.caption("Expand a finding below to view full details.")

    for _, row in display_df.iterrows():
        finding_id = row["finding_id"]
        finding_type = row.get("finding_type", "")
        description = _safe_value(row.get("description"))
        evidence = _safe_value(row.get("evidence"))
        clause_ref = _safe_value(row.get("clause_ref"))
        standards = row.get("standards", "")
        process_zone = row.get("process_zone", "")

        with st.expander(f"{finding_id} — {finding_type} | {process_zone}"):
            st.markdown(f"**Finding ID:** {finding_id}")
            st.markdown(f"**Type:** {finding_type}")
            st.markdown(f"**Standard(s):** {standards}")
            st.markdown(f"**Process Zone:** {process_zone}")
            st.markdown(f"**Clause Reference:** {clause_ref}")
            st.divider()
            st.markdown("**Description:**")
            st.markdown(description)
            st.divider()
            st.markdown("**Evidence:**")
            st.markdown(evidence)

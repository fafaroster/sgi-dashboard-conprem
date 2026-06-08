"""
Executive Summary panel for the SGI Audit Dashboard.

This module provides:
- compute_executive_metrics: Pure function that computes all summary metrics
  from a findings DataFrame (testable, no Streamlit dependency).
- render_executive_summary: Streamlit renderer that displays the executive
  summary panel as the first visible section.

Design decisions:
- Separation of computation (pure) from presentation (Streamlit) for testability.
- Deduplication by finding_id ensures multi-standard findings are counted once.
- Compliance health formula: (1 - actual_score / (unique_count × 5)) × 100.
- HTS alert uses st.error for prominent red-background + warning icon display.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.metrics import WEIGHTS


# =============================================================================
# Pure computation (no Streamlit dependency — fully testable)
# =============================================================================


def compute_executive_metrics(df: pd.DataFrame) -> dict:
    """Compute all executive summary metrics from a findings DataFrame.

    This helper is pure (no Streamlit calls) and can be unit-tested
    independently.

    Args:
        df: Findings DataFrame with columns: finding_id, finding_type,
            is_transversal. May be empty.

    Returns:
        Dict with keys:
            - "total_risk_score": float (1 decimal place)
            - "compliance_health": float (percentage, 1 decimal place)
            - "finding_counts": dict[str, int] mapping type → count
              (keys: "NCM", "NCm", "ODM", "OBS")
            - "has_hts": bool (True if any is_transversal == True)

    Special cases:
        - Empty DataFrame: total_risk_score=0.0, compliance_health=100.0,
          all finding_counts=0, has_hts=False.
    """
    # Initialize default finding counts for all types
    finding_counts: dict[str, int] = {"NCM": 0, "NCm": 0, "ODM": 0, "OBS": 0}

    if df.empty:
        return {
            "total_risk_score": 0.0,
            "compliance_health": 100.0,
            "finding_counts": finding_counts,
            "has_hts": False,
        }

    # Deduplicate by finding_id for unique count
    unique_df = df.drop_duplicates(subset=["finding_id"])
    unique_count = len(unique_df)

    # Compute total risk score from deduplicated findings
    total_risk_score = round(
        unique_df["finding_type"].map(WEIGHTS).fillna(0.0).sum(), 1
    )

    # Compliance health: (1 - actual_score / (unique_count × 5)) × 100
    if unique_count == 0:
        compliance_health = 100.0
    else:
        theoretical_max = unique_count * 5.0
        compliance_health = round(
            (1 - total_risk_score / theoretical_max) * 100.0, 1
        )

    # Count per finding type (from deduplicated set)
    type_counts = unique_df["finding_type"].value_counts()
    for ftype in finding_counts:
        finding_counts[ftype] = int(type_counts.get(ftype, 0))

    # HTS detection
    has_hts = False
    if "is_transversal" in df.columns:
        has_hts = bool(df["is_transversal"].any())

    return {
        "total_risk_score": total_risk_score,
        "compliance_health": compliance_health,
        "finding_counts": finding_counts,
        "has_hts": has_hts,
    }


# =============================================================================
# Streamlit rendering
# =============================================================================


def render_executive_summary(df: pd.DataFrame, metrics: dict) -> None:
    """Render the executive summary panel as the first dashboard section.

    Displays key metrics at a glance: total findings, risk score,
    compliance health, per-type counts, and an HTS alert if applicable.
    Occupies full viewport width.

    Args:
        df: Currently filtered findings DataFrame.
        metrics: Dict containing pre-computed values from
                 compute_executive_metrics():
                 - "total_risk_score": float
                 - "compliance_health": float
                 - "finding_counts": dict[str, int]
                 - "has_hts": bool
    """
    # Deduplicate for display count
    if df.empty:
        total_count = 0
    else:
        total_count = df.drop_duplicates(subset=["finding_id"]).shape[0]

    total_risk_score = metrics.get("total_risk_score", 0.0)
    compliance_health = metrics.get("compliance_health", 100.0)
    finding_counts = metrics.get("finding_counts", {"NCM": 0, "NCm": 0, "ODM": 0, "OBS": 0})
    has_hts = metrics.get("has_hts", False)

    # --- Executive Summary Section (full width) ---
    st.header("📊 Executive Summary")

    # Top-level KPIs in 3 columns
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Total Findings", value=total_count)

    with col2:
        st.metric(label="Risk Load Score", value=f"{total_risk_score:.1f}")

    with col3:
        st.metric(label="Compliance Health", value=f"{compliance_health:.1f}%")

    # Finding type breakdown in 4 columns
    type_cols = st.columns(4)
    type_labels = ["NCM", "NCm", "ODM", "OBS"]
    type_descriptions = [
        "Major Non-Conformity",
        "Minor Non-Conformity",
        "Opportunity for Improvement",
        "Observation",
    ]

    for i, (ftype, desc) in enumerate(zip(type_labels, type_descriptions)):
        with type_cols[i]:
            st.metric(
                label=f"{ftype}",
                value=finding_counts.get(ftype, 0),
                help=desc,
            )

    # HTS Alert
    if has_hts:
        st.error(
            "⚠️ **Systemic Transversal Finding (HTS) Detected** — "
            "A cross-process systemic finding affects multiple zones and requires "
            "organization-wide corrective action."
        )

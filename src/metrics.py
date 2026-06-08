"""
Metrics Engine for the SGI Audit Dashboard.

This module computes all derived metrics from the findings DataFrame:
- Risk Load Score: weighted sum of findings per group
- Criticality Rate: NCM proportion per standard
- Maturity Index: SGI implementation level per zone
- Pareto Threshold: 80/20 boundary identification

Design decisions:
- All functions operate on a Pandas DataFrame with the schema defined in models.py
- Zone-level aggregation deduplicates by finding_id (multi-standard findings counted once)
- Standard-level aggregation counts each row (multi-standard findings counted per standard)
- All percentage/score outputs rounded to 1 decimal place
"""

from __future__ import annotations

import pandas as pd


# =============================================================================
# Constants
# =============================================================================

WEIGHTS: dict[str, float] = {
    "NCM": 5.0,
    "NCm": 2.0,
    "ODM": 1.0,
    "OBS": 0.5,
}
"""Risk weights per finding type used in Risk_Load_Score calculation."""


# =============================================================================
# Public API
# =============================================================================


def calculate_risk_load_score(
    df: pd.DataFrame,
    group_by: str = "process_zone",
) -> pd.Series:
    """
    Calculate weighted Risk_Load_Score grouped by the specified column.

    Formula: sum(NCM×5 + NCm×2 + ODM×1 + OBS×0.5) per group.

    Args:
        df: Findings DataFrame with 'finding_type' and group_by columns.
            Must also contain 'finding_id' for zone-level deduplication.
        group_by: Column name to group by. One of "process_zone",
                  "standards", or "clause_ref".

    Returns:
        Series indexed by group values with float scores rounded to
        1 decimal place. Groups with zero findings return 0.0.

    Special cases:
        - Zone-level grouping: deduplicates by finding_id before scoring
          (multi-standard findings counted once per zone).
        - Standard-level grouping: counts each row independently
          (multi-standard findings counted per standard).
    """
    if df.empty:
        return pd.Series(dtype=float)

    # For zone-level grouping, deduplicate by finding_id within each group
    if group_by == "process_zone":
        working_df = df.drop_duplicates(subset=[group_by, "finding_id"])
    else:
        working_df = df

    # Map finding types to their weights
    working_df = working_df.copy()
    working_df["_weight"] = working_df["finding_type"].map(WEIGHTS).fillna(0.0)

    # Group and sum weights
    scores = working_df.groupby(group_by)["_weight"].sum()

    # Round to 1 decimal place
    scores = scores.round(1)

    return scores


def calculate_criticality_rate(df: pd.DataFrame) -> dict[str, float]:
    """
    Calculate Criticality_Rate per ISO standard.

    Formula: (NCM_count / total_count) × 100 per standard.

    Args:
        df: Findings DataFrame with 'finding_type' and 'standards' columns.

    Returns:
        Dict mapping standard name to rate as a percentage (0.0–100.0)
        with 1 decimal place. Standards with zero findings return 0.0.
    """
    if df.empty:
        return {}

    rates: dict[str, float] = {}

    # Group by standard
    grouped = df.groupby("standards")

    for standard, group in grouped:
        total = len(group)
        if total == 0:
            rates[standard] = 0.0
        else:
            ncm_count = (group["finding_type"] == "NCM").sum()
            rates[standard] = round((ncm_count / total) * 100.0, 1)

    return rates


def calculate_maturity_index(df: pd.DataFrame) -> dict[str, float]:
    """
    Calculate Maturity_Index per process zone.

    Formula: 100 - (Risk_Load_Score / (unique_finding_count × 5)) × 100
    Where unique_finding_count is deduplicated by finding_id within the zone.

    Args:
        df: Findings DataFrame with 'process_zone', 'finding_type',
            and 'finding_id' columns.

    Returns:
        Dict mapping zone name to maturity score (0.0–100.0, 1 decimal).
        Zones with zero findings return 100.0.

    Invariant: 0.0 <= result <= 100.0 for all zones.
    """
    if df.empty:
        return {}

    maturity: dict[str, float] = {}

    for zone, group in df.groupby("process_zone"):
        # Deduplicate by finding_id within the zone
        unique_findings = group.drop_duplicates(subset=["finding_id"])
        unique_count = len(unique_findings)

        if unique_count == 0:
            maturity[zone] = 100.0
            continue

        # Calculate risk load score for deduplicated findings
        score = unique_findings["finding_type"].map(WEIGHTS).fillna(0.0).sum()

        # Maximum possible score (all findings are NCM)
        max_score = unique_count * 5.0

        # Maturity index formula
        index = 100.0 - (score / max_score) * 100.0
        maturity[zone] = round(index, 1)

    return maturity


def calculate_pareto_threshold(
    scores: pd.Series,
    threshold: float = 0.8,
) -> tuple[list[str], list[str], pd.Series]:
    """
    Determine the Pareto 80/20 boundary for a scored Series.

    Args:
        scores: Series of scores indexed by category (zone or clause).
        threshold: Cumulative percentage cutoff (default 0.8 = 80%).

    Returns:
        Tuple of:
          - critical_categories: list of categories up to threshold
          - remaining_categories: list below threshold
          - cumulative_pct: Series of cumulative percentages (0.0–1.0)

    Algorithm:
        1. Sort scores descending
        2. Compute total = sum(scores)
        3. Compute cumulative_pct = cumsum(scores) / total
        4. Find index where cumulative_pct first exceeds threshold
        5. Split into critical (up to and including boundary) and remaining

    Special cases:
        - Empty input: returns ([], [], empty Series)
        - All-zero scores: returns ([], list of all categories, Series of 0.0)
    """
    if scores.empty:
        return ([], [], pd.Series(dtype=float))

    # Sort descending
    sorted_scores = scores.sort_values(ascending=False)

    total = sorted_scores.sum()

    if total == 0:
        # All scores are zero — nothing is "critical"
        cumulative_pct = pd.Series(0.0, index=sorted_scores.index)
        return ([], list(sorted_scores.index), cumulative_pct)

    # Compute cumulative percentage
    cumulative_pct = sorted_scores.cumsum() / total

    # Find the boundary: first index where cumulative >= threshold
    above_threshold = cumulative_pct >= threshold
    if above_threshold.any():
        # Get the position of the first True value
        boundary_idx = above_threshold.values.argmax()
    else:
        # Threshold never reached (shouldn't happen if total > 0 and threshold <= 1.0)
        boundary_idx = len(sorted_scores) - 1

    # Split into critical and remaining
    critical_categories = list(sorted_scores.index[: boundary_idx + 1])
    remaining_categories = list(sorted_scores.index[boundary_idx + 1 :])

    return (critical_categories, remaining_categories, cumulative_pct)

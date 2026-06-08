"""
Unit tests for the Metrics Engine (src/metrics.py).

Tests cover:
- calculate_risk_load_score: empty DF, single finding, multi-standard,
  zone-level deduplication, standard-level counting, zero-finding groups
- calculate_criticality_rate: empty DF, single standard, multiple standards,
  zero NCM, all NCM, zero-division
- calculate_maturity_index: empty DF, single zone, zero-finding zone,
  all-NCM zone (maturity=0), all-OBS zone (high maturity), deduplication
- calculate_pareto_threshold: empty series, single category, normal 80/20,
  all-zero scores, equal scores
"""

import pandas as pd
import pytest

from src.metrics import (
    WEIGHTS,
    calculate_criticality_rate,
    calculate_maturity_index,
    calculate_pareto_threshold,
    calculate_risk_load_score,
)


# =============================================================================
# Helpers
# =============================================================================


def make_findings_df(rows: list[dict]) -> pd.DataFrame:
    """Create a findings DataFrame from a list of row dicts."""
    columns = [
        "finding_id",
        "finding_type",
        "description",
        "standards",
        "process_zone",
        "clause_ref",
        "evidence",
        "is_transversal",
        "responsible_party",
        "deadline",
        "estimated_mitigation_cost",
        "corrective_action_status",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(rows)
    # Ensure all expected columns exist
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df


# =============================================================================
# Tests: WEIGHTS constant
# =============================================================================


class TestWeights:
    """Verify the WEIGHTS constant is correctly defined."""

    def test_weights_values(self):
        assert WEIGHTS == {"NCM": 5.0, "NCm": 2.0, "ODM": 1.0, "OBS": 0.5}

    def test_weights_keys_match_finding_types(self):
        expected_types = {"NCM", "NCm", "ODM", "OBS"}
        assert set(WEIGHTS.keys()) == expected_types


# =============================================================================
# Tests: calculate_risk_load_score
# =============================================================================


class TestCalculateRiskLoadScore:
    """Tests for calculate_risk_load_score function."""

    def test_empty_dataframe(self):
        """Empty DataFrame returns empty Series."""
        df = make_findings_df([])
        result = calculate_risk_load_score(df)
        assert result.empty

    def test_single_ncm_finding(self):
        """Single NCM finding in one zone scores 5.0."""
        df = make_findings_df([
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Logistics",
                "standards": "ISO 9001:2015",
            }
        ])
        result = calculate_risk_load_score(df)
        assert result["Logistics"] == 5.0

    def test_single_ncm_finding_minor(self):
        """Single NCm finding scores 2.0."""
        df = make_findings_df([
            {
                "finding_id": "NCm-01",
                "finding_type": "NCm",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            }
        ])
        result = calculate_risk_load_score(df)
        assert result["Lab"] == 2.0

    def test_single_odm_finding(self):
        """Single ODM finding scores 1.0."""
        df = make_findings_df([
            {
                "finding_id": "ODM-01",
                "finding_type": "ODM",
                "process_zone": "Lab",
                "standards": "ISO 14001:2015",
            }
        ])
        result = calculate_risk_load_score(df)
        assert result["Lab"] == 1.0

    def test_single_obs_finding(self):
        """Single OBS finding scores 0.5."""
        df = make_findings_df([
            {
                "finding_id": "OBS-01",
                "finding_type": "OBS",
                "process_zone": "Boilers",
                "standards": "ISO 45001:2018",
            }
        ])
        result = calculate_risk_load_score(df)
        assert result["Boilers"] == 0.5

    def test_multiple_findings_same_zone(self):
        """Multiple findings in one zone sum their weights."""
        df = make_findings_df([
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Logistics",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "NCm-01",
                "finding_type": "NCm",
                "process_zone": "Logistics",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "OBS-01",
                "finding_type": "OBS",
                "process_zone": "Logistics",
                "standards": "ISO 9001:2015",
            },
        ])
        result = calculate_risk_load_score(df)
        # 5.0 + 2.0 + 0.5 = 7.5
        assert result["Logistics"] == 7.5

    def test_multiple_zones(self):
        """Findings in different zones produce independent scores."""
        df = make_findings_df([
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Logistics",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "OBS-01",
                "finding_type": "OBS",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
        ])
        result = calculate_risk_load_score(df)
        assert result["Logistics"] == 5.0
        assert result["Lab"] == 0.5

    def test_zone_level_deduplication_multi_standard(self):
        """Multi-standard finding counted once at zone level."""
        # Same finding_id appearing twice (expanded for 2 standards)
        df = make_findings_df([
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Logistics",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Logistics",
                "standards": "ISO 14001:2015",
            },
        ])
        result = calculate_risk_load_score(df, group_by="process_zone")
        # Deduplicated: only counted once → 5.0
        assert result["Logistics"] == 5.0

    def test_standard_level_counts_each_row(self):
        """Multi-standard finding counted per standard at standard level."""
        df = make_findings_df([
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Logistics",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Logistics",
                "standards": "ISO 14001:2015",
            },
        ])
        result = calculate_risk_load_score(df, group_by="standards")
        # Each row counts independently → 5.0 per standard
        assert result["ISO 9001:2015"] == 5.0
        assert result["ISO 14001:2015"] == 5.0

    def test_result_rounded_to_one_decimal(self):
        """Scores are rounded to 1 decimal place."""
        # 3 OBS = 3 × 0.5 = 1.5 (already 1 decimal)
        df = make_findings_df([
            {
                "finding_id": "OBS-01",
                "finding_type": "OBS",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "OBS-02",
                "finding_type": "OBS",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "OBS-03",
                "finding_type": "OBS",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
        ])
        result = calculate_risk_load_score(df)
        assert result["Lab"] == 1.5

    def test_all_finding_types_combined(self):
        """All four types in one zone produce correct weighted sum."""
        df = make_findings_df([
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Aggregates",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "NCm-01",
                "finding_type": "NCm",
                "process_zone": "Aggregates",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "ODM-01",
                "finding_type": "ODM",
                "process_zone": "Aggregates",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "OBS-01",
                "finding_type": "OBS",
                "process_zone": "Aggregates",
                "standards": "ISO 9001:2015",
            },
        ])
        result = calculate_risk_load_score(df)
        # 5.0 + 2.0 + 1.0 + 0.5 = 8.5
        assert result["Aggregates"] == 8.5


# =============================================================================
# Tests: calculate_criticality_rate
# =============================================================================


class TestCalculateCriticalityRate:
    """Tests for calculate_criticality_rate function."""

    def test_empty_dataframe(self):
        """Empty DataFrame returns empty dict."""
        df = make_findings_df([])
        result = calculate_criticality_rate(df)
        assert result == {}

    def test_single_standard_all_ncm(self):
        """All findings are NCM → 100.0%."""
        df = make_findings_df([
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "NCM-02",
                "finding_type": "NCM",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
        ])
        result = calculate_criticality_rate(df)
        assert result["ISO 9001:2015"] == 100.0

    def test_single_standard_no_ncm(self):
        """No NCM findings → 0.0%."""
        df = make_findings_df([
            {
                "finding_id": "ODM-01",
                "finding_type": "ODM",
                "process_zone": "Lab",
                "standards": "ISO 14001:2015",
            },
            {
                "finding_id": "OBS-01",
                "finding_type": "OBS",
                "process_zone": "Lab",
                "standards": "ISO 14001:2015",
            },
        ])
        result = calculate_criticality_rate(df)
        assert result["ISO 14001:2015"] == 0.0

    def test_mixed_findings_one_third_ncm(self):
        """1 NCM out of 3 total → 33.3%."""
        df = make_findings_df([
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "NCm-01",
                "finding_type": "NCm",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "ODM-01",
                "finding_type": "ODM",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
        ])
        result = calculate_criticality_rate(df)
        assert result["ISO 9001:2015"] == 33.3

    def test_multiple_standards(self):
        """Multiple standards each get their own rate."""
        df = make_findings_df([
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "ODM-01",
                "finding_type": "ODM",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "OBS-01",
                "finding_type": "OBS",
                "process_zone": "Lab",
                "standards": "ISO 14001:2015",
            },
        ])
        result = calculate_criticality_rate(df)
        # ISO 9001: 1 NCM / 2 total = 50.0%
        assert result["ISO 9001:2015"] == 50.0
        # ISO 14001: 0 NCM / 1 total = 0.0%
        assert result["ISO 14001:2015"] == 0.0

    def test_result_one_decimal_place(self):
        """Rate is rounded to 1 decimal place."""
        # 1 NCM out of 7 = 14.285...% → 14.3%
        rows = [
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
        ]
        for i in range(6):
            rows.append({
                "finding_id": f"OBS-0{i+1}",
                "finding_type": "OBS",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            })
        df = make_findings_df(rows)
        result = calculate_criticality_rate(df)
        assert result["ISO 9001:2015"] == 14.3


# =============================================================================
# Tests: calculate_maturity_index
# =============================================================================


class TestCalculateMaturityIndex:
    """Tests for calculate_maturity_index function."""

    def test_empty_dataframe(self):
        """Empty DataFrame returns empty dict."""
        df = make_findings_df([])
        result = calculate_maturity_index(df)
        assert result == {}

    def test_all_ncm_findings_maturity_zero(self):
        """Zone with all NCM findings has maturity 0.0."""
        df = make_findings_df([
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Logistics",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "NCM-02",
                "finding_type": "NCM",
                "process_zone": "Logistics",
                "standards": "ISO 9001:2015",
            },
        ])
        result = calculate_maturity_index(df)
        # Risk = 10.0, max = 2×5 = 10.0
        # Maturity = 100 - (10/10)*100 = 0.0
        assert result["Logistics"] == 0.0

    def test_all_obs_findings_high_maturity(self):
        """Zone with all OBS findings has high maturity."""
        df = make_findings_df([
            {
                "finding_id": "OBS-01",
                "finding_type": "OBS",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "OBS-02",
                "finding_type": "OBS",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
        ])
        result = calculate_maturity_index(df)
        # Risk = 1.0, max = 2×5 = 10.0
        # Maturity = 100 - (1.0/10.0)*100 = 90.0
        assert result["Lab"] == 90.0

    def test_mixed_findings(self):
        """Zone with mixed findings produces correct maturity."""
        df = make_findings_df([
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "OBS-01",
                "finding_type": "OBS",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
        ])
        result = calculate_maturity_index(df)
        # Risk = 5.0 + 0.5 = 5.5, max = 2×5 = 10.0
        # Maturity = 100 - (5.5/10.0)*100 = 45.0
        assert result["Lab"] == 45.0

    def test_deduplication_for_multi_standard(self):
        """Multi-standard finding deduplicated for unique count."""
        df = make_findings_df([
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Logistics",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Logistics",
                "standards": "ISO 14001:2015",
            },
        ])
        result = calculate_maturity_index(df)
        # After dedup: 1 unique finding (NCM-01)
        # Risk = 5.0, max = 1×5 = 5.0
        # Maturity = 100 - (5.0/5.0)*100 = 0.0
        assert result["Logistics"] == 0.0

    def test_multiple_zones(self):
        """Each zone gets its own maturity index."""
        df = make_findings_df([
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Logistics",
                "standards": "ISO 9001:2015",
            },
            {
                "finding_id": "OBS-01",
                "finding_type": "OBS",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
        ])
        result = calculate_maturity_index(df)
        # Logistics: risk=5.0, max=5.0, maturity=0.0
        assert result["Logistics"] == 0.0
        # Lab: risk=0.5, max=5.0, maturity=90.0
        assert result["Lab"] == 90.0

    def test_maturity_bounded_0_to_100(self):
        """Maturity index is always between 0.0 and 100.0."""
        df = make_findings_df([
            {
                "finding_id": "NCM-01",
                "finding_type": "NCM",
                "process_zone": "Lab",
                "standards": "ISO 9001:2015",
            },
        ])
        result = calculate_maturity_index(df)
        assert 0.0 <= result["Lab"] <= 100.0

    def test_single_odm_finding(self):
        """Single ODM → maturity = 100 - (1.0/5.0)*100 = 80.0."""
        df = make_findings_df([
            {
                "finding_id": "ODM-01",
                "finding_type": "ODM",
                "process_zone": "Boilers",
                "standards": "ISO 9001:2015",
            },
        ])
        result = calculate_maturity_index(df)
        assert result["Boilers"] == 80.0


# =============================================================================
# Tests: calculate_pareto_threshold
# =============================================================================


class TestCalculateParetoThreshold:
    """Tests for calculate_pareto_threshold function."""

    def test_empty_series(self):
        """Empty input returns empty lists and Series."""
        scores = pd.Series(dtype=float)
        critical, remaining, cumulative = calculate_pareto_threshold(scores)
        assert critical == []
        assert remaining == []
        assert cumulative.empty

    def test_single_category(self):
        """Single category is always critical (100% of total)."""
        scores = pd.Series({"Logistics": 10.0})
        critical, remaining, cumulative = calculate_pareto_threshold(scores)
        assert critical == ["Logistics"]
        assert remaining == []
        assert cumulative["Logistics"] == 1.0

    def test_all_zero_scores(self):
        """All-zero scores: nothing is critical."""
        scores = pd.Series({"A": 0.0, "B": 0.0, "C": 0.0})
        critical, remaining, cumulative = calculate_pareto_threshold(scores)
        assert critical == []
        assert set(remaining) == {"A", "B", "C"}

    def test_classic_pareto_distribution(self):
        """80/20 distribution: 1 high scorer is critical."""
        scores = pd.Series({
            "Zone_A": 80.0,
            "Zone_B": 10.0,
            "Zone_C": 5.0,
            "Zone_D": 5.0,
        })
        critical, remaining, cumulative = calculate_pareto_threshold(scores)
        assert critical == ["Zone_A"]
        assert "Zone_B" in remaining
        assert "Zone_C" in remaining
        assert "Zone_D" in remaining

    def test_equal_scores(self):
        """Equal scores: need enough categories to reach 80%."""
        scores = pd.Series({
            "A": 10.0,
            "B": 10.0,
            "C": 10.0,
            "D": 10.0,
            "E": 10.0,
        })
        critical, remaining, cumulative = calculate_pareto_threshold(scores)
        # 5 equal items: each is 20%. Need 4 items (80%) to reach threshold.
        assert len(critical) == 4
        assert len(remaining) == 1

    def test_cumulative_ends_at_one(self):
        """Cumulative percentage line ends at 1.0 (100%)."""
        scores = pd.Series({"A": 30.0, "B": 20.0, "C": 10.0})
        _, _, cumulative = calculate_pareto_threshold(scores)
        assert cumulative.iloc[-1] == pytest.approx(1.0)

    def test_cumulative_monotonically_increasing(self):
        """Cumulative percentages are non-decreasing."""
        scores = pd.Series({"A": 50.0, "B": 30.0, "C": 15.0, "D": 5.0})
        _, _, cumulative = calculate_pareto_threshold(scores)
        for i in range(1, len(cumulative)):
            assert cumulative.iloc[i] >= cumulative.iloc[i - 1]

    def test_custom_threshold(self):
        """Custom threshold of 0.6 includes fewer categories."""
        scores = pd.Series({
            "Zone_A": 60.0,
            "Zone_B": 25.0,
            "Zone_C": 15.0,
        })
        critical, remaining, _ = calculate_pareto_threshold(
            scores, threshold=0.6
        )
        assert critical == ["Zone_A"]
        assert "Zone_B" in remaining
        assert "Zone_C" in remaining

    def test_descending_order_in_output(self):
        """Cumulative series is in descending score order."""
        scores = pd.Series({"Low": 5.0, "High": 50.0, "Mid": 20.0})
        _, _, cumulative = calculate_pareto_threshold(scores)
        # First entry should be the highest scorer
        assert cumulative.index[0] == "High"
        assert cumulative.index[1] == "Mid"
        assert cumulative.index[2] == "Low"

"""
Unit tests for the executive summary module.

Tests the pure compute_executive_metrics function which has no Streamlit
dependency and can be verified in isolation.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

import pandas as pd
import pytest

from src.dashboard.executive_summary import compute_executive_metrics


# =============================================================================
# Fixtures
# =============================================================================


def _make_df(rows: list[dict]) -> pd.DataFrame:
    """Helper to create a findings DataFrame from a list of row dicts."""
    if not rows:
        return pd.DataFrame(
            columns=[
                "finding_id",
                "finding_type",
                "standards",
                "process_zone",
                "is_transversal",
            ]
        )
    return pd.DataFrame(rows)


# =============================================================================
# Tests: Empty dataset
# =============================================================================


class TestEmptyDataset:
    """Requirement 8.5: empty dataset → all zeros, compliance health = 100.0%."""

    def test_empty_dataframe_returns_defaults(self):
        df = _make_df([])
        metrics = compute_executive_metrics(df)

        assert metrics["total_risk_score"] == 0.0
        assert metrics["compliance_health"] == 100.0
        assert metrics["finding_counts"] == {"NCM": 0, "NCm": 0, "ODM": 0, "OBS": 0}
        assert metrics["has_hts"] is False


# =============================================================================
# Tests: Risk score calculation
# =============================================================================


class TestTotalRiskScore:
    """Requirement 8.1: total Risk_Load_Score with 1 decimal place."""

    def test_single_ncm_finding(self):
        df = _make_df([
            {"finding_id": "NCM-01", "finding_type": "NCM", "standards": "ISO 9001:2015",
             "process_zone": "Logistics", "is_transversal": False},
        ])
        metrics = compute_executive_metrics(df)
        assert metrics["total_risk_score"] == 5.0

    def test_mixed_findings(self):
        df = _make_df([
            {"finding_id": "NCM-01", "finding_type": "NCM", "standards": "ISO 9001:2015",
             "process_zone": "Logistics", "is_transversal": False},
            {"finding_id": "NCm-01", "finding_type": "NCm", "standards": "ISO 9001:2015",
             "process_zone": "Lab", "is_transversal": False},
            {"finding_id": "ODM-01", "finding_type": "ODM", "standards": "ISO 14001:2015",
             "process_zone": "Boilers", "is_transversal": False},
            {"finding_id": "OBS-01", "finding_type": "OBS", "standards": "ISO 45001:2018",
             "process_zone": "Lab", "is_transversal": False},
        ])
        metrics = compute_executive_metrics(df)
        # 5.0 + 2.0 + 1.0 + 0.5 = 8.5
        assert metrics["total_risk_score"] == 8.5

    def test_deduplication_by_finding_id(self):
        """Multi-standard findings should be counted once for risk score."""
        df = _make_df([
            {"finding_id": "NCM-01", "finding_type": "NCM", "standards": "ISO 9001:2015",
             "process_zone": "Logistics", "is_transversal": False},
            {"finding_id": "NCM-01", "finding_type": "NCM", "standards": "ISO 14001:2015",
             "process_zone": "Logistics", "is_transversal": False},
        ])
        metrics = compute_executive_metrics(df)
        # Should deduplicate: only one NCM-01, score = 5.0
        assert metrics["total_risk_score"] == 5.0


# =============================================================================
# Tests: Compliance health
# =============================================================================


class TestComplianceHealth:
    """Requirement 8.3: (1 - actual / (unique_count × 5)) × 100."""

    def test_all_ncm_gives_zero_health(self):
        """All NCM = worst case → health = 0%."""
        df = _make_df([
            {"finding_id": "NCM-01", "finding_type": "NCM", "standards": "ISO 9001:2015",
             "process_zone": "Logistics", "is_transversal": False},
        ])
        metrics = compute_executive_metrics(df)
        # (1 - 5.0 / (1 × 5)) × 100 = 0.0
        assert metrics["compliance_health"] == 0.0

    def test_all_obs_gives_high_health(self):
        """All OBS = least severe → health = 90%."""
        df = _make_df([
            {"finding_id": "OBS-01", "finding_type": "OBS", "standards": "ISO 9001:2015",
             "process_zone": "Logistics", "is_transversal": False},
        ])
        metrics = compute_executive_metrics(df)
        # (1 - 0.5 / (1 × 5)) × 100 = 90.0
        assert metrics["compliance_health"] == 90.0

    def test_mixed_findings_health(self):
        """Mixed: NCM + OBS → health based on actual vs theoretical max."""
        df = _make_df([
            {"finding_id": "NCM-01", "finding_type": "NCM", "standards": "ISO 9001:2015",
             "process_zone": "Logistics", "is_transversal": False},
            {"finding_id": "OBS-01", "finding_type": "OBS", "standards": "ISO 9001:2015",
             "process_zone": "Lab", "is_transversal": False},
        ])
        metrics = compute_executive_metrics(df)
        # actual = 5.0 + 0.5 = 5.5, max = 2 × 5 = 10
        # (1 - 5.5/10) × 100 = 45.0
        assert metrics["compliance_health"] == 45.0

    def test_compliance_health_one_decimal(self):
        """Health is displayed with 1 decimal place."""
        df = _make_df([
            {"finding_id": "NCm-01", "finding_type": "NCm", "standards": "ISO 9001:2015",
             "process_zone": "Logistics", "is_transversal": False},
            {"finding_id": "ODM-01", "finding_type": "ODM", "standards": "ISO 9001:2015",
             "process_zone": "Lab", "is_transversal": False},
            {"finding_id": "OBS-01", "finding_type": "OBS", "standards": "ISO 9001:2015",
             "process_zone": "Lab", "is_transversal": False},
        ])
        metrics = compute_executive_metrics(df)
        # actual = 2.0 + 1.0 + 0.5 = 3.5, max = 3 × 5 = 15
        # (1 - 3.5/15) × 100 = 76.666... → 76.7
        assert metrics["compliance_health"] == 76.7


# =============================================================================
# Tests: Finding counts per type
# =============================================================================


class TestFindingCounts:
    """Requirement 8.1: count per finding type."""

    def test_all_types_present(self):
        df = _make_df([
            {"finding_id": "NCM-01", "finding_type": "NCM", "standards": "ISO 9001:2015",
             "process_zone": "Logistics", "is_transversal": False},
            {"finding_id": "NCM-02", "finding_type": "NCM", "standards": "ISO 9001:2015",
             "process_zone": "Lab", "is_transversal": False},
            {"finding_id": "NCm-01", "finding_type": "NCm", "standards": "ISO 9001:2015",
             "process_zone": "Boilers", "is_transversal": False},
            {"finding_id": "ODM-01", "finding_type": "ODM", "standards": "ISO 14001:2015",
             "process_zone": "Lab", "is_transversal": False},
            {"finding_id": "OBS-01", "finding_type": "OBS", "standards": "ISO 45001:2018",
             "process_zone": "Lab", "is_transversal": False},
        ])
        metrics = compute_executive_metrics(df)
        assert metrics["finding_counts"]["NCM"] == 2
        assert metrics["finding_counts"]["NCm"] == 1
        assert metrics["finding_counts"]["ODM"] == 1
        assert metrics["finding_counts"]["OBS"] == 1

    def test_missing_types_are_zero(self):
        """Types not present in data should show 0."""
        df = _make_df([
            {"finding_id": "NCM-01", "finding_type": "NCM", "standards": "ISO 9001:2015",
             "process_zone": "Logistics", "is_transversal": False},
        ])
        metrics = compute_executive_metrics(df)
        assert metrics["finding_counts"]["NCm"] == 0
        assert metrics["finding_counts"]["ODM"] == 0
        assert metrics["finding_counts"]["OBS"] == 0

    def test_deduplication_for_counts(self):
        """Multi-standard findings counted once in type counts."""
        df = _make_df([
            {"finding_id": "NCM-01", "finding_type": "NCM", "standards": "ISO 9001:2015",
             "process_zone": "Logistics", "is_transversal": False},
            {"finding_id": "NCM-01", "finding_type": "NCM", "standards": "ISO 14001:2015",
             "process_zone": "Logistics", "is_transversal": False},
            {"finding_id": "NCM-01", "finding_type": "NCM", "standards": "ISO 45001:2018",
             "process_zone": "Logistics", "is_transversal": False},
        ])
        metrics = compute_executive_metrics(df)
        # NCM-01 appears 3 times but is deduplicated to 1
        assert metrics["finding_counts"]["NCM"] == 1


# =============================================================================
# Tests: HTS detection
# =============================================================================


class TestHTSDetection:
    """Requirement 8.4: HTS alert when is_transversal == True exists."""

    def test_no_hts_findings(self):
        df = _make_df([
            {"finding_id": "NCM-01", "finding_type": "NCM", "standards": "ISO 9001:2015",
             "process_zone": "Logistics", "is_transversal": False},
        ])
        metrics = compute_executive_metrics(df)
        assert metrics["has_hts"] is False

    def test_hts_finding_present(self):
        df = _make_df([
            {"finding_id": "NCM-01", "finding_type": "NCM", "standards": "ISO 9001:2015",
             "process_zone": "Logistics", "is_transversal": False},
            {"finding_id": "NCM-15", "finding_type": "NCM", "standards": "ISO 9001:2015",
             "process_zone": "General/Transversal", "is_transversal": True},
        ])
        metrics = compute_executive_metrics(df)
        assert metrics["has_hts"] is True

    def test_hts_detection_uses_full_df_not_deduplicated(self):
        """HTS detection checks the full (non-deduplicated) DataFrame."""
        df = _make_df([
            {"finding_id": "NCM-15", "finding_type": "NCM", "standards": "ISO 9001:2015",
             "process_zone": "General/Transversal", "is_transversal": True},
            {"finding_id": "NCM-15", "finding_type": "NCM", "standards": "ISO 14001:2015",
             "process_zone": "General/Transversal", "is_transversal": True},
        ])
        metrics = compute_executive_metrics(df)
        assert metrics["has_hts"] is True

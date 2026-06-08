"""
Unit tests for the findings table module.

Tests cover:
- Description truncation logic
- Deduplication of multi-standard findings
- Safe value handling for null/empty fields
- Empty state handling
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.dashboard.findings_table import (
    _truncate_description,
    _deduplicate_findings,
    _safe_value,
    _DESCRIPTION_TRUNCATE_LENGTH,
    _NULL_PLACEHOLDER,
)


# =============================================================================
# _truncate_description tests
# =============================================================================


class TestTruncateDescription:
    """Tests for the description truncation helper."""

    def test_short_string_unchanged(self):
        """Text <= 120 chars is returned as-is."""
        text = "Short description"
        assert _truncate_description(text) == text

    def test_exactly_120_chars_unchanged(self):
        """Text of exactly 120 chars is returned as-is."""
        text = "a" * 120
        assert _truncate_description(text) == text

    def test_long_string_truncated_with_ellipsis(self):
        """Text > 120 chars is truncated to 120 chars + '...'."""
        text = "b" * 200
        result = _truncate_description(text)
        assert result == "b" * 120 + "..."
        assert len(result) == 123

    def test_none_returns_empty_string(self):
        """None input returns empty string."""
        assert _truncate_description(None) == ""

    def test_empty_string_returns_empty(self):
        """Empty string is returned as-is."""
        assert _truncate_description("") == ""

    def test_custom_max_length(self):
        """Custom max_length parameter works correctly."""
        text = "hello world"
        result = _truncate_description(text, max_length=5)
        assert result == "hello..."


# =============================================================================
# _deduplicate_findings tests
# =============================================================================


class TestDeduplicateFindings:
    """Tests for multi-standard finding deduplication."""

    def test_empty_dataframe(self):
        """Empty DataFrame returns empty DataFrame."""
        df = pd.DataFrame(columns=["finding_id", "finding_type", "standards", "description", "process_zone", "clause_ref", "evidence"])
        result = _deduplicate_findings(df)
        assert result.empty

    def test_single_standard_no_change(self):
        """Findings with unique IDs are unchanged."""
        df = pd.DataFrame({
            "finding_id": ["NCM-01", "NCM-02"],
            "finding_type": ["NCM", "NCM"],
            "standards": ["ISO 9001:2015", "ISO 14001:2015"],
            "description": ["Desc 1", "Desc 2"],
            "process_zone": ["Logistics", "Lab"],
            "clause_ref": ["4.4", "5.1"],
            "evidence": ["Evidence 1", "Evidence 2"],
        })
        result = _deduplicate_findings(df)
        assert len(result) == 2

    def test_multi_standard_finding_combined(self):
        """Multi-standard findings (same ID, different standards) are combined into one row."""
        df = pd.DataFrame({
            "finding_id": ["NCM-01", "NCM-01", "NCM-02"],
            "finding_type": ["NCM", "NCM", "NCm"],
            "standards": ["ISO 9001:2015", "ISO 14001:2015", "ISO 45001:2018"],
            "description": ["Desc 1", "Desc 1", "Desc 2"],
            "process_zone": ["Logistics", "Logistics", "Lab"],
            "clause_ref": ["4.4", "4.4", "5.1"],
            "evidence": ["Evidence 1", "Evidence 1", "Evidence 2"],
        })
        result = _deduplicate_findings(df)
        assert len(result) == 2

        # NCM-01 should have combined standards
        ncm01 = result[result["finding_id"] == "NCM-01"].iloc[0]
        assert "ISO 9001:2015" in ncm01["standards"]
        assert "ISO 14001:2015" in ncm01["standards"]

    def test_deduplication_preserves_all_columns(self):
        """All columns are preserved after deduplication."""
        df = pd.DataFrame({
            "finding_id": ["NCM-01", "NCM-01"],
            "finding_type": ["NCM", "NCM"],
            "standards": ["ISO 9001:2015", "ISO 14001:2015"],
            "description": ["Desc 1", "Desc 1"],
            "process_zone": ["Logistics", "Logistics"],
            "clause_ref": ["4.4", "4.4"],
            "evidence": ["Evidence 1", "Evidence 1"],
        })
        result = _deduplicate_findings(df)
        expected_cols = {"finding_id", "finding_type", "standards", "description", "process_zone", "clause_ref", "evidence"}
        assert set(result.columns) == expected_cols


# =============================================================================
# _safe_value tests
# =============================================================================


class TestSafeValue:
    """Tests for null/empty value handling."""

    def test_none_returns_placeholder(self):
        """None returns the dash placeholder."""
        assert _safe_value(None) == _NULL_PLACEHOLDER

    def test_nan_returns_placeholder(self):
        """NaN float returns the dash placeholder."""
        assert _safe_value(float("nan")) == _NULL_PLACEHOLDER

    def test_empty_string_returns_placeholder(self):
        """Empty string returns the dash placeholder."""
        assert _safe_value("") == _NULL_PLACEHOLDER

    def test_whitespace_only_returns_placeholder(self):
        """Whitespace-only string returns the dash placeholder."""
        assert _safe_value("   ") == _NULL_PLACEHOLDER

    def test_valid_string_returned(self):
        """Valid strings are returned as-is (stripped)."""
        assert _safe_value("4.4.1") == "4.4.1"

    def test_custom_placeholder(self):
        """Custom placeholder is used when specified."""
        assert _safe_value(None, placeholder="N/A") == "N/A"

    def test_numeric_value_converted_to_string(self):
        """Numeric values are converted to string."""
        assert _safe_value(42) == "42"

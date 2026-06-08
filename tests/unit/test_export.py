"""
Unit tests for the export module.

Tests CSV export generation, zero-findings handling, filter metadata
inclusion, and the PNG placeholder message.
"""

import pandas as pd
import pytest

from src.dashboard.filters import FilterState
from src.export import ExportError, export_csv, export_png_placeholder


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """A small findings DataFrame for testing exports."""
    return pd.DataFrame(
        {
            "finding_id": ["NCM-01", "NCm-01", "ODM-01"],
            "finding_type": ["NCM", "NCm", "ODM"],
            "description": [
                "Major non-conformity in quality",
                "Minor non-conformity in environment",
                "Improvement opportunity in safety",
            ],
            "standards": [
                "ISO 9001:2015",
                "ISO 14001:2015",
                "ISO 45001:2018",
            ],
            "process_zone": ["Logistics", "Lab", "Boilers"],
            "clause_ref": ["4.4", "6.1.2", None],
            "evidence": ["Evidence A", None, "Evidence C"],
            "is_transversal": [False, False, False],
            "responsible_party": [None, None, None],
            "deadline": [None, None, None],
            "estimated_mitigation_cost": [None, None, None],
            "corrective_action_status": [None, None, None],
        }
    )


@pytest.fixture
def default_filters() -> FilterState:
    """Default filter state (all values selected)."""
    return FilterState()


@pytest.fixture
def partial_filters() -> FilterState:
    """Filter state with specific selections."""
    return FilterState(
        standards=["ISO 9001:2015"],
        finding_types=["NCM", "NCm"],
        process_zones=["Logistics", "Lab"],
        search_text="quality",
    )


# =============================================================================
# Tests: export_csv
# =============================================================================


class TestExportCsv:
    """Tests for the export_csv function."""

    def test_returns_bytes_for_nonempty_df(
        self, sample_df: pd.DataFrame, default_filters: FilterState
    ):
        """CSV export returns bytes when DataFrame has rows."""
        result = export_csv(sample_df, default_filters)
        assert result is not None
        assert isinstance(result, bytes)

    def test_returns_none_for_empty_df(self, default_filters: FilterState):
        """CSV export returns None when DataFrame is empty."""
        empty_df = pd.DataFrame(
            columns=[
                "finding_id",
                "finding_type",
                "description",
                "standards",
                "process_zone",
            ]
        )
        result = export_csv(empty_df, default_filters)
        assert result is None

    def test_csv_contains_header_comments(
        self, sample_df: pd.DataFrame, default_filters: FilterState
    ):
        """CSV output includes comment lines starting with #."""
        result = export_csv(sample_df, default_filters)
        assert result is not None
        text = result.decode("utf-8")
        lines = text.split("\n")
        comment_lines = [line for line in lines if line.startswith("#")]
        assert len(comment_lines) >= 5  # At least date, filters, record count

    def test_csv_contains_export_date(
        self, sample_df: pd.DataFrame, default_filters: FilterState
    ):
        """CSV header includes export date."""
        result = export_csv(sample_df, default_filters)
        assert result is not None
        text = result.decode("utf-8")
        assert "# Export Date:" in text

    def test_csv_contains_filter_summary(
        self, sample_df: pd.DataFrame, partial_filters: FilterState
    ):
        """CSV header reflects the active filter configuration."""
        result = export_csv(sample_df, partial_filters)
        assert result is not None
        text = result.decode("utf-8")
        assert "ISO 9001:2015" in text
        assert "NCM, NCm" in text
        assert "Logistics, Lab" in text
        assert '"quality"' in text

    def test_csv_contains_all_data_rows(
        self, sample_df: pd.DataFrame, default_filters: FilterState
    ):
        """CSV includes all rows from the DataFrame."""
        result = export_csv(sample_df, default_filters)
        assert result is not None
        text = result.decode("utf-8")
        assert "NCM-01" in text
        assert "NCm-01" in text
        assert "ODM-01" in text

    def test_csv_contains_all_columns(
        self, sample_df: pd.DataFrame, default_filters: FilterState
    ):
        """CSV includes all metadata columns."""
        result = export_csv(sample_df, default_filters)
        assert result is not None
        text = result.decode("utf-8")
        # Check column headers are present (after the comment lines)
        non_comment_lines = [
            line for line in text.split("\n") if not line.startswith("#") and line.strip()
        ]
        header_line = non_comment_lines[0]
        assert "finding_id" in header_line
        assert "finding_type" in header_line
        assert "description" in header_line
        assert "standards" in header_line
        assert "process_zone" in header_line

    def test_csv_includes_record_count(
        self, sample_df: pd.DataFrame, default_filters: FilterState
    ):
        """CSV header shows the total number of exported records."""
        result = export_csv(sample_df, default_filters)
        assert result is not None
        text = result.decode("utf-8")
        assert "# Total Records: 3" in text

    def test_custom_filename_prefix(
        self, sample_df: pd.DataFrame, default_filters: FilterState
    ):
        """CSV header includes the custom filename prefix."""
        result = export_csv(sample_df, default_filters, filename_prefix="custom_export")
        assert result is not None
        text = result.decode("utf-8")
        assert "custom_export" in text

    def test_search_text_none_in_header(
        self, sample_df: pd.DataFrame, default_filters: FilterState
    ):
        """When no search text, header shows (none)."""
        result = export_csv(sample_df, default_filters)
        assert result is not None
        text = result.decode("utf-8")
        assert "#   Search Text: (none)" in text


# =============================================================================
# Tests: export_png_placeholder
# =============================================================================


class TestExportPngPlaceholder:
    """Tests for the export_png_placeholder function."""

    def test_returns_string(self):
        """Placeholder returns a non-empty string message."""
        result = export_png_placeholder()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_mentions_kaleido(self):
        """Message mentions kaleido as the required package."""
        result = export_png_placeholder()
        assert "kaleido" in result

    def test_mentions_alternative(self):
        """Message mentions the Plotly toolbar as an alternative."""
        result = export_png_placeholder()
        assert "toolbar" in result.lower() or "camera" in result.lower()


# =============================================================================
# Tests: ExportError
# =============================================================================


class TestExportError:
    """Tests for the ExportError exception class."""

    def test_error_message_stored(self):
        """ExportError stores the message attribute."""
        err = ExportError("test failure")
        assert err.message == "test failure"
        assert str(err) == "test failure"

    def test_is_exception(self):
        """ExportError is a proper Exception subclass."""
        err = ExportError("test")
        assert isinstance(err, Exception)

    def test_can_be_raised_and_caught(self):
        """ExportError can be raised and caught."""
        with pytest.raises(ExportError, match="generation failed"):
            raise ExportError("generation failed")

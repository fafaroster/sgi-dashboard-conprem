"""
Unit tests for the filter module (apply_filters pure function).

Tests cover:
- Basic filtering by each category
- AND between categories, OR within categories
- Case-insensitive text search with min 2 chars
- Empty selection returns empty DataFrame
- Idempotence property
- Zero-match case
"""

import pandas as pd
import pytest

from src.dashboard.filters import FilterState, apply_filters, FINDING_TYPES
from src.models import PROCESS_ZONES, STANDARDS


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Create a sample findings DataFrame for testing."""
    data = [
        {
            "finding_id": "NCM-01",
            "finding_type": "NCM",
            "description": "Missing calibration records for lab equipment",
            "standards": "ISO 9001:2015",
            "process_zone": "Lab",
        },
        {
            "finding_id": "NCm-01",
            "finding_type": "NCm",
            "description": "Incomplete storage yard inspection logs",
            "standards": "ISO 14001:2015",
            "process_zone": "Storage Yard",
        },
        {
            "finding_id": "ODM-01",
            "finding_type": "ODM",
            "description": "Opportunity to improve boiler maintenance schedule",
            "standards": "ISO 45001:2018",
            "process_zone": "Boilers",
        },
        {
            "finding_id": "OBS-01",
            "finding_type": "OBS",
            "description": "Observation on logistics documentation flow",
            "standards": "ISO 9001:2015",
            "process_zone": "Logistics",
        },
        {
            "finding_id": "NCM-02",
            "finding_type": "NCM",
            "description": "Chemical storage area lacks proper labeling",
            "standards": "ISO 14001:2015",
            "process_zone": "Chemical Storage",
        },
    ]
    return pd.DataFrame(data)


# =============================================================================
# Tests: Basic filtering by category
# =============================================================================


class TestApplyFiltersStandards:
    """Test filtering by ISO standards."""

    def test_filter_single_standard(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=["ISO 9001:2015"],
            finding_types=FINDING_TYPES,
            process_zones=list(PROCESS_ZONES),
        )
        result = apply_filters(sample_df, filters)
        assert len(result) == 2
        assert all(result["standards"] == "ISO 9001:2015")

    def test_filter_multiple_standards(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=["ISO 9001:2015", "ISO 14001:2015"],
            finding_types=FINDING_TYPES,
            process_zones=list(PROCESS_ZONES),
        )
        result = apply_filters(sample_df, filters)
        assert len(result) == 4

    def test_filter_no_standards_returns_empty(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=[],
            finding_types=FINDING_TYPES,
            process_zones=list(PROCESS_ZONES),
        )
        result = apply_filters(sample_df, filters)
        assert len(result) == 0


class TestApplyFiltersFindingTypes:
    """Test filtering by finding types."""

    def test_filter_single_type(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=list(STANDARDS),
            finding_types=["NCM"],
            process_zones=list(PROCESS_ZONES),
        )
        result = apply_filters(sample_df, filters)
        assert len(result) == 2
        assert all(result["finding_type"] == "NCM")

    def test_filter_multiple_types(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=list(STANDARDS),
            finding_types=["NCM", "NCm"],
            process_zones=list(PROCESS_ZONES),
        )
        result = apply_filters(sample_df, filters)
        assert len(result) == 3

    def test_filter_no_types_returns_empty(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=list(STANDARDS),
            finding_types=[],
            process_zones=list(PROCESS_ZONES),
        )
        result = apply_filters(sample_df, filters)
        assert len(result) == 0


class TestApplyFiltersProcessZones:
    """Test filtering by process zones."""

    def test_filter_single_zone(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=list(STANDARDS),
            finding_types=FINDING_TYPES,
            process_zones=["Lab"],
        )
        result = apply_filters(sample_df, filters)
        assert len(result) == 1
        assert result.iloc[0]["process_zone"] == "Lab"

    def test_filter_no_zones_returns_empty(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=list(STANDARDS),
            finding_types=FINDING_TYPES,
            process_zones=[],
        )
        result = apply_filters(sample_df, filters)
        assert len(result) == 0


# =============================================================================
# Tests: AND between categories
# =============================================================================


class TestApplyFiltersANDLogic:
    """Test AND logic between filter categories."""

    def test_combined_standard_and_type(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=["ISO 9001:2015"],
            finding_types=["NCM"],
            process_zones=list(PROCESS_ZONES),
        )
        result = apply_filters(sample_df, filters)
        assert len(result) == 1
        assert result.iloc[0]["finding_id"] == "NCM-01"

    def test_combined_all_categories_no_match(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=["ISO 45001:2018"],
            finding_types=["NCM"],
            process_zones=list(PROCESS_ZONES),
        )
        result = apply_filters(sample_df, filters)
        assert len(result) == 0


# =============================================================================
# Tests: Text search
# =============================================================================


class TestApplyFiltersSearch:
    """Test text search functionality."""

    def test_search_in_description(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=list(STANDARDS),
            finding_types=FINDING_TYPES,
            process_zones=list(PROCESS_ZONES),
            search_text="calibration",
        )
        result = apply_filters(sample_df, filters)
        assert len(result) == 1
        assert result.iloc[0]["finding_id"] == "NCM-01"

    def test_search_case_insensitive(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=list(STANDARDS),
            finding_types=FINDING_TYPES,
            process_zones=list(PROCESS_ZONES),
            search_text="CALIBRATION",
        )
        result = apply_filters(sample_df, filters)
        assert len(result) == 1

    def test_search_in_finding_id(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=list(STANDARDS),
            finding_types=FINDING_TYPES,
            process_zones=list(PROCESS_ZONES),
            search_text="NCM-02",
        )
        result = apply_filters(sample_df, filters)
        assert len(result) == 1
        assert result.iloc[0]["finding_id"] == "NCM-02"

    def test_search_less_than_2_chars_ignored(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=list(STANDARDS),
            finding_types=FINDING_TYPES,
            process_zones=list(PROCESS_ZONES),
            search_text="N",
        )
        result = apply_filters(sample_df, filters)
        # Single char search should be ignored, return all
        assert len(result) == 5

    def test_search_empty_string_ignored(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=list(STANDARDS),
            finding_types=FINDING_TYPES,
            process_zones=list(PROCESS_ZONES),
            search_text="",
        )
        result = apply_filters(sample_df, filters)
        assert len(result) == 5

    def test_search_no_match_returns_empty(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=list(STANDARDS),
            finding_types=FINDING_TYPES,
            process_zones=list(PROCESS_ZONES),
            search_text="zzzznonexistent",
        )
        result = apply_filters(sample_df, filters)
        assert len(result) == 0


# =============================================================================
# Tests: Idempotence
# =============================================================================


class TestApplyFiltersIdempotence:
    """Test that applying filters twice gives the same result as once."""

    def test_idempotence_with_all_defaults(self, sample_df: pd.DataFrame):
        filters = FilterState()
        once = apply_filters(sample_df, filters)
        twice = apply_filters(once, filters)
        pd.testing.assert_frame_equal(once, twice)

    def test_idempotence_with_restrictive_filters(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=["ISO 9001:2015"],
            finding_types=["NCM", "OBS"],
            process_zones=["Lab", "Logistics"],
            search_text="",
        )
        once = apply_filters(sample_df, filters)
        twice = apply_filters(once, filters)
        pd.testing.assert_frame_equal(once, twice)

    def test_idempotence_with_search(self, sample_df: pd.DataFrame):
        filters = FilterState(
            standards=list(STANDARDS),
            finding_types=FINDING_TYPES,
            process_zones=list(PROCESS_ZONES),
            search_text="storage",
        )
        once = apply_filters(sample_df, filters)
        twice = apply_filters(once, filters)
        pd.testing.assert_frame_equal(once, twice)


# =============================================================================
# Tests: Edge cases
# =============================================================================


class TestApplyFiltersEdgeCases:
    """Test edge cases."""

    def test_empty_dataframe(self):
        df = pd.DataFrame(
            columns=["finding_id", "finding_type", "description", "standards", "process_zone"]
        )
        filters = FilterState()
        result = apply_filters(df, filters)
        assert len(result) == 0
        assert list(result.columns) == list(df.columns)

    def test_all_defaults_returns_all(self, sample_df: pd.DataFrame):
        filters = FilterState()
        result = apply_filters(sample_df, filters)
        assert len(result) == 5

"""
Unit tests for the Pretty_Printer module.

Tests cover:
- Valid DataFrame produces valid Markdown table
- Missing required columns raises SerializationError
- Null mandatory fields raises SerializationError with row/column info
- Optional null fields produce empty cells
- Output is parseable (starts with header, has separator row)
- validate_roundtrip verifies round-trip consistency
- serialize_to_json produces correct JSON output
"""

import json
from datetime import date

import pytest
import pandas as pd

from src.pretty_printer import (
    format_to_markdown,
    serialize_to_json,
    validate_roundtrip,
    SerializationError,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def valid_df() -> pd.DataFrame:
    """A minimal valid DataFrame with all required and optional columns."""
    return pd.DataFrame(
        {
            "finding_id": ["NCM-01", "NCm-02", "ODM-03"],
            "finding_type": ["NCM", "NCm", "ODM"],
            "description": [
                "Major non-conformity in documentation",
                "Minor issue with labeling",
                "Opportunity for improvement in process",
            ],
            "standards": [
                "ISO 9001:2015",
                "ISO 14001:2015",
                "ISO 45001:2018",
            ],
            "process_zone": ["Logistics", "Lab", "Boilers"],
            "clause_ref": ["4.4", "6.1.2", "9.1"],
            "evidence": [
                "Document review showed gaps",
                "Labeling inconsistency found",
                "Process audit observation",
            ],
        }
    )


@pytest.fixture
def df_with_optional_nulls() -> pd.DataFrame:
    """DataFrame with null values in optional fields (clause_ref, evidence)."""
    return pd.DataFrame(
        {
            "finding_id": ["NCM-01", "OBS-01"],
            "finding_type": ["NCM", "OBS"],
            "description": ["A finding description", "An observation"],
            "standards": ["ISO 9001:2015", "ISO 45001:2018"],
            "process_zone": ["Logistics", "Lab"],
            "clause_ref": [None, "7.1"],
            "evidence": ["Some evidence", None],
        }
    )


# =============================================================================
# Tests: Valid DataFrame produces valid Markdown
# =============================================================================


class TestFormatToMarkdownValid:
    """Tests for successful Markdown table generation."""

    def test_valid_df_produces_markdown_string(self, valid_df: pd.DataFrame):
        """A valid DataFrame produces a non-empty Markdown string."""
        result = format_to_markdown(valid_df)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_output_has_correct_row_count(self, valid_df: pd.DataFrame):
        """Output has header + separator + one row per DataFrame row."""
        result = format_to_markdown(valid_df)
        lines = result.strip().split("\n")
        # header + separator + 3 data rows = 5 lines
        assert len(lines) == 5

    def test_output_contains_finding_data(self, valid_df: pd.DataFrame):
        """Output contains the actual finding IDs and data."""
        result = format_to_markdown(valid_df)
        assert "NCM-01" in result
        assert "NCm-02" in result
        assert "ODM-03" in result
        assert "Logistics" in result
        assert "Lab" in result
        assert "Boilers" in result

    def test_output_preserves_column_order(self, valid_df: pd.DataFrame):
        """Output header has columns in the specified order."""
        result = format_to_markdown(valid_df)
        header_line = result.split("\n")[0]
        # Check expected column order
        assert "ID" in header_line
        assert "Type" in header_line
        assert "Standard(s)" in header_line
        assert "Process Zone" in header_line
        assert "Clause" in header_line
        assert "Description" in header_line
        assert "Evidence" in header_line
        # Verify order by checking positions
        id_pos = header_line.index("ID")
        type_pos = header_line.index("Type")
        std_pos = header_line.index("Standard(s)")
        zone_pos = header_line.index("Process Zone")
        clause_pos = header_line.index("Clause")
        desc_pos = header_line.index("Description")
        evidence_pos = header_line.index("Evidence")
        assert id_pos < type_pos < std_pos < zone_pos < clause_pos < desc_pos < evidence_pos


# =============================================================================
# Tests: Missing required columns raises SerializationError
# =============================================================================


class TestFormatToMarkdownMissingColumns:
    """Tests for missing required column validation."""

    def test_missing_finding_id_column_raises(self):
        """Missing 'finding_id' column raises SerializationError."""
        df = pd.DataFrame(
            {
                "finding_type": ["NCM"],
                "process_zone": ["Logistics"],
            }
        )
        with pytest.raises(SerializationError) as exc_info:
            format_to_markdown(df)
        assert "finding_id" in str(exc_info.value)
        assert "finding_id" in exc_info.value.columns

    def test_missing_finding_type_column_raises(self):
        """Missing 'finding_type' column raises SerializationError."""
        df = pd.DataFrame(
            {
                "finding_id": ["NCM-01"],
                "process_zone": ["Logistics"],
            }
        )
        with pytest.raises(SerializationError) as exc_info:
            format_to_markdown(df)
        assert "finding_type" in str(exc_info.value)
        assert "finding_type" in exc_info.value.columns

    def test_missing_process_zone_column_raises(self):
        """Missing 'process_zone' column raises SerializationError."""
        df = pd.DataFrame(
            {
                "finding_id": ["NCM-01"],
                "finding_type": ["NCM"],
            }
        )
        with pytest.raises(SerializationError) as exc_info:
            format_to_markdown(df)
        assert "process_zone" in str(exc_info.value)
        assert "process_zone" in exc_info.value.columns

    def test_missing_multiple_columns_reports_all(self):
        """Missing multiple required columns are all reported."""
        df = pd.DataFrame({"description": ["Some text"]})
        with pytest.raises(SerializationError) as exc_info:
            format_to_markdown(df)
        error = exc_info.value
        assert "finding_id" in error.columns
        assert "finding_type" in error.columns
        assert "process_zone" in error.columns


# =============================================================================
# Tests: Null mandatory fields raises SerializationError with row/column info
# =============================================================================


class TestFormatToMarkdownNullMandatory:
    """Tests for null value validation in mandatory fields."""

    def test_null_finding_id_raises_with_row_info(self):
        """Null in finding_id raises SerializationError with affected row index."""
        df = pd.DataFrame(
            {
                "finding_id": ["NCM-01", None, "ODM-01"],
                "finding_type": ["NCM", "NCm", "ODM"],
                "process_zone": ["Logistics", "Lab", "Boilers"],
            }
        )
        with pytest.raises(SerializationError) as exc_info:
            format_to_markdown(df)
        error = exc_info.value
        assert 1 in error.rows
        assert "finding_id" in error.columns

    def test_null_finding_type_raises_with_row_info(self):
        """Null in finding_type raises SerializationError with affected row index."""
        df = pd.DataFrame(
            {
                "finding_id": ["NCM-01", "NCm-01"],
                "finding_type": ["NCM", None],
                "process_zone": ["Logistics", "Lab"],
            }
        )
        with pytest.raises(SerializationError) as exc_info:
            format_to_markdown(df)
        error = exc_info.value
        assert 1 in error.rows
        assert "finding_type" in error.columns

    def test_null_process_zone_raises_with_row_info(self):
        """Null in process_zone raises SerializationError with affected row index."""
        df = pd.DataFrame(
            {
                "finding_id": ["NCM-01"],
                "finding_type": ["NCM"],
                "process_zone": [None],
            }
        )
        with pytest.raises(SerializationError) as exc_info:
            format_to_markdown(df)
        error = exc_info.value
        assert 0 in error.rows
        assert "process_zone" in error.columns

    def test_multiple_null_fields_reports_all(self):
        """Multiple null mandatory fields report all affected rows and columns."""
        df = pd.DataFrame(
            {
                "finding_id": [None, "NCM-01"],
                "finding_type": ["NCM", None],
                "process_zone": ["Logistics", "Lab"],
            }
        )
        with pytest.raises(SerializationError) as exc_info:
            format_to_markdown(df)
        error = exc_info.value
        assert 0 in error.rows
        assert 1 in error.rows
        assert "finding_id" in error.columns
        assert "finding_type" in error.columns

    def test_no_partial_output_on_validation_failure(self):
        """No partial Markdown output is produced when validation fails."""
        df = pd.DataFrame(
            {
                "finding_id": ["NCM-01", None],
                "finding_type": ["NCM", "NCm"],
                "process_zone": ["Logistics", "Lab"],
            }
        )
        with pytest.raises(SerializationError):
            format_to_markdown(df)
        # If SerializationError is raised, no output is returned


# =============================================================================
# Tests: Optional null fields produce empty cells
# =============================================================================


class TestFormatToMarkdownOptionalNulls:
    """Tests for handling null values in optional fields."""

    def test_null_clause_ref_produces_empty_cell(
        self, df_with_optional_nulls: pd.DataFrame
    ):
        """Null clause_ref results in an empty cell in the Markdown table."""
        result = format_to_markdown(df_with_optional_nulls)
        lines = result.strip().split("\n")
        # First data row (index 2) has None clause_ref
        first_data_row = lines[2]
        cells = [c.strip() for c in first_data_row.split("|")[1:-1]]
        # Clause is at index 4 (0: ID, 1: Type, 2: Standard(s), 3: Process Zone, 4: Clause)
        assert cells[4] == ""

    def test_null_evidence_produces_empty_cell(
        self, df_with_optional_nulls: pd.DataFrame
    ):
        """Null evidence results in an empty cell in the Markdown table."""
        result = format_to_markdown(df_with_optional_nulls)
        lines = result.strip().split("\n")
        # Second data row (index 3) has None evidence
        second_data_row = lines[3]
        cells = [c.strip() for c in second_data_row.split("|")[1:-1]]
        # Evidence is at index 6
        assert cells[6] == ""

    def test_null_description_produces_empty_cell(self):
        """Null description (optional in output) results in an empty cell."""
        df = pd.DataFrame(
            {
                "finding_id": ["NCM-01"],
                "finding_type": ["NCM"],
                "process_zone": ["Logistics"],
                "standards": ["ISO 9001:2015"],
                "clause_ref": ["4.4"],
                "description": [None],
                "evidence": ["Some evidence"],
            }
        )
        result = format_to_markdown(df)
        lines = result.strip().split("\n")
        data_row = lines[2]
        cells = [c.strip() for c in data_row.split("|")[1:-1]]
        # Description is at index 5
        assert cells[5] == ""

    def test_all_optional_null_still_produces_valid_table(self):
        """DataFrame with all optional fields null still produces valid Markdown."""
        df = pd.DataFrame(
            {
                "finding_id": ["NCM-01"],
                "finding_type": ["NCM"],
                "process_zone": ["Logistics"],
            }
        )
        result = format_to_markdown(df)
        lines = result.strip().split("\n")
        assert len(lines) == 3  # header + separator + 1 data row


# =============================================================================
# Tests: Output is parseable (structure validation)
# =============================================================================


class TestFormatToMarkdownStructure:
    """Tests for Markdown table structural correctness."""

    def test_starts_with_header_row(self, valid_df: pd.DataFrame):
        """Output starts with a pipe-delimited header row."""
        result = format_to_markdown(valid_df)
        first_line = result.split("\n")[0]
        assert first_line.startswith("|")
        assert first_line.endswith("|")
        assert "ID" in first_line

    def test_has_separator_row(self, valid_df: pd.DataFrame):
        """Output has a separator row (---) as the second line."""
        result = format_to_markdown(valid_df)
        second_line = result.split("\n")[1]
        assert second_line.startswith("|")
        assert second_line.endswith("|")
        assert "---" in second_line

    def test_separator_has_correct_column_count(self, valid_df: pd.DataFrame):
        """Separator row has the same number of columns as the header."""
        result = format_to_markdown(valid_df)
        lines = result.split("\n")
        header_cols = len(
            [c for c in lines[0].split("|") if c.strip() != ""]
        )
        separator_cols = len(
            [c for c in lines[1].split("|") if c.strip() != ""]
        )
        assert header_cols == separator_cols == 7

    def test_all_data_rows_have_correct_column_count(
        self, valid_df: pd.DataFrame
    ):
        """All data rows have the same column count as the header."""
        result = format_to_markdown(valid_df)
        lines = result.split("\n")
        expected_cols = 7
        for line in lines[2:]:  # Skip header and separator
            cols = len([c for c in line.split("|") if c.strip() != ""])
            assert cols == expected_cols

    def test_empty_dataframe_produces_header_and_separator_only(self):
        """An empty DataFrame (0 rows) produces only header + separator."""
        df = pd.DataFrame(
            {
                "finding_id": pd.Series([], dtype=str),
                "finding_type": pd.Series([], dtype=str),
                "process_zone": pd.Series([], dtype=str),
            }
        )
        result = format_to_markdown(df)
        lines = result.strip().split("\n")
        assert len(lines) == 2  # header + separator only

    def test_pipe_in_cell_content_is_escaped(self):
        """Pipe characters within cell content are escaped."""
        df = pd.DataFrame(
            {
                "finding_id": ["NCM-01"],
                "finding_type": ["NCM"],
                "process_zone": ["Logistics"],
                "description": ["Issue with A | B scenario"],
                "standards": ["ISO 9001:2015"],
                "clause_ref": ["4.4"],
                "evidence": ["Evidence text"],
            }
        )
        result = format_to_markdown(df)
        # The pipe in description should be escaped
        assert "A \\| B" in result


# =============================================================================
# Tests: serialize_to_json
# =============================================================================


class TestSerializeToJson:
    """Tests for JSON serialization of findings DataFrame."""

    def test_produces_valid_json_string(self, valid_df: pd.DataFrame):
        """serialize_to_json produces a valid JSON string."""
        result = serialize_to_json(valid_df)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 3

    def test_uses_snake_case_field_names(self, valid_df: pd.DataFrame):
        """JSON output uses snake_case field names matching DataFrame columns."""
        result = serialize_to_json(valid_df)
        parsed = json.loads(result)
        first_record = parsed[0]
        assert "finding_id" in first_record
        assert "finding_type" in first_record
        assert "process_zone" in first_record
        assert "standards" in first_record
        assert "clause_ref" in first_record

    def test_null_optional_fields_are_json_null(self):
        """Empty optional fields are serialized as JSON null."""
        df = pd.DataFrame(
            {
                "finding_id": ["NCM-01"],
                "finding_type": ["NCM"],
                "description": ["A finding"],
                "standards": ["ISO 9001:2015"],
                "process_zone": ["Logistics"],
                "clause_ref": [None],
                "evidence": [None],
                "is_transversal": [False],
                "responsible_party": [None],
                "deadline": [None],
                "estimated_mitigation_cost": [None],
                "corrective_action_status": [None],
            }
        )
        result = serialize_to_json(df)
        parsed = json.loads(result)
        record = parsed[0]
        assert record["clause_ref"] is None
        assert record["evidence"] is None
        assert record["responsible_party"] is None
        assert record["deadline"] is None
        assert record["estimated_mitigation_cost"] is None
        assert record["corrective_action_status"] is None

    def test_date_formatted_as_iso_8601(self):
        """Date values are formatted as ISO 8601 (YYYY-MM-DD)."""
        df = pd.DataFrame(
            {
                "finding_id": ["NCM-01"],
                "finding_type": ["NCM"],
                "process_zone": ["Logistics"],
                "deadline": [date(2025, 6, 30)],
            }
        )
        result = serialize_to_json(df)
        parsed = json.loads(result)
        assert parsed[0]["deadline"] == "2025-06-30"

    def test_includes_all_optional_fields(self):
        """JSON includes all optional fields even when null."""
        df = pd.DataFrame(
            {
                "finding_id": ["NCM-01"],
                "finding_type": ["NCM"],
                "description": ["A finding"],
                "standards": ["ISO 9001:2015"],
                "process_zone": ["Logistics"],
                "clause_ref": ["4.4"],
                "evidence": ["Some evidence"],
                "is_transversal": [False],
                "responsible_party": ["John Doe"],
                "deadline": [date(2025, 12, 1)],
                "estimated_mitigation_cost": [1500.50],
                "corrective_action_status": ["open"],
            }
        )
        result = serialize_to_json(df)
        parsed = json.loads(result)
        record = parsed[0]
        assert record["responsible_party"] == "John Doe"
        assert record["deadline"] == "2025-12-01"
        assert record["estimated_mitigation_cost"] == 1500.50
        assert record["corrective_action_status"] == "open"

    def test_boolean_serialization(self):
        """Boolean values are serialized as JSON booleans."""
        df = pd.DataFrame(
            {
                "finding_id": ["NCM-01"],
                "finding_type": ["NCM"],
                "process_zone": ["Logistics"],
                "is_transversal": [True],
            }
        )
        result = serialize_to_json(df)
        parsed = json.loads(result)
        assert parsed[0]["is_transversal"] is True

    def test_output_uses_indent_2(self):
        """Output JSON uses indent=2 for readability."""
        df = pd.DataFrame(
            {
                "finding_id": ["NCM-01"],
                "finding_type": ["NCM"],
                "process_zone": ["Logistics"],
            }
        )
        result = serialize_to_json(df)
        # Indented JSON should have lines starting with spaces
        lines = result.split("\n")
        # Second line should be indented
        assert lines[1].startswith("  ")

    def test_empty_dataframe_produces_empty_array(self):
        """Empty DataFrame produces an empty JSON array."""
        df = pd.DataFrame(
            {
                "finding_id": pd.Series([], dtype=str),
                "finding_type": pd.Series([], dtype=str),
                "process_zone": pd.Series([], dtype=str),
            }
        )
        result = serialize_to_json(df)
        parsed = json.loads(result)
        assert parsed == []


# =============================================================================
# Tests: validate_roundtrip
# =============================================================================


class TestValidateRoundtrip:
    """Tests for round-trip validation."""

    def test_returns_false_when_serialization_fails(self):
        """Returns False when format_to_markdown raises (missing columns)."""
        df = pd.DataFrame({"bad_column": ["value"]})
        result = validate_roundtrip("some markdown", df)
        assert result is False

    def test_returns_false_when_null_mandatory_fields(self):
        """Returns False when mandatory fields have nulls."""
        df = pd.DataFrame(
            {
                "finding_id": [None],
                "finding_type": ["NCM"],
                "process_zone": ["Logistics"],
            }
        )
        result = validate_roundtrip("some markdown", df)
        assert result is False

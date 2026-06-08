"""
Pretty_Printer module for the SGI Audit Dashboard.

Serializes a findings DataFrame back into valid pipe-delimited Markdown
tables, and provides JSON serialization. Guarantees round-trip consistency
with the Parser module.

Design decisions:
- Validation before serialization: raise early without partial output
- Pipe-delimited Markdown matching Parser's expected input format
- Empty cells for optional null fields to preserve schema structure
- JSON serialization uses snake_case field names matching DataFrame columns
- Round-trip validation uses tempfile for intermediate parse step
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Optional

import pandas as pd


# =============================================================================
# Exception Classes
# =============================================================================


class SerializationError(Exception):
    """Raised when DataFrame serialization fails validation.

    Attributes:
        rows: List of row indices that failed validation.
        columns: List of column names that failed validation.
        message: Human-readable error description.
    """

    def __init__(
        self,
        message: str,
        rows: Optional[list[int]] = None,
        columns: Optional[list[str]] = None,
    ) -> None:
        self.rows = rows or []
        self.columns = columns or []
        super().__init__(message)


# =============================================================================
# Constants
# =============================================================================

_REQUIRED_COLUMNS = ["finding_id", "finding_type", "process_zone"]
"""Columns that must exist in the DataFrame."""

_MANDATORY_FIELDS = ["finding_id", "finding_type", "process_zone"]
"""Columns that must not contain null values."""

_MARKDOWN_COLUMNS = [
    "ID",
    "Type",
    "Standard(s)",
    "Process Zone",
    "Clause",
    "Description",
    "Evidence",
]
"""Column headers for the output Markdown table."""

_COLUMN_MAPPING = {
    "finding_id": "ID",
    "finding_type": "Type",
    "standards": "Standard(s)",
    "process_zone": "Process Zone",
    "clause_ref": "Clause",
    "description": "Description",
    "evidence": "Evidence",
}
"""Mapping from DataFrame column names to Markdown header names."""


# =============================================================================
# Public Functions
# =============================================================================


def format_to_markdown(df: pd.DataFrame) -> str:
    """Format a findings DataFrame into a Markdown table string.

    Column order: ID | Type | Standard(s) | Process Zone | Clause |
                  Description | Evidence

    Args:
        df: DataFrame with required columns. Must not have null values
            in mandatory fields (finding_id, finding_type, process_zone).

    Returns:
        Markdown string with pipe-delimited table, header row,
        and separator row.

    Raises:
        SerializationError: If required columns are missing or mandatory
                           fields contain null values. Error specifies
                           affected rows and columns.
    """
    # Validate required columns exist
    missing_columns = [
        col for col in _REQUIRED_COLUMNS if col not in df.columns
    ]
    if missing_columns:
        raise SerializationError(
            f"Missing required columns: {missing_columns}",
            columns=missing_columns,
        )

    # Check no null values in mandatory fields
    null_info: dict[str, list[int]] = {}
    for col in _MANDATORY_FIELDS:
        null_mask = df[col].isnull()
        if null_mask.any():
            null_info[col] = df.index[null_mask].tolist()

    if null_info:
        all_rows = sorted(
            set(row for rows in null_info.values() for row in rows)
        )
        all_columns = list(null_info.keys())
        details = ", ".join(
            f"column '{col}' has null values in rows {rows}"
            for col, rows in null_info.items()
        )
        raise SerializationError(
            f"Mandatory fields contain null values: {details}",
            rows=all_rows,
            columns=all_columns,
        )

    # Build Markdown table
    header = "| " + " | ".join(_MARKDOWN_COLUMNS) + " |"
    separator = "| " + " | ".join(["---"] * len(_MARKDOWN_COLUMNS)) + " |"

    rows: list[str] = []
    for _, row in df.iterrows():
        cells = [
            _safe_cell(row.get("finding_id", "")),
            _safe_cell(row.get("finding_type", "")),
            _safe_cell(row.get("standards", "")),
            _safe_cell(row.get("process_zone", "")),
            _safe_cell(row.get("clause_ref", "")),
            _safe_cell(row.get("description", "")),
            _safe_cell(row.get("evidence", "")),
        ]
        rows.append("| " + " | ".join(cells) + " |")

    return "\n".join([header, separator] + rows)


def validate_roundtrip(original_md: str, df: pd.DataFrame) -> bool:
    """Validate that parse(print(df)) produces a DataFrame identical to df.

    This implements the round-trip invariant:
        parse(format_to_markdown(parse(original_md))) == parse(original_md)

    The function applies format_to_markdown(df) then parses the result with
    parse_markdown_report, comparing: same column names, same row count,
    and cell-by-cell string equality after stripping whitespace.

    Args:
        original_md: The original Markdown source text.
        df: The DataFrame produced by parsing original_md.

    Returns:
        True if round-trip produces identical DataFrame, False otherwise.
    """
    from src.parser import parse_markdown_report

    try:
        # Step 1: Serialize the DataFrame back to Markdown
        md_output = format_to_markdown(df)

        # Step 2: Write to a temp file since parse_markdown_report takes a file_path
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".md",
            encoding="utf-8",
            delete=False,
        ) as tmp_file:
            tmp_file.write(md_output)
            tmp_path = tmp_file.name

        try:
            # Step 3: Parse the generated Markdown back into a DataFrame
            reparsed_df = parse_markdown_report(tmp_path)
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

        # Step 4: Compare the DataFrames
        # Check same column names
        if set(df.columns) != set(reparsed_df.columns):
            return False

        # Check same row count
        if len(df) != len(reparsed_df):
            return False

        # Compare columns that exist in both DataFrames
        common_columns = list(set(df.columns) & set(reparsed_df.columns))

        # Cell-by-cell string equality after stripping whitespace
        for col in common_columns:
            for i in range(len(df)):
                original_val = df.iloc[i][col]
                reparsed_val = reparsed_df.iloc[i][col]

                # Convert both to strings for comparison, handling None/NaN
                orig_str = "" if (original_val is None or (isinstance(original_val, float) and pd.isna(original_val))) else str(original_val).strip()
                repr_str = "" if (reparsed_val is None or (isinstance(reparsed_val, float) and pd.isna(reparsed_val))) else str(reparsed_val).strip()

                if orig_str != repr_str:
                    return False

        return True

    except Exception:
        # If any step fails (serialization, parsing, comparison), round-trip fails
        return False


def serialize_to_json(df: pd.DataFrame) -> str:
    """Serialize a findings DataFrame to a JSON array string.

    Produces a JSON array where each finding is a flat object with
    snake_case field names matching the DataFrame column names.

    - Dates are formatted as ISO 8601 (YYYY-MM-DD)
    - Empty optional fields use JSON null
    - All fields are included (including optional ones: responsible_party,
      deadline, estimated_mitigation_cost, corrective_action_status)
    - Output uses indent=2 for readability

    Args:
        df: DataFrame with findings data.

    Returns:
        JSON string representing the array of finding objects.
    """
    records = []

    for _, row in df.iterrows():
        record: dict = {}

        for col in df.columns:
            value = row[col]

            # Handle None/NaN → JSON null
            if value is None or (isinstance(value, float) and pd.isna(value)):
                record[col] = None
            # Handle date objects → ISO 8601 string
            elif hasattr(value, "strftime"):
                record[col] = value.strftime("%Y-%m-%d")
            # Handle pandas Timestamp
            elif isinstance(value, pd.Timestamp):
                record[col] = value.strftime("%Y-%m-%d")
            # Handle boolean (must be before numeric check since bool is subclass of int)
            elif isinstance(value, bool):
                record[col] = value
            # Handle numeric values
            elif isinstance(value, (int, float)):
                record[col] = value
            # Everything else → string
            else:
                record[col] = str(value)

        records.append(record)

    return json.dumps(records, indent=2, ensure_ascii=False)


# =============================================================================
# Private Helpers
# =============================================================================


def _safe_cell(value) -> str:
    """Convert a cell value to a safe string for Markdown output.

    Handles None, NaN, and other falsy values by returning an empty string.
    Pipes within cell content are escaped to avoid breaking the table format.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    cell_str = str(value)
    # Escape pipes to avoid breaking Markdown table
    cell_str = cell_str.replace("|", "\\|")
    return cell_str

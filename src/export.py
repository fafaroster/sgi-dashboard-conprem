"""
Export module for the SGI Audit Dashboard.

Provides CSV data export and export UI controls for Streamlit.

Design decisions:
- CSV export includes filter metadata as comment header lines (# prefix)
- export_csv returns bytes (suitable for st.download_button) or None if no data
- PNG/SVG export deferred to kaleido package; Streamlit's built-in Plotly
  SVG rendering is available in-browser as an alternative
- render_export_controls handles all UI state and error display
- ExportError raised on generation failures for graceful error handling
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

import pandas as pd

from src.dashboard.filters import FilterState


# =============================================================================
# Exceptions
# =============================================================================


class ExportError(Exception):
    """Raised when export file generation fails.

    Attributes:
        message: Human-readable description of the failure.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


# =============================================================================
# CSV Export
# =============================================================================


def export_csv(
    df: pd.DataFrame,
    filters: FilterState,
    filename_prefix: str = "sgi_findings",
) -> Optional[bytes]:
    """Generate CSV bytes from a filtered findings DataFrame.

    The CSV includes:
    - Header comment lines (starting with #) documenting the export date
      and active filter configuration
    - All metadata columns present in the DataFrame

    Args:
        df: Filtered findings DataFrame to export.
        filters: Active FilterState to include as metadata header.
        filename_prefix: Prefix for the generated filename (informational).

    Returns:
        CSV content as bytes ready for download, or None if the DataFrame
        is empty (caller should show a "no data" message).

    Raises:
        ExportError: If CSV generation fails for any reason.
    """
    if df.empty:
        return None

    try:
        buffer = io.StringIO()

        # Write header comments with export metadata
        export_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        buffer.write(f"# SGI Audit Dashboard - Data Export\n")
        buffer.write(f"# Export Date: {export_date}\n")
        buffer.write(f"# Filename Prefix: {filename_prefix}\n")
        buffer.write(f"#\n")
        buffer.write(f"# Active Filters:\n")
        buffer.write(f"#   Standards: {', '.join(filters.standards)}\n")
        buffer.write(f"#   Finding Types: {', '.join(filters.finding_types)}\n")
        buffer.write(f"#   Process Zones: {', '.join(filters.process_zones)}\n")
        if filters.search_text:
            buffer.write(f'#   Search Text: "{filters.search_text}"\n')
        else:
            buffer.write(f"#   Search Text: (none)\n")
        buffer.write(f"#\n")
        buffer.write(f"# Total Records: {len(df)}\n")
        buffer.write(f"#\n")

        # Write CSV data with all columns
        df.to_csv(buffer, index=False)

        return buffer.getvalue().encode("utf-8")

    except Exception as e:
        raise ExportError(f"Failed to generate CSV export: {e}") from e


# =============================================================================
# Image Export Placeholder
# =============================================================================


def export_png_placeholder() -> str:
    """Return an informational message about PNG/SVG export availability.

    PNG export at 1920×1080 resolution requires the `kaleido` package
    (pip install kaleido). Streamlit's built-in st.plotly_chart already
    supports SVG rendering and image download via the Plotly toolbar
    in the browser.

    Returns:
        Human-readable message explaining export options.
    """
    return (
        "PNG/SVG chart export requires the 'kaleido' package "
        "(pip install kaleido). In the meantime, you can use the camera icon "
        "in the Plotly chart toolbar to download individual charts as PNG, "
        "or use the browser's built-in SVG rendering for vector quality."
    )


# =============================================================================
# Streamlit Export Controls
# =============================================================================


def render_export_controls(df: pd.DataFrame, filters: FilterState) -> None:
    """Render Streamlit UI component with export buttons.

    Provides:
    - "Export CSV" download button with the filtered data
    - Informational message about image export
    - Graceful error handling with st.error

    Args:
        df: Currently filtered findings DataFrame.
        filters: Active FilterState for metadata inclusion.
    """
    import streamlit as st

    st.subheader("📥 Export Data")

    col1, col2 = st.columns(2)

    with col1:
        try:
            csv_data = export_csv(df, filters)

            if csv_data is None:
                st.info(
                    "No data available to export. "
                    "Adjust your filters to include findings."
                )
            else:
                export_date = datetime.now().strftime("%Y%m%d")
                filename = f"sgi_findings_{export_date}.csv"

                st.download_button(
                    label="📄 Export CSV",
                    data=csv_data,
                    file_name=filename,
                    mime="text/csv",
                    help="Download filtered findings as CSV with metadata",
                )

        except ExportError as e:
            st.error(f"Export failed: {e.message}")
        except Exception as e:
            st.error(f"Unexpected export error: {e}")

    with col2:
        st.info(export_png_placeholder())

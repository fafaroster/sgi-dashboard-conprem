"""
Main Streamlit application entry point for the SGI Audit Dashboard.

Wires all dashboard components together:
1. Configures page settings (title, icon, layout)
2. Uses st.cache_data to cache parsed DataFrame (parse once, reuse on interactions)
3. Accepts command-line argument or default file path for the audit report
4. Validates dataset size (rejects >200 findings)
5. Renders components in order: Filters → Executive Summary → HTS Panel →
   Pareto Charts → Risk Heatmap → Maturity Radar → Findings Table →
   Timeline → Export Controls

Requirements: 14.1, 14.2, 14.3, 14.4, 14.5
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path for absolute imports
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st

# =============================================================================
# Page Configuration — MUST be the first Streamlit command
# =============================================================================

_PAGE_TITLE = "SGI Audit Dashboard"
_PAGE_ICON = "📊"

st.set_page_config(
    page_title=_PAGE_TITLE,
    page_icon=_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject futuristic CSS styling (must be right after set_page_config)
from src.dashboard.custom_css import inject_futuristic_css
inject_futuristic_css()

# =============================================================================
# Main Login Gate — protects entire dashboard
# =============================================================================

_MAIN_PASSWORD = "conprem2026"

if not st.session_state.get("main_auth", False):
    st.markdown("## 🔐 Dashboard SGI — CONPREM GRAU")
    st.markdown("Ingrese la clave de acceso para continuar.")
    pwd = st.text_input("Clave de acceso", type="password", key="main_login_input")
    if pwd:
        if pwd == _MAIN_PASSWORD:
            st.session_state["main_auth"] = True
            st.rerun()
        else:
            st.error("Clave incorrecta")
    st.stop()

# =============================================================================
# Remaining imports (after set_page_config)
# =============================================================================

import pandas as pd

from src.parser import parse_markdown_report, ParserError
from src.metrics import (
    calculate_risk_load_score,
    calculate_criticality_rate,
    calculate_maturity_index,
)
from src.dashboard.filters import render_filters_sidebar, apply_filters, FilterState
from src.dashboard.executive_summary import render_executive_summary, compute_executive_metrics
from src.dashboard.pareto import render_pareto_chart, render_pareto_chart_clauses
from src.dashboard.heatmap import render_risk_heatmap
from src.dashboard.radar import render_maturity_radar
from src.dashboard.findings_table import render_findings_table
from src.dashboard.hts_panel import render_hts_panel
from src.dashboard.timeline import render_timeline
from src.export import render_export_controls
from src.dashboard.proposal_viewer import render_proposal_section
from src.dashboard.strategic_plan import render_strategic_plan


# =============================================================================
# Constants
# =============================================================================

_DEFAULT_REPORT_PATH = "data/informe_hallazgos.md"
"""Default path to the audit report file, relative to workspace root."""

_MAX_FINDINGS = 200
"""Maximum number of findings (unique finding IDs) supported."""


# =============================================================================
# Cached Data Loading
# =============================================================================


@st.cache_data(show_spinner="Parsing audit report...")
def load_and_parse_report(file_path: str) -> pd.DataFrame:
    """Parse the Markdown audit report and cache the resulting DataFrame.

    Uses st.cache_data to ensure the file is parsed only once. Subsequent
    Streamlit interactions reuse the cached DataFrame without re-parsing
    (Requirement 14.4).

    Args:
        file_path: Path to the Markdown audit report.

    Returns:
        Parsed findings DataFrame.

    Raises:
        FileNotFoundError: If the report file does not exist.
        ParserError: If the report is malformed.
    """
    return parse_markdown_report(file_path)


# =============================================================================
# Helper: Resolve report file path
# =============================================================================


def _resolve_report_path() -> str:
    """Determine the report file path from command-line args or default.

    Checks sys.argv for a custom path (passed after '--' in streamlit run).
    Falls back to the default path relative to the workspace root.

    Returns:
        Resolved file path string.
    """
    # Check if a custom path was provided via command-line arguments
    # streamlit run src/app.py -- path/to/report.md
    args = sys.argv[1:]  # Skip the script name itself
    for arg in args:
        # Skip Streamlit's own arguments (start with --)
        if arg.startswith("--"):
            continue
        # Skip known Streamlit flags
        if arg in ("run",):
            continue
        # Treat the first non-flag argument as the report path
        if Path(arg).suffix in (".md", ".markdown"):
            return arg

    return _DEFAULT_REPORT_PATH


# =============================================================================
# Main Application
# =============================================================================


def main() -> None:
    """Main application function that wires all dashboard components."""

    # 1. Resolve report file path
    report_path = _resolve_report_path()

    # 3. Load and parse data (cached)
    try:
        df = load_and_parse_report(report_path)
    except FileNotFoundError:
        st.error(
            f"📁 **Report file not found:** `{report_path}`\n\n"
            f"Please ensure the audit report exists at the specified path. "
            f"You can provide a custom path via:\n\n"
            f"```\nstreamlit run src/app.py -- path/to/report.md\n```"
        )
        return
    except ParserError as e:
        st.error(
            f"⚠️ **Error parsing report:** {e}\n\n"
            f"The file `{report_path}` could not be parsed. "
            f"Please verify the Markdown format matches the expected structure."
        )
        if e.line_number:
            st.error(f"Error at line {e.line_number}, field: {e.field_name}")
        return

    # 4. Validate dataset size (Requirement 14.5)
    unique_finding_count = df["finding_id"].nunique() if not df.empty else 0
    if unique_finding_count > _MAX_FINDINGS:
        st.error(
            f"❌ **Dataset too large:** {unique_finding_count} unique findings detected.\n\n"
            f"The dashboard supports a maximum of {_MAX_FINDINGS} findings. "
            f"Please reduce the dataset size or apply pre-filtering to the source file."
        )
        return

    # 5. Render filters sidebar
    filters: FilterState = render_filters_sidebar()

    # 6. Apply filters to cached DataFrame
    filtered_df = apply_filters(df, filters)

    # 7. Compute executive metrics
    metrics = compute_executive_metrics(filtered_df)

    # 8. Render dashboard components in order

    # a. Executive Summary — FIRST SECTION (Requirement 8.2)
    render_executive_summary(filtered_df, metrics)

    st.divider()

    # b. HTS Panel — if transversal findings exist
    render_hts_panel(filtered_df)

    st.divider()

    # c. Pareto Charts — primary (zones) + secondary (clauses)
    st.header("📈 Pareto Analysis")
    col_pareto1, col_pareto2 = st.columns(2)
    with col_pareto1:
        render_pareto_chart(filtered_df, metrics, filters)
    with col_pareto2:
        render_pareto_chart_clauses(filtered_df, filters)

    st.divider()

    # d. Risk Heatmap
    st.header("🔥 Risk Heatmap")
    render_risk_heatmap(filtered_df, filters)

    st.divider()

    # e. Maturity Radar
    st.header("🎯 SGI Maturity Radar")
    render_maturity_radar(filtered_df, metrics)

    st.divider()

    # f. Findings Table
    render_findings_table(filtered_df, filters)

    st.divider()

    # g. Timeline
    render_timeline(filtered_df)

    st.divider()

    # h. Export Controls
    render_export_controls(filtered_df, filters)

    st.divider()

    # =========================================================================
    # Password-protected strategic modules
    # =========================================================================
    st.header("🔐 Módulos Estratégicos (Acceso Restringido)")

    # Single password input at the top — unlocks both tabs for the session
    if not st.session_state.get("auth_granted", False):
        password = st.text_input(
            "🔐 Acceso Módulo Propuesta",
            type="password",
            key="strategic_password_input",
        )
        if password:
            if password == "conprem2026":
                st.session_state["auth_granted"] = True
                st.rerun()
            else:
                st.warning("Clave incorrecta")

    tab1, tab2 = st.tabs(
        ["📋 Propuesta Técnica-Económica", "🎯 Plan Estratégico SGI"]
    )
    with tab1:
        render_proposal_section()
    with tab2:
        render_strategic_plan(filtered_df)


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    main()

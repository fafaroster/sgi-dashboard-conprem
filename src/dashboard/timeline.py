"""
Corrective Action Timeline for the SGI Audit Dashboard.

This module renders a Gantt-style timeline visualization showing corrective
actions with their planned dates, deadlines, status, and responsible parties.
Uses Plotly for interactive dark-theme-compatible visualization.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# =============================================================================
# Constants
# =============================================================================

_STATUS_COLORS = {
    "open": "#6B7280",          # Gray — not started
    "in_progress": "#3B82F6",   # Blue — in progress
    "completed": "#10B981",     # Green — completed
    "verified": "#10B981",      # Green — verified (treated as completed)
    "closed": "#10B981",        # Green — closed (treated as completed)
    "overdue": "#EF4444",       # Red — overdue
}

_STATUS_LABELS = {
    "open": "No Iniciado",
    "in_progress": "En Progreso",
    "completed": "Completado",
    "verified": "Verificado",
    "closed": "Cerrado",
    "overdue": "Vencido",
}

_ITEMS_PER_PAGE = 50
"""Maximum visible actions before pagination kicks in."""

_PLACEHOLDER_TEXT = "Pending Assignment"
"""Placeholder for missing responsible party, deadline, or status fields."""


# =============================================================================
# Public API
# =============================================================================


def render_timeline(df: pd.DataFrame) -> None:
    """Render corrective action Gantt-style timeline.

    Displays a Plotly timeline showing corrective actions with start dates,
    deadlines, and color-coded status. Handles up to 50 visible actions
    with pagination/scroll for more.

    Color coding:
    - Gray: not started (open)
    - Blue: in progress
    - Green: completed/verified/closed
    - Red: overdue (current_date > deadline AND status != completed)

    Missing fields are shown as "Pending Assignment" placeholders.
    Empty/no deadline data shows an informational message.

    Args:
        df: Findings DataFrame with optional CAPA fields:
            - corrective_action_status (str or None)
            - deadline (date/str or None)
            - responsible_party (str or None)
            - finding_id (str)
            - description (str)

    Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
    """
    st.subheader("📅 Línea de Tiempo — Acciones Correctivas")

    # Prepare timeline data
    timeline_data = _prepare_timeline_data(df)

    if timeline_data.empty:
        st.info(
            "ℹ️ No hay datos de acciones correctivas disponibles. "
            "Las fechas límite y estados se mostrarán cuando sean asignados."
        )
        return

    # Pagination for > 50 items (Requirement 12.6)
    total_actions = len(timeline_data)
    if total_actions > _ITEMS_PER_PAGE:
        total_pages = (total_actions + _ITEMS_PER_PAGE - 1) // _ITEMS_PER_PAGE
        page = st.selectbox(
            "Página",
            range(1, total_pages + 1),
            format_func=lambda x: f"Página {x} de {total_pages} ({total_actions} acciones)",
            key="timeline_page",
        )
        start_idx = (page - 1) * _ITEMS_PER_PAGE
        end_idx = start_idx + _ITEMS_PER_PAGE
        page_data = timeline_data.iloc[start_idx:end_idx].copy()
    else:
        page_data = timeline_data.copy()

    # Build and display Plotly Gantt chart
    fig = _build_gantt_chart(page_data)
    st.plotly_chart(fig, use_container_width=True, key="timeline_chart")

    # Display legend
    _render_legend()


# =============================================================================
# Private Helpers
# =============================================================================


def _prepare_timeline_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare timeline data from the findings DataFrame.

    Extracts corrective action information and determines visual status
    (including overdue detection). Filters to rows that have at least
    a deadline or a corrective action status.

    Args:
        df: Full findings DataFrame.

    Returns:
        DataFrame with columns: Task, Start, Finish, Status, Color,
        Responsible, StatusLabel, Description. Empty if no timeline data.
    """
    # Check if CAPA fields exist
    has_status = "corrective_action_status" in df.columns
    has_deadline = "deadline" in df.columns
    has_responsible = "responsible_party" in df.columns

    if not has_status and not has_deadline:
        return pd.DataFrame()

    # Deduplicate by finding_id (multi-standard findings share same CAPA)
    if "finding_id" in df.columns:
        work_df = df.drop_duplicates(subset=["finding_id"]).copy()
    else:
        work_df = df.copy()

    # Filter to rows with at least some CAPA data
    mask = pd.Series(False, index=work_df.index)
    if has_status:
        mask = mask | work_df["corrective_action_status"].notna()
    if has_deadline:
        mask = mask | work_df["deadline"].notna()

    capa_df = work_df[mask].copy()

    if capa_df.empty:
        return pd.DataFrame()

    today = date.today()
    rows = []

    for _, row in capa_df.iterrows():
        finding_id = row.get("finding_id", "Unknown")
        description = row.get("description", "")

        # Responsible party (Requirement 12.3)
        responsible = _PLACEHOLDER_TEXT
        if has_responsible and pd.notna(row.get("responsible_party")):
            responsible = str(row["responsible_party"]).strip()
            if not responsible:
                responsible = _PLACEHOLDER_TEXT

        # Deadline handling
        deadline_date = _parse_date(row.get("deadline") if has_deadline else None)

        # Status handling (Requirement 12.3, 12.4)
        raw_status = None
        if has_status and pd.notna(row.get("corrective_action_status")):
            raw_status = str(row["corrective_action_status"]).strip().lower()

        # Determine display status with overdue logic (Requirement 12.4)
        display_status = _determine_display_status(raw_status, deadline_date, today)

        # Determine start and finish dates for the Gantt bar
        start_date, finish_date = _compute_date_range(deadline_date, today)

        color = _STATUS_COLORS.get(display_status, _STATUS_COLORS["open"])
        label = _STATUS_LABELS.get(display_status, "Desconocido")

        # Build task label
        task_label = f"{finding_id}"
        if responsible != _PLACEHOLDER_TEXT:
            task_label += f" ({responsible})"

        rows.append({
            "Task": task_label,
            "Start": start_date,
            "Finish": finish_date,
            "Status": display_status,
            "Color": color,
            "Responsible": responsible,
            "StatusLabel": label,
            "Description": (
                description[:80] + "..." if len(str(description)) > 80 else description
            ),
            "FindingID": finding_id,
        })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def _build_gantt_chart(data: pd.DataFrame) -> go.Figure:
    """Build a Plotly Gantt chart from prepared timeline data.

    Args:
        data: Prepared DataFrame with Task, Start, Finish, Color, etc.

    Returns:
        Plotly Figure configured for dark theme.
    """
    fig = px.timeline(
        data,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="StatusLabel",
        color_discrete_map={
            "No Iniciado": _STATUS_COLORS["open"],
            "En Progreso": _STATUS_COLORS["in_progress"],
            "Completado": _STATUS_COLORS["completed"],
            "Verificado": _STATUS_COLORS["verified"],
            "Cerrado": _STATUS_COLORS["closed"],
            "Vencido": _STATUS_COLORS["overdue"],
        },
        hover_data={"Description": True, "Responsible": True, "Start": True, "Finish": True},
    )

    # Dark theme styling + transparent backgrounds
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(10, 15, 30, 0.4)",
        font=dict(color="#e2e8f0", size=12),
        title=dict(
            text="Acciones Correctivas — Línea de Tiempo",
            font=dict(size=16, color="#e2e8f0"),
        ),
        xaxis=dict(
            title="Fecha",
            gridcolor="rgba(99, 102, 241, 0.1)",
            showgrid=True,
        ),
        yaxis=dict(
            title="",
            autorange="reversed",
            gridcolor="rgba(99, 102, 241, 0.1)",
        ),
        legend=dict(
            title="Estado",
            bgcolor="rgba(15, 23, 42, 0.6)",
            bordercolor="rgba(99, 102, 241, 0.3)",
            borderwidth=1,
        ),
        height=max(400, len(data) * 35 + 100),
        margin=dict(l=20, r=20, t=60, b=40),
    )

    return fig


def _render_legend() -> None:
    """Render a color-coded legend below the chart."""
    cols = st.columns(5)
    legend_items = [
        ("⬜ No Iniciado", "#6B7280"),
        ("🔵 En Progreso", "#3B82F6"),
        ("🟢 Completado", "#10B981"),
        ("🔴 Vencido", "#EF4444"),
        ("📋 Pendiente", "#888"),
    ]
    for col, (label, _) in zip(cols, legend_items):
        col.caption(label)


def _determine_display_status(
    raw_status: Optional[str],
    deadline_date: Optional[date],
    today: date,
) -> str:
    """Determine the visual display status including overdue detection.

    Overdue logic (Requirement 12.4):
    current_date > deadline AND status != "completed" (and not verified/closed)

    Args:
        raw_status: Raw status string (lowercase) or None.
        deadline_date: Parsed deadline date or None.
        today: Current date for overdue comparison.

    Returns:
        Display status key for color mapping.
    """
    # If no status, treat as "open" (not started)
    if raw_status is None:
        raw_status = "open"

    # Normalize status
    completed_statuses = {"completed", "verified", "closed"}

    # Check overdue condition: past deadline and not completed
    if (
        deadline_date is not None
        and today > deadline_date
        and raw_status not in completed_statuses
    ):
        return "overdue"

    # Map to known statuses
    if raw_status in _STATUS_COLORS:
        return raw_status

    # Fallback
    return "open"


def _compute_date_range(
    deadline_date: Optional[date],
    today: date,
) -> tuple[date, date]:
    """Compute start and finish dates for a Gantt bar.

    If no deadline is available, uses today as reference with a
    default 30-day span.

    Args:
        deadline_date: Target deadline date or None.
        today: Current date.

    Returns:
        Tuple of (start_date, finish_date).
    """
    if deadline_date is not None:
        # Assume a 30-day action window ending at deadline
        start_date = deadline_date - timedelta(days=30)
        finish_date = deadline_date
    else:
        # No deadline: show from today with 30-day placeholder span
        start_date = today
        finish_date = today + timedelta(days=30)

    return start_date, finish_date


def _parse_date(value) -> Optional[date]:
    """Parse a date value from various formats.

    Accepts: date objects, datetime objects, ISO 8601 strings (YYYY-MM-DD),
    pandas Timestamp. Returns None for unparseable or null values.

    Args:
        value: Date value to parse.

    Returns:
        date object or None.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, pd.Timestamp):
        return value.date()

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

    return None

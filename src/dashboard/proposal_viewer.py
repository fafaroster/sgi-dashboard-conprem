"""
Propuesta Técnica-Económica Viewer module.

Renders the full technical-economic proposal document within the dashboard.
Access is protected by a shared session-state password gate (auth_granted).

Requirements: Module A — Password-protected proposal viewer.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st


# =============================================================================
# Constants
# =============================================================================

_PROPOSAL_FILE = "PROPUESTA_TECNICA_ECONOMICA_SGI.md"
"""Filename of the proposal document at the workspace root."""


# =============================================================================
# Public API
# =============================================================================


def render_proposal_section() -> None:
    """Display the full Propuesta Técnica-Económica if authenticated.

    Reads the proposal Markdown file from the workspace root at runtime
    and renders it using st.markdown(). Requires prior authentication
    via the shared session_state key ``auth_granted``.

    If not authenticated, shows a locked message.
    """
    if not st.session_state.get("auth_granted", False):
        st.info("🔒 Este módulo requiere acceso autorizado")
        return

    # Resolve file path relative to workspace root
    workspace_root = Path(__file__).resolve().parent.parent.parent
    proposal_path = workspace_root / _PROPOSAL_FILE

    if not proposal_path.exists():
        st.error(
            f"📁 No se encontró el archivo de propuesta: `{_PROPOSAL_FILE}`\n\n"
            f"Asegúrese de que el archivo existe en la raíz del proyecto."
        )
        return

    content = proposal_path.read_text(encoding="utf-8")
    st.markdown(content, unsafe_allow_html=False)

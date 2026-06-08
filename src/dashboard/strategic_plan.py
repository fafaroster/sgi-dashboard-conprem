"""
Plan Estratégico SGI — CONPREM GRAU.

Módulo estratégico completo con 4 frameworks:
1. Balanced Scorecard (4 perspectivas, gauges, tablas)
2. Hoshin Kanri (visión, breakthroughs, Matriz X, catchball)
3. FODA + Mapa Estratégico (Sankey)
4. Plan OdM + Roadmap (data_editor + Gantt 12 meses)

Acceso protegido por auth_granted en session_state.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st


# =============================================================================
# Visual Theme Constants
# =============================================================================

_PAPER_BG = "rgba(0,0,0,0)"
_PLOT_BG = "rgba(10,15,30,0.4)"
_FONT_COLOR = "#e2e8f0"
_GRID_COLOR = "rgba(255,255,255,0.08)"

_LAYOUT_DEFAULTS = dict(
    paper_bgcolor=_PAPER_BG,
    plot_bgcolor=_PLOT_BG,
    font=dict(color=_FONT_COLOR, size=12),
    margin=dict(l=30, r=30, t=50, b=30),
)


# =============================================================================
# BSC Data — 4 Perspectivas × 4 Objetivos
# =============================================================================

_BSC_FINANCIERA = [
    {"Objetivo": "Aumentar ingresos ISO-dependientes", "KPI": "Ingresos nuevos licitaciones (CLP)", "Baseline": "$0", "Meta": "+$800M CLP/año", "Iniciativa": "Certificación triple norma como habilitante", "Vinculado a NCM": "NCM-15"},
    {"Objetivo": "Reducir costo no-calidad", "KPI": "% reproceso sobre producción", "Baseline": "8%", "Meta": "<2%", "Iniciativa": "Controles estadísticos de proceso", "Vinculado a NCM": "NCM-05, NCM-14"},
    {"Objetivo": "Evitar multas regulatorias", "KPI": "N° multas SMA/DT/Seremi", "Baseline": "Riesgo alto", "Meta": "0 multas", "Iniciativa": "Programa cumplimiento legal", "Vinculado a NCM": "NCM-08, NCM-10, NCM-11"},
    {"Objetivo": "Reducir prima seguro laboral", "KPI": "Cotización adicional Ley 16.744", "Baseline": "3.4%", "Meta": "2.4% (-1 punto)", "Iniciativa": "Sistema gestión SSO", "Vinculado a NCM": "NCM-02, NCM-04"},
]

_BSC_CLIENTES = [
    {"Objetivo": "Satisfacción cliente ≥90%", "KPI": "Índice satisfacción EFE/MOP", "Baseline": "Sin medición", "Meta": "≥90%", "Iniciativa": "Encuesta + acción correctiva", "Vinculado a NCM": "NCM-15"},
    {"Objetivo": "Certificación como habilitante", "KPI": "Estado certificación ISO", "Baseline": "No certificado", "Meta": "Certificado emitido", "Iniciativa": "Implementación SGI completa", "Vinculado a NCM": "NCM-01 a NCM-15"},
    {"Objetivo": "Confiabilidad de entregas ≥95%", "KPI": "% entregas a tiempo", "Baseline": "~80%", "Meta": "≥95%", "Iniciativa": "Planificación producción + control MP", "Vinculado a NCM": "NCM-06, NCM-09"},
    {"Objetivo": "Trazabilidad garantizada", "KPI": "% lotes con trazabilidad completa", "Baseline": "0%", "Meta": "100%", "Iniciativa": "Sistema identificación y registros", "Vinculado a NCM": "NCM-07, NCM-12"},
]

_BSC_PROCESOS = [
    {"Objetivo": "Cero NCMs abiertas", "KPI": "N° NCMs activas", "Baseline": "15", "Meta": "0", "Iniciativa": "Plan cierre 15 NCMs", "Vinculado a NCM": "NCM-01 a NCM-15"},
    {"Objetivo": "Controles operacionales formalizados", "KPI": "% procedimientos documentados", "Baseline": "~20%", "Meta": "100%", "Iniciativa": "Documentación SGI", "Vinculado a NCM": "NCM-14, NCM-13"},
    {"Objetivo": "MP sin deterioro almacenamiento", "KPI": "% MP conforme en inspección", "Baseline": "~60%", "Meta": "≥98%", "Iniciativa": "Mejora almacenamiento + FIFO", "Vinculado a NCM": "NCM-06, NCM-09"},
    {"Objetivo": "Emergencias preparadas", "KPI": "N° simulacros ejecutados/año", "Baseline": "0", "Meta": "≥4/año", "Iniciativa": "Plan emergencia + simulacros", "Vinculado a NCM": "NCM-03, NCM-11"},
]

_BSC_APRENDIZAJE = [
    {"Objetivo": "Competencia SGI del personal", "KPI": "% personal capacitado SGI", "Baseline": "0%", "Meta": "100%", "Iniciativa": "Plan capacitación anual", "Vinculado a NCM": "NCM-13"},
    {"Objetivo": "Cultura de reporte instalada", "KPI": "N° reportes incidentes/mes", "Baseline": "0", "Meta": "≥5/mes", "Iniciativa": "Sistema reporte no punitivo", "Vinculado a NCM": "NCM-02, NCM-04"},
    {"Objetivo": "Auditoría interna operativa", "KPI": "N° auditorías internas/año", "Baseline": "0", "Meta": "≥2/año", "Iniciativa": "Formar auditores internos", "Vinculado a NCM": "NCM-15"},
    {"Objetivo": "Digitalización registros SGI", "KPI": "% registros digitalizados", "Baseline": "~5%", "Meta": "≥80%", "Iniciativa": "Plataforma digital SGI", "Vinculado a NCM": "NCM-07, NCM-12"},
]

_BSC_PERSPECTIVES = [
    ("💰 Financiera", _BSC_FINANCIERA, 15, "#22c55e"),
    ("🤝 Clientes", _BSC_CLIENTES, 12, "#3b82f6"),
    ("⚙️ Procesos Internos", _BSC_PROCESOS, 18, "#f59e0b"),
    ("📚 Aprendizaje y Crecimiento", _BSC_APRENDIZAJE, 10, "#a855f7"),
]


# =============================================================================
# Hoshin Kanri Data
# =============================================================================

_HOSHIN_VISION = (
    "Para 2027, CONPREM GRAU será la única empresa de durmientes pretensados "
    "en Chile con certificación triple norma (ISO 9001 + 14001 + 45001), "
    "consolidando su posición monopólica y habilitando acceso irrestricto a "
    "licitaciones EFE/MOP y contratos mineros de gran escala."
)

_BREAKTHROUGHS = [
    {"titulo": "Certificación Triple Norma", "meta": "Certificado Q1 2027", "kpi": "3 normas certificadas", "actual": "0/3"},
    {"titulo": "Cero NCMs Activas", "meta": "0 NCMs en 6 meses", "kpi": "NCMs cerradas", "actual": "0/15"},
    {"titulo": "Cartera +$2.000M CLP", "meta": "Nuevas licitaciones 2026-2028", "kpi": "Ingresos adicionales", "actual": "$0"},
]

_ANNUAL_OBJECTIVES = [
    "Cierre 15 NCMs",
    "Documentación SGI 100%",
    "Capacitación personal completa",
    "Auditoría interna operativa",
    "Certificación otorgada",
]

# Matriz X: correlación entre breakthroughs (filas) y objetivos anuales (cols)
# 0=sin relación, 1=contribuye, 2=crítico
_MATRIX_X = np.array([
    [2, 2, 1, 2, 2],  # Certificación Triple Norma
    [2, 1, 1, 1, 1],  # Cero NCMs
    [1, 0, 0, 1, 2],  # Cartera +$2.000M
])


# =============================================================================
# FODA Data
# =============================================================================

_FORTALEZAS = [
    "Monopolio nacional en durmientes pretensados",
    "Infraestructura productiva instalada y operativa",
    "Relación comercial consolidada con EFE y MOP",
    "Barrera técnica alta para nuevos competidores",
    "Nave interior ordenada con potencial de mejora rápida",
]

_DEBILIDADES = [
    "SGI no implementado (0% formalización)",
    "15 No Conformidades Mayores activas (NCM-01 a NCM-15)",
    "0 auditorías internas realizadas históricamente",
    "Almacenamiento deficiente de materias primas y RRPP",
    "Sin sistema de trazabilidad de productos",
]

_OPORTUNIDADES = [
    "Licitaciones EFE 2026-2028 con requisito ISO obligatorio",
    "Expansión minera requiere durmientes en nuevos proyectos",
    "Certificación como barrera permanente a importadores",
    "Exportación a mercados sudamericanos (Perú, Argentina)",
    "Fondos CORFO para implementación de sistemas de gestión",
]

_AMENAZAS = [
    "Exigencias ISO como requisito excluyente en licitaciones",
    "Importadores de Turquía/China con precios competitivos",
    "Fiscalización intensificada post-accidente ferroviario",
    "SMA con criterios endurecidos para industria de hormigón",
    "Riesgo reputacional ante incidentes sin sistema de gestión",
]


# =============================================================================
# OdM Default Data
# =============================================================================

_ODM_DEFAULT = [
    {"ID": "OdM-01", "Descripción": "Implementar sistema de gestión documental digital", "Zona": "Oficina SGI", "Estado": "No iniciado", "Responsable": "Jefe SGI", "Plazo": date.today() + timedelta(days=60)},
    {"ID": "OdM-02", "Descripción": "Establecer programa de calibración de equipos de medición", "Zona": "Laboratorio", "Estado": "No iniciado", "Responsable": "Jefe Calidad", "Plazo": date.today() + timedelta(days=90)},
    {"ID": "OdM-03", "Descripción": "Desarrollar plan de capacitación SGI para todo el personal", "Zona": "Planta general", "Estado": "No iniciado", "Responsable": "RRHH", "Plazo": date.today() + timedelta(days=45)},
    {"ID": "OdM-04", "Descripción": "Implementar sistema FIFO en bodega de materias primas", "Zona": "Bodega MP", "Estado": "No iniciado", "Responsable": "Jefe Bodega", "Plazo": date.today() + timedelta(days=30)},
    {"ID": "OdM-05", "Descripción": "Instalar contención secundaria en zona de químicos", "Zona": "Patio químicos", "Estado": "No iniciado", "Responsable": "Jefe Planta", "Plazo": date.today() + timedelta(days=45)},
    {"ID": "OdM-06", "Descripción": "Crear programa de auditoría interna con ciclo semestral", "Zona": "Toda la planta", "Estado": "No iniciado", "Responsable": "Coord. SGI", "Plazo": date.today() + timedelta(days=120)},
    {"ID": "OdM-07", "Descripción": "Digitalizar registros de trazabilidad por lote", "Zona": "Producción", "Estado": "No iniciado", "Responsable": "Jefe Producción", "Plazo": date.today() + timedelta(days=90)},
    {"ID": "OdM-08", "Descripción": "Implementar indicadores de desempeño SGI (dashboard)", "Zona": "Gerencia", "Estado": "No iniciado", "Responsable": "Consultor SGI", "Plazo": date.today() + timedelta(days=60)},
    {"ID": "OdM-09", "Descripción": "Rediseñar layout almacenamiento productos terminados", "Zona": "Patio PT", "Estado": "No iniciado", "Responsable": "Jefe Logística", "Plazo": date.today() + timedelta(days=75)},
    {"ID": "OdM-10", "Descripción": "Establecer sistema de reporte de incidentes no punitivo", "Zona": "Toda la planta", "Estado": "No iniciado", "Responsable": "Prevencionista", "Plazo": date.today() + timedelta(days=30)},
]


# =============================================================================
# Roadmap / Gantt Data
# =============================================================================

_GANTT_MILESTONES = [
    {"Hito": "Diagnóstico y cierre NCMs críticas", "Inicio": 0, "Duración": 3, "Framework": "BSC"},
    {"Hito": "Documentación SGI completa", "Inicio": 1, "Duración": 4, "Framework": "BSC"},
    {"Hito": "Programa calibración implementado", "Inicio": 0, "Duración": 3, "Framework": "BSC"},
    {"Hito": "Capacitación personal SGI 100%", "Inicio": 1, "Duración": 5, "Framework": "Hoshin"},
    {"Hito": "Controles operacionales formalizados", "Inicio": 2, "Duración": 4, "Framework": "BSC"},
    {"Hito": "Simulacros emergencia ejecutados", "Inicio": 3, "Duración": 2, "Framework": "FODA"},
    {"Hito": "Auditoría interna ciclo 1", "Inicio": 5, "Duración": 1, "Framework": "Hoshin"},
    {"Hito": "Mejora almacenamiento MP", "Inicio": 1, "Duración": 3, "Framework": "FODA"},
    {"Hito": "Trazabilidad digital operativa", "Inicio": 3, "Duración": 4, "Framework": "BSC"},
    {"Hito": "Pre-auditoría certificación", "Inicio": 7, "Duración": 1, "Framework": "Hoshin"},
    {"Hito": "Auditoría certificación triple norma", "Inicio": 8, "Duración": 1, "Framework": "Hoshin"},
    {"Hito": "Certificación emitida", "Inicio": 9, "Duración": 1, "Framework": "Hoshin"},
    {"Hito": "Postulación licitaciones EFE 2026", "Inicio": 9, "Duración": 3, "Framework": "Hoshin"},
]


# =============================================================================
# Public API
# =============================================================================


def render_strategic_plan(df: pd.DataFrame) -> None:
    """Renderiza el Plan Estratégico SGI completo con 4 tabs de frameworks."""

    if not st.session_state.get("auth_granted", False):
        st.info("🔒 Este módulo requiere acceso autorizado")
        return

    st.markdown("### 🎯 Plan Estratégico SGI — CONPREM GRAU")
    st.caption("Frameworks integrados para la transformación del Sistema de Gestión Integrado")

    tab_bsc, tab_hoshin, tab_foda, tab_plan = st.tabs([
        "📊 Balanced Scorecard", "🎯 Hoshin Kanri",
        "🔍 FODA + Mapa Estratégico", "📋 Plan OdM + Roadmap"
    ])

    with tab_bsc:
        _render_balanced_scorecard()

    with tab_hoshin:
        _render_hoshin_kanri()

    with tab_foda:
        _render_foda_mapa()

    with tab_plan:
        _render_plan_odm_roadmap(df)


# =============================================================================
# TAB 1: BALANCED SCORECARD
# =============================================================================


def _render_balanced_scorecard() -> None:
    """BSC con 4 gauges + 4 tablas detalladas."""

    st.markdown("#### 📊 Balanced Scorecard — Estado Actual")
    st.markdown(
        "Situación base pre-implementación SGI. "
        "Todas las perspectivas parten desde niveles mínimos de madurez."
    )

    # --- Gauge Charts ---
    st.markdown("##### Progreso por Perspectiva")
    cols = st.columns(4)

    for i, (nombre, _, baseline, color) in enumerate(_BSC_PERSPECTIVES):
        with cols[i]:
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=baseline,
                number={"suffix": "%", "font": {"size": 28, "color": _FONT_COLOR}},
                title={"text": nombre, "font": {"size": 13, "color": _FONT_COLOR}},
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": _FONT_COLOR, "dtick": 25},
                    "bar": {"color": color},
                    "bgcolor": "rgba(30,40,60,0.6)",
                    "borderwidth": 1,
                    "bordercolor": "rgba(255,255,255,0.1)",
                    "steps": [
                        {"range": [0, 25], "color": "rgba(239,68,68,0.2)"},
                        {"range": [25, 50], "color": "rgba(245,158,11,0.2)"},
                        {"range": [50, 75], "color": "rgba(59,130,246,0.2)"},
                        {"range": [75, 100], "color": "rgba(34,197,94,0.2)"},
                    ],
                    "threshold": {
                        "line": {"color": "#ffffff", "width": 2},
                        "thickness": 0.8,
                        "value": baseline,
                    },
                },
            ))
            fig.update_layout(
                height=220,
                paper_bgcolor=_PAPER_BG,
                plot_bgcolor=_PLOT_BG,
                font=dict(color=_FONT_COLOR, size=12),
                margin=dict(l=20, r=20, t=60, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

    # --- Tables per perspective ---
    st.markdown("---")
    st.markdown("##### Detalle por Perspectiva")

    for nombre, data, _, color in _BSC_PERSPECTIVES:
        with st.expander(f"{nombre}", expanded=True):
            tbl = pd.DataFrame(data)
            st.dataframe(
                tbl,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Vinculado a NCM": st.column_config.TextColumn("Vinculado a NCM", width="medium"),
                },
            )


# =============================================================================
# TAB 2: HOSHIN KANRI
# =============================================================================


def _render_hoshin_kanri() -> None:
    """Hoshin Kanri: visión, breakthroughs, Matriz X, catchball."""

    st.markdown("#### 🎯 Hoshin Kanri — Despliegue Estratégico")

    # --- Visión 3 años ---
    st.markdown("##### 🔭 Visión a 3 Años")
    st.markdown(
        f'<div style="background:rgba(59,130,246,0.1);border-left:4px solid #3b82f6;'
        f'padding:16px;border-radius:8px;margin-bottom:20px;">'
        f'<em style="color:{_FONT_COLOR};font-size:15px;">{_HOSHIN_VISION}</em></div>',
        unsafe_allow_html=True,
    )

    # --- Breakthrough Objectives ---
    st.markdown("##### 🚀 Objetivos Breakthrough (3 años)")
    cols = st.columns(3)
    for i, bt in enumerate(_BREAKTHROUGHS):
        with cols[i]:
            st.metric(
                label=bt["titulo"],
                value=bt["actual"],
                delta=bt["meta"],
            )
            st.caption(f"KPI: {bt['kpi']}")

    st.markdown("---")

    # --- Matriz X ---
    st.markdown("##### 🔗 Matriz X — Correlación Estratégica")
    st.caption("Intensidad: 0=Sin relación | 1=Contribuye | 2=Crítico")

    fig_matrix = go.Figure(data=go.Heatmap(
        z=_MATRIX_X,
        x=_ANNUAL_OBJECTIVES,
        y=[b["titulo"] for b in _BREAKTHROUGHS],
        colorscale=[
            [0, "rgba(30,40,60,0.8)"],
            [0.5, "rgba(59,130,246,0.6)"],
            [1, "rgba(34,197,94,0.9)"],
        ],
        zmin=0,
        zmax=2,
        text=_MATRIX_X,
        texttemplate="%{text}",
        textfont={"size": 16, "color": _FONT_COLOR},
        hovertemplate="Breakthrough: %{y}<br>Objetivo Anual: %{x}<br>Correlación: %{z}<extra></extra>",
        colorbar=dict(
            title=dict(text="Intensidad", font=dict(color=_FONT_COLOR)),
            tickfont=dict(color=_FONT_COLOR),
            tickvals=[0, 1, 2],
            ticktext=["Sin relación", "Contribuye", "Crítico"],
        ),
    ))

    fig_matrix.update_layout(
        height=300,
        xaxis=dict(tickangle=-30, tickfont=dict(size=11, color=_FONT_COLOR), side="bottom"),
        yaxis=dict(tickfont=dict(size=11, color=_FONT_COLOR)),
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_PLOT_BG,
        font=dict(color=_FONT_COLOR, size=12),
        margin=dict(l=10, r=10, t=30, b=100),
    )
    st.plotly_chart(fig_matrix, use_container_width=True)

    st.markdown("---")

    # --- Catchball Cascade ---
    st.markdown("##### 🏓 Cascada Catchball — Despliegue Organizacional")
    st.caption("Flujo de compromiso bidireccional desde Gerencia hasta Operarios")

    c1, c2, c3, c4 = st.columns(4)

    _cascade_levels = [
        (c1, "🏢 Gerencia General", "Definir política SGI\nAprobar recursos\nRevisión por dirección", "#22c55e"),
        (c2, "🏭 Jefe de Planta", "Desplegar objetivos\nAsignar responsables\nControlar avance", "#3b82f6"),
        (c3, "👷 Supervisores", "Implementar controles\nCapacitar equipos\nReportar desviaciones", "#f59e0b"),
        (c4, "🔧 Operarios", "Ejecutar procedimientos\nReportar incidentes\nParticipar en mejora", "#a855f7"),
    ]

    for col, titulo, tareas, color in _cascade_levels:
        with col:
            st.markdown(
                f'<div style="background:rgba(30,40,60,0.6);border:2px solid {color};'
                f'border-radius:12px;padding:16px;text-align:center;min-height:200px;">'
                f'<h4 style="color:{color};margin-bottom:12px;font-size:14px;">{titulo}</h4>'
                f'<p style="color:{_FONT_COLOR};font-size:12px;white-space:pre-line;">{tareas}</p>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        '<p style="text-align:center;color:#94a3b8;margin-top:10px;">'
        '← → Compromiso bidireccional (catchball) entre todos los niveles</p>',
        unsafe_allow_html=True,
    )


# =============================================================================
# TAB 3: FODA + MAPA ESTRATÉGICO
# =============================================================================


def _render_foda_mapa() -> None:
    """FODA 2x2 + Mapa Estratégico Sankey."""

    st.markdown("#### 🔍 Análisis FODA — CONPREM GRAU")

    # --- FODA Grid 2x2 ---
    col1, col2 = st.columns(2)

    with col1:
        _foda_card("💪 Fortalezas", _FORTALEZAS, "#22c55e", "rgba(34,197,94,0.08)")
    with col2:
        _foda_card("⚠️ Debilidades", _DEBILIDADES, "#ef4444", "rgba(239,68,68,0.08)")

    col3, col4 = st.columns(2)

    with col3:
        _foda_card("🌟 Oportunidades", _OPORTUNIDADES, "#3b82f6", "rgba(59,130,246,0.08)")
    with col4:
        _foda_card("🔥 Amenazas", _AMENAZAS, "#f97316", "rgba(249,115,22,0.08)")

    st.markdown("---")

    # --- Mapa Estratégico Sankey ---
    st.markdown("##### 🗺️ Mapa Estratégico — Flujo de Valor (BSC)")
    st.caption("Conexión causal bottom-up: Aprendizaje → Procesos → Clientes → Financiera")

    # Nodes: 4 per perspective = 16 total
    labels = [
        # Aprendizaje (0-3)
        "Competencia SGI", "Cultura reporte", "Auditoría interna", "Digitalización",
        # Procesos (4-7)
        "Cero NCMs", "Controles formalizados", "MP sin deterioro", "Emergencias preparadas",
        # Clientes (8-11)
        "Satisfacción ≥90%", "Certificación habilitante", "Confiabilidad entregas", "Trazabilidad",
        # Financiera (12-15)
        "Ingresos ISO", "Reducir costo no-calidad", "Evitar multas", "Reducir prima seguro",
    ]

    # Colors per perspective
    node_colors = (
        ["rgba(168,85,247,0.8)"] * 4 +   # Aprendizaje - purple
        ["rgba(245,158,11,0.8)"] * 4 +    # Procesos - amber
        ["rgba(59,130,246,0.8)"] * 4 +    # Clientes - blue
        ["rgba(34,197,94,0.8)"] * 4       # Financiera - green
    )

    # Links: Aprendizaje → Procesos → Clientes → Financiera
    sources = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11]
    targets = [4, 5, 4, 7, 5, 6, 4, 6, 8, 9, 9, 10, 10, 11, 8, 11, 12, 13, 12, 14, 13, 15, 14, 15]
    values = [3, 2, 2, 2, 3, 2, 2, 2, 3, 3, 2, 3, 2, 3, 2, 2, 3, 2, 3, 2, 2, 3, 2, 2]

    link_colors = []
    for s in sources:
        if s < 4:
            link_colors.append("rgba(168,85,247,0.2)")
        elif s < 8:
            link_colors.append("rgba(245,158,11,0.2)")
        elif s < 12:
            link_colors.append("rgba(59,130,246,0.2)")
        else:
            link_colors.append("rgba(34,197,94,0.2)")

    fig_sankey = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20,
            thickness=25,
            line=dict(color="rgba(255,255,255,0.2)", width=1),
            label=labels,
            color=node_colors,
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values,
            color=link_colors,
        ),
    )])

    fig_sankey.update_layout(
        title=dict(text="Cadena Causal Estratégica", font=dict(color=_FONT_COLOR, size=14)),
        height=500,
        **_LAYOUT_DEFAULTS,
    )
    st.plotly_chart(fig_sankey, use_container_width=True)

    # Legend
    st.markdown(
        '<div style="display:flex;gap:20px;justify-content:center;flex-wrap:wrap;">'
        '<span style="color:#a855f7;">● Aprendizaje</span>'
        '<span style="color:#f59e0b;">● Procesos</span>'
        '<span style="color:#3b82f6;">● Clientes</span>'
        '<span style="color:#22c55e;">● Financiera</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def _foda_card(titulo: str, items: list[str], border_color: str, bg_color: str) -> None:
    """Renderiza una tarjeta FODA con estilo."""
    bullets = "".join(f'<li style="margin-bottom:6px;color:{_FONT_COLOR};font-size:13px;">{item}</li>' for item in items)
    st.markdown(
        f'<div style="background:{bg_color};border:2px solid {border_color};'
        f'border-radius:12px;padding:18px;margin-bottom:12px;min-height:220px;">'
        f'<h4 style="color:{border_color};margin-bottom:12px;font-size:15px;">{titulo}</h4>'
        f'<ul style="padding-left:18px;margin:0;">{bullets}</ul>'
        f'</div>',
        unsafe_allow_html=True,
    )


# =============================================================================
# TAB 4: PLAN OdM + ROADMAP
# =============================================================================


def _render_plan_odm_roadmap(df: pd.DataFrame) -> None:
    """Plan OdM editable + Gantt 12 meses."""

    st.markdown("#### 📋 Plan de Oportunidades de Mejora (OdM)")

    # --- Key Metrics ---
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total OdMs", "10", delta="Identificadas")
    with m2:
        st.metric("NCMs Vinculadas", "15", delta="NCM-01 a NCM-15")
    with m3:
        st.metric("Plazo Máximo", "12 meses", delta="Certificación")
    with m4:
        st.metric("Inversión", "950 UF", delta="Presupuesto SGI")

    st.markdown("---")

    # --- Editable OdM Table ---
    st.markdown("##### ✏️ Tabla de Seguimiento OdM")
    st.caption("Edite Estado, Responsable y Plazo directamente en la tabla")

    state_key = "strategic_odm_plan"
    if state_key not in st.session_state:
        st.session_state[state_key] = pd.DataFrame(_ODM_DEFAULT)

    edited_df = st.data_editor(
        st.session_state[state_key],
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        column_config={
            "ID": st.column_config.TextColumn("ID", disabled=True, width="small"),
            "Descripción": st.column_config.TextColumn("Descripción", width="large"),
            "Zona": st.column_config.TextColumn("Zona", width="medium"),
            "Estado": st.column_config.SelectboxColumn(
                "Estado",
                options=["No iniciado", "En progreso", "Completado", "Bloqueado"],
                required=True,
                width="medium",
            ),
            "Responsable": st.column_config.TextColumn("Responsable", width="medium"),
            "Plazo": st.column_config.DateColumn("Plazo", width="small"),
        },
        key="strategic_odm_editor",
    )
    st.session_state[state_key] = edited_df

    st.markdown("---")

    # --- Roadmap Gantt 12 meses ---
    st.markdown("##### 🗺️ Roadmap Estratégico — 12 Meses")
    st.caption("Timeline integrado con hitos de BSC, Hoshin Kanri y FODA")

    today = date.today()
    gantt_data = []

    for milestone in _GANTT_MILESTONES:
        start = today + timedelta(days=milestone["Inicio"] * 30)
        end = start + timedelta(days=milestone["Duración"] * 30)
        gantt_data.append({
            "Hito": milestone["Hito"],
            "Inicio": start,
            "Fin": end,
            "Framework": milestone["Framework"],
        })

    gantt_df = pd.DataFrame(gantt_data)

    color_map = {
        "BSC": "#3b82f6",
        "Hoshin": "#22c55e",
        "FODA": "#f59e0b",
    }

    fig_gantt = px.timeline(
        gantt_df,
        x_start="Inicio",
        x_end="Fin",
        y="Hito",
        color="Framework",
        color_discrete_map=color_map,
        title="Plan Estratégico SGI — Línea de Tiempo Integrada",
    )

    fig_gantt.update_layout(
        height=500,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
            font=dict(color=_FONT_COLOR),
        ),
        xaxis_title="",
        yaxis_title="",
        xaxis=dict(gridcolor=_GRID_COLOR, tickfont=dict(color=_FONT_COLOR)),
        yaxis=dict(gridcolor=_GRID_COLOR, tickfont=dict(color=_FONT_COLOR, size=11), autorange="reversed"),
        paper_bgcolor=_PAPER_BG,
        plot_bgcolor=_PLOT_BG,
        font=dict(color=_FONT_COLOR, size=12),
        margin=dict(l=10, r=10, t=50, b=80),
    )

    fig_gantt.update_traces(marker_line_width=0, opacity=0.85)
    st.plotly_chart(fig_gantt, use_container_width=True)

    # --- Resumen final ---
    st.markdown(
        '<div style="background:rgba(34,197,94,0.08);border:1px solid #22c55e;'
        'border-radius:10px;padding:16px;margin-top:16px;">'
        '<p style="color:#22c55e;font-weight:600;margin-bottom:8px;">📌 Resumen Ejecutivo del Plan</p>'
        '<ul style="color:#e2e8f0;font-size:13px;margin:0;padding-left:18px;">'
        '<li>15 No Conformidades Mayores a cerrar en 6 meses</li>'
        '<li>10 Oportunidades de Mejora priorizadas</li>'
        '<li>Certificación triple norma ISO proyectada Q1 2027</li>'
        '<li>ROI estimado: +$2.000M CLP en cartera habilitada</li>'
        '<li>Inversión total: 950 UF (implementación + certificación)</li>'
        '</ul></div>',
        unsafe_allow_html=True,
    )

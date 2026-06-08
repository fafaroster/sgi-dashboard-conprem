# Implementation Plan: SGI Audit Dashboard

## Overview

Implement a Streamlit-based interactive visualization dashboard that transforms CONPREM GRAU's SGI audit Markdown report into strategic decision-making tools. The architecture follows a modular pipeline: Markdown → Parser → DataFrame → Metrics Engine → Streamlit Visualizations. Technology stack: Python 3.11+, Streamlit, Pandas, Plotly, Hypothesis.

## Tasks

- [x] 1. Project setup and core data model
  - [x] 1.1 Initialize Python project structure and dependencies
    - Create project directory structure: `src/`, `src/dashboard/`, `tests/`, `tests/property/`, `tests/unit/`, `tests/integration/`
    - Create `pyproject.toml` with dependencies: streamlit>=1.28, pandas>=2.0, plotly>=5.18, hypothesis>=6.90, pytest>=7.4, pytest-cov
    - Create `requirements.txt` with pinned versions
    - Create `src/__init__.py`, `src/dashboard/__init__.py`, `tests/__init__.py`
    - _Requirements: 14.1 (application infrastructure)_

  - [x] 1.2 Implement core data model with Finding dataclass and enums
    - Create `src/models.py` with: `FindingType` enum (NCM, NCm, ODM, OBS), `CorrectiveActionStatus` enum (open, in_progress, completed, verified, closed), `PROCESS_ZONES` list (10 zones), `STANDARDS` list (3 ISO norms), `FINDING_WEIGHTS` dict, and `Finding` dataclass with all required and optional fields
    - Implement field validation in `Finding.__post_init__`: finding_id pattern `(NCM|NCm|ODM|OBS)-\d{2}`, description max 2000 chars, evidence max 5000 chars, clause_ref pattern `\d+\.\d+(\.\d+)?`, responsible_party max 150 chars, estimated_mitigation_cost range 0.01–999,999,999.99, deadline ISO 8601 validation
    - Create `ValidationResult` dataclass with `is_valid`, `errors`, `line_number`, `section_heading`
    - _Requirements: 1.1, 16.1, 16.3, 16.4_

  - [ ]* 1.3 Write unit tests for data model validation
    - Test valid Finding creation with all fields populated
    - Test Finding with optional fields as None
    - Test invalid finding_id format raises error
    - Test description exceeding 2000 chars raises error
    - Test invalid deadline format raises error
    - Test estimated_mitigation_cost out of range raises error
    - Test invalid corrective_action_status value raises error
    - _Requirements: 16.1, 16.3, 16.4_

- [x] 2. Parser module
  - [x] 2.1 Implement `parse_markdown_report` function
    - Create `src/parser.py` with `ParserError` exception class (line_number, field_name, expected_format attributes)
    - Implement `parse_markdown_report(file_path: str) -> pd.DataFrame`: read file, split by finding-type section headers, call `extract_section_findings` per section, expand multi-norm findings into one row per standard, return DataFrame with schema: finding_id, finding_type, description, standards, process_zone, clause_ref, evidence, is_transversal, responsible_party, deadline, estimated_mitigation_cost, corrective_action_status
    - Handle HTS findings: set `is_transversal=True`, associate with all explicitly listed process zones
    - _Requirements: 1.1, 1.2, 1.4, 1.5_

  - [x] 2.2 Implement `extract_section_findings` and `validate_finding_structure`
    - Implement `extract_section_findings(section_text: str, finding_type: str) -> list[Finding]`: split by finding ID regex, extract fields via regex patterns, validate each finding
    - Implement `validate_finding_structure(finding: Finding) -> ValidationResult`: check required fields (finding_id, finding_type, description, standards non-empty, process_zone), format rules for ID pattern, clause_ref pattern, description/evidence length limits
    - On validation failure, return `ValidationResult(is_valid=False, errors=[...], line_number=..., section_heading=...)`
    - Handle absent clause_ref or evidence gracefully (set to None, continue parsing)
    - _Requirements: 1.1, 1.3, 1.6_

  - [ ]* 2.3 Write property test: Finding ID Preservation (Property 9)
    - **Property 9: Finding ID Preservation**
    - **Validates: Requirements 1.4**
    - Use Hypothesis to generate valid Markdown with finding IDs matching `(NCM|NCm|ODM|OBS)-\d{2}` and verify parsed DataFrame preserves IDs character-for-character

  - [ ]* 2.4 Write property test: Multi-Standard Finding Counting (Property 8)
    - **Property 8: Multi-Standard Finding Counting Consistency**
    - **Validates: Requirements 1.2, 3.2**
    - Use Hypothesis to generate findings affecting 1–3 standards, verify standard-level count = N rows per finding, zone-level deduplication counts each finding once

  - [ ]* 2.5 Write unit tests for parser error handling
    - Test malformed file missing finding_id → ParserError with line number
    - Test file missing process_zone field → specific error message
    - Test valid file with absent clause_ref → null in DataFrame, no error
    - Test HTS finding detection and multi-zone association
    - Test multi-norm finding produces correct row expansion
    - _Requirements: 1.3, 1.5, 1.6_

- [x] 3. Pretty_Printer module
  - [x] 3.1 Implement `format_to_markdown` function
    - Create `src/pretty_printer.py` with `SerializationError` exception class
    - Implement `format_to_markdown(df: pd.DataFrame) -> str`: validate required columns exist (finding_id, finding_type, process_zone), check no null values in mandatory fields, build pipe-delimited Markdown table with column order (ID, Type, Standard(s), Process Zone, Clause, Description, Evidence), include header separator row
    - On validation failure: raise `SerializationError` specifying affected rows and columns without producing partial output
    - Handle optional fields with null/empty values: serialize as empty cells preserving schema structure
    - _Requirements: 2.1, 2.4, 2.5_

  - [x] 3.2 Implement `validate_roundtrip` and JSON serialization
    - Implement `validate_roundtrip(original_md: str, df: pd.DataFrame) -> bool`: apply format_to_markdown then parse_markdown_report, compare column names, row count, and cell-by-cell string equality after stripping whitespace
    - Implement `serialize_to_json(df: pd.DataFrame) -> str`: produce JSON array with snake_case field names, ISO 8601 dates, JSON null for empty optional fields
    - _Requirements: 2.2, 2.3, 2.5_

  - [ ]* 3.3 Write property test: Round-Trip Idempotence (Property 1)
    - **Property 1: Parser-Printer Round-Trip Idempotence**
    - **Validates: Requirements 2.1, 2.2**
    - Use Hypothesis to generate valid Markdown reports (1–50 findings), verify parse→format→parse produces identical DataFrame (column names, row count, cell equality)

  - [ ]* 3.4 Write property test: Optional Field Schema Preservation (Property 11)
    - **Property 11: Optional Field Schema Preservation**
    - **Validates: Requirements 2.5, 16.1, 16.2**
    - Use Hypothesis to generate findings with random null optionals, verify JSON includes fields with null values, Markdown includes empty cells

- [x] 4. Checkpoint - Ensure core pipeline tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Metrics Engine
  - [x] 5.1 Implement `calculate_risk_load_score` function
    - Create `src/metrics.py` with `WEIGHTS` dict constant
    - Implement `calculate_risk_load_score(df: pd.DataFrame, group_by: str = "process_zone") -> pd.Series`: compute weighted sum per group using formula NCM×5 + NCm×2 + ODM×1 + OBS×0.5, round to 1 decimal place
    - Handle zone-level grouping: deduplicate by finding_id before scoring (multi-standard findings counted once)
    - Handle standard-level grouping: count each row (multi-standard findings counted per standard)
    - Return 0.0 for groups with zero findings
    - _Requirements: 3.1, 3.2, 3.5_

  - [x] 5.2 Implement `calculate_criticality_rate` function
    - Implement `calculate_criticality_rate(df: pd.DataFrame) -> dict[str, float]`: compute NCM_count / total_count per standard, return as percentage 0.0–100.0 with 1 decimal place
    - Handle zero-division: return 0.0 when standard has zero findings
    - _Requirements: 6.1, 6.2, 6.4_

  - [x] 5.3 Implement `calculate_maturity_index` function
    - Implement `calculate_maturity_index(df: pd.DataFrame) -> dict[str, float]`: compute 100 - (Risk_Load_Score / (unique_finding_count × 5)) × 100 per zone, 1 decimal place
    - Handle zero-finding zones: return 100.0
    - Deduplicate by finding_id for unique count
    - _Requirements: 7.1, 7.2, 7.4_

  - [x] 5.4 Implement `calculate_pareto_threshold` function
    - Implement `calculate_pareto_threshold(scores: pd.Series, threshold: float = 0.8) -> tuple[list, list, pd.Series]`: sort descending, compute cumulative percentage, find 80% boundary, split into critical and remaining categories
    - Handle empty/zero-total input gracefully
    - _Requirements: 4.1, 4.2_

  - [ ]* 5.5 Write property test: Risk_Load_Score Monotonicity (Property 2)
    - **Property 2: Risk_Load_Score Monotonicity (NCM Addition)**
    - **Validates: Requirements 3.1, 3.5**
    - Use Hypothesis to generate random zones with findings, add one finding of each type, verify score increases by exact weight

  - [ ]* 5.6 Write property test: Maturity_Index Bounds (Property 3)
    - **Property 3: Maturity_Index Bounds**
    - **Validates: Requirements 7.1, 7.2, 7.4**
    - Use Hypothesis to generate random finding distributions, verify all Maturity_Index values in [0.0, 100.0], zero-finding zones = 100.0

  - [ ]* 5.7 Write property test: Pareto Cumulative Completeness (Property 4)
    - **Property 4: Pareto Cumulative Completeness**
    - **Validates: Requirements 4.1, 4.2**
    - Use Hypothesis to generate random score distributions, verify cumulative line ends at 100%, sum of bar percentages = 100%

  - [ ]* 5.8 Write property test: Criticality_Rate Bounds (Property 7)
    - **Property 7: Criticality_Rate Domain Bounds**
    - **Validates: Requirements 6.1, 6.4, 6.5**
    - Use Hypothesis to generate random standard/finding distributions, verify all rates in [0.0, 100.0], zero-finding standards = 0.0

  - [ ]* 5.9 Write property test: Compliance Health Bounds (Property 10)
    - **Property 10: Compliance Health Bounds and Formula Consistency**
    - **Validates: Requirements 8.3, 8.5**
    - Use Hypothesis to generate random datasets (0–200 findings), verify health in [0.0, 100.0], empty dataset = 100.0

  - [ ]* 5.10 Write property test: Pareto Ordering Invariant (Property 14)
    - **Property 14: Pareto Ordering Invariant**
    - **Validates: Requirements 4.1, 4.5**
    - Use Hypothesis to generate non-empty datasets, verify bars in non-increasing order, cumulative line is monotonically non-decreasing

  - [ ]* 5.11 Write property test: Heatmap Cell Score Accuracy (Property 15)
    - **Property 15: Heatmap Cell Score Accuracy**
    - **Validates: Requirements 5.1, 5.2**
    - Use Hypothesis to generate random findings across zones/standards, verify each (zone, standard) cell equals computed Risk_Load_Score for that subset

- [x] 6. Checkpoint - Ensure metrics engine tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Dashboard UI - Filters and Executive Summary
  - [x] 7.1 Implement filter sidebar with `render_filters_sidebar` and `apply_filters`
    - Create `src/dashboard/filters.py` with `FilterState` dataclass
    - Implement `render_filters_sidebar() -> FilterState`: Streamlit sidebar with st.multiselect for standards (default all 3), finding_types (default all 4), process_zones (default all 10), and st.text_input for search
    - Implement `apply_filters(df, filters) -> pd.DataFrame`: AND between categories, OR within categories, case-insensitive substring search on descriptions/IDs (min 2 chars)
    - Display active filter state as persistent summary area
    - Handle zero-match case: return empty DataFrame (UI will show empty-state message)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [ ]* 7.2 Write property test: Filter Idempotence (Property 5)
    - **Property 5: Filter Idempotence**
    - **Validates: Requirements 9.2, 9.3, 9.5**
    - Use Hypothesis to generate random DataFrames and FilterStates, verify apply_filters(apply_filters(df, f), f) == apply_filters(df, f)

  - [ ]* 7.3 Write property test: Filter AND/OR Logic (Property 6)
    - **Property 6: Filter Logic Correctness (AND/OR)**
    - **Validates: Requirements 9.3**
    - Use Hypothesis to generate complex multi-filter combinations, verify correct AND/OR semantics

  - [x] 7.4 Implement Executive Summary panel with `render_executive_summary`
    - Create `src/dashboard/executive_summary.py`
    - Implement `render_executive_summary(df, metrics)`: display total finding count, total Risk_Load_Score (1 decimal), overall compliance health % (formula: (1 - actual/theoretical_max) × 100), count per finding type (NCM, NCm, ODM, OBS) using st.metric in columns
    - Show HTS alert with red background and warning icon using st.error when transversal finding present
    - Handle empty dataset: all zeros, compliance health = 100.0%
    - Place as first visible section occupying full viewport width
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 8. Dashboard UI - Pareto Charts
  - [x] 8.1 Implement primary Pareto chart (process zones by Risk_Load_Score)
    - Create `src/dashboard/pareto.py`
    - Implement `render_pareto_chart(df, metrics, filters)`: Plotly Figure with vertical bars (descending Risk_Load_Score), cumulative % line on secondary y-axis (0–100%), 80% threshold highlight with color boundary between critical/remaining zones
    - Apply dark theme styling, SVG rendering
    - Handle zero-match filter: display empty-state message
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 8.2 Implement secondary Pareto chart (clause references by finding count)
    - Add secondary chart ordering ISO clause references by descending finding count with cumulative % line and 80% threshold highlight
    - Consistent visual styling with primary chart
    - _Requirements: 4.5_

- [x] 9. Dashboard UI - Risk Heatmap
  - [x] 9.1 Implement Risk Heatmap with `render_risk_heatmap`
    - Create `src/dashboard/heatmap.py`
    - Implement `render_risk_heatmap(df, filters)`: Plotly heatmap with process zones (10) on y-axis, standards (3) on x-axis, sequential color scale (Plasma), numeric annotations in cells
    - Zero-finding cells: neutral gray color distinct from scored scale, value = 0
    - Hover tooltip: Risk_Load_Score + per-type breakdown (NCM, NCm, ODM, OBS counts)
    - Recalculate on filter application within 1 second
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 10. Dashboard UI - Maturity Radar Chart
  - [x] 10.1 Implement Maturity Radar with `render_maturity_radar`
    - Create `src/dashboard/radar.py`
    - Implement `render_maturity_radar(df, metrics)`: Plotly Scatterpolar with one axis per process zone (10 axes), scale 0–100, filled area, zone name labels
    - Recalculate on filter change within 1 second
    - Dark mode compatible colors
    - _Requirements: 7.3, 7.5_

- [x] 11. Dashboard UI - Findings Table with Drill-Down
  - [x] 11.1 Implement interactive findings table with `render_findings_table`
    - Create `src/dashboard/findings_table.py`
    - Implement `render_findings_table(df, filters)`: display columns ID, Type, Standard(s), Process Zone, Clause, Description (truncated at 120 chars with "...")
    - Support sorting by any column (default: ID ascending)
    - Case-insensitive substring search (min 2 chars trigger)
    - Row click → detail view (st.expander) showing full description, evidence, affected clauses, with return control
    - Empty-state message when no matches
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [ ]* 11.2 Write property test: Description Truncation Invariant (Property 13)
    - **Property 13: Description Truncation Invariant**
    - **Validates: Requirements 10.1**
    - Use Hypothesis to generate strings of varying lengths, verify truncation logic: full text if ≤120 chars, first 120 + "..." if >120 chars

- [x] 12. Dashboard UI - HTS Systemic Finding Panel
  - [x] 12.1 Implement HTS panel with `render_hts_panel`
    - Create `src/dashboard/hts_panel.py`
    - Implement `render_hts_panel(df)`: display finding description, affected zones, affected standards, systemic explanation with distinct border/background color (custom CSS via st.markdown)
    - Show process-zone impact diagram indicating affected vs unaffected zones
    - Conditional rendering: hide panel entirely when HTS absent from dataset
    - Handle incomplete HTS metadata: show available fields + "Data not available" placeholders
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 13. Dashboard UI - Corrective Action Timeline
  - [x] 13.1 Implement Gantt-style timeline with `render_timeline`
    - Create `src/dashboard/timeline.py`
    - Implement `render_timeline(df)`: Plotly timeline (px.timeline) showing up to 50 corrective actions with start dates, deadlines, status
    - Color coding: gray=not started, blue=in_progress, green=completed, red=overdue (current_date > deadline AND status ≠ completed)
    - Missing fields → "Pending Assignment" placeholder
    - Pagination/scrolling for >50 actions
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

- [x] 14. Dashboard UI - Dark Mode Theming and Layout
  - [x] 14.1 Implement dark mode theme and modular layout
    - Create `src/dashboard/theme.py` with Streamlit config (`.streamlit/config.toml`) for dark theme default
    - Configure Plotly template with dark background, high-contrast text (luminance ≥0.75 foreground, ≤0.05 background)
    - Ensure all charts use SVG/vector rendering (no pixelation at 50%–400% zoom)
    - Implement modular collapsible layout: each visualization section independently scrollable and collapsible via st.expander, all expanded by default
    - Collapse/expand transitions within 300ms, state preserved for session duration
    - Verify minimum 4.5:1 contrast ratio for normal text, 3:1 for large text and UI components
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

- [x] 15. Checkpoint - Ensure all dashboard components render correctly
  - Ensure all tests pass, ask the user if questions arise.

- [x] 16. Export module
  - [x] 16.1 Implement CSV and image export functionality
    - Create `src/export.py` with `ExportError` exception class
    - Implement CSV export: generate file with all filtered findings + metadata columns, file named with export date and active filter summary, include active filter config as header section
    - Implement visualization export: generate PNG (min 1920×1080) or SVG of all displayed charts, embed active filter metadata
    - Handle zero-findings case: display message "no data available to export", do not generate file
    - Handle export failures: display error reason, do not produce partial/corrupted files
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

- [x] 17. Application entry point and wiring
  - [x] 17.1 Create main Streamlit application entry point
    - Create `src/app.py` as the main entry point: configure page settings, initialize `st.cache_data` for parsed DataFrame, wire together all dashboard components in correct order (executive summary first, then charts, table, panels)
    - Implement dataset size validation: reject >200 findings with error message
    - Ensure initial load completes within 3 seconds for 37 findings
    - Ensure filter interactions re-render within 1 second without re-parsing source file
    - Display progress indicator for datasets >200 findings during recalculation
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_

- [ ] 18. Property-based tests - Date Validation
  - [ ]* 18.1 Write property test: Date Validation Correctness (Property 12)
    - **Property 12: Date Validation Correctness**
    - **Validates: Requirements 16.3**
    - Use Hypothesis to generate valid ISO 8601 dates and invalid strings, verify validator accepts/rejects correctly

- [ ] 19. Integration and performance tests
  - [ ]* 19.1 Write integration tests for full pipeline
    - Test full pipeline: file → parse → metrics → render for default dataset (37 findings)
    - Test Streamlit app launch with default dataset completes in <3 seconds
    - Test export file generation and format validation (CSV structure, PNG/SVG resolution)
    - _Requirements: 14.1, 15.1, 15.2_

  - [ ]* 19.2 Write performance tests
    - Test parse + render 37 findings < 3 seconds
    - Test parse + render 200 findings < 3 seconds
    - Test filter re-render < 1 second
    - Test heatmap filter update < 1 second
    - _Requirements: 14.1, 14.2, 14.3, 5.5_

- [x] 20. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (Properties 1–15)
- Unit tests validate specific examples and edge cases
- Python 3.11+ required for modern dataclass features and type annotations
- All Hypothesis property tests must run minimum 100 iterations
- Streamlit caching (`st.cache_data`) is critical for meeting performance requirements

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2"] },
    { "id": 2, "tasks": ["1.3", "2.1"] },
    { "id": 3, "tasks": ["2.2"] },
    { "id": 4, "tasks": ["2.3", "2.4", "2.5", "3.1"] },
    { "id": 5, "tasks": ["3.2"] },
    { "id": 6, "tasks": ["3.3", "3.4", "5.1"] },
    { "id": 7, "tasks": ["5.2", "5.3", "5.4"] },
    { "id": 8, "tasks": ["5.5", "5.6", "5.7", "5.8", "5.9", "5.10", "5.11"] },
    { "id": 9, "tasks": ["7.1"] },
    { "id": 10, "tasks": ["7.2", "7.3", "7.4"] },
    { "id": 11, "tasks": ["8.1", "9.1", "10.1", "11.1", "12.1", "13.1"] },
    { "id": 12, "tasks": ["8.2", "11.2"] },
    { "id": 13, "tasks": ["14.1"] },
    { "id": 14, "tasks": ["16.1"] },
    { "id": 15, "tasks": ["17.1"] },
    { "id": 16, "tasks": ["18.1", "19.1", "19.2"] }
  ]
}
```

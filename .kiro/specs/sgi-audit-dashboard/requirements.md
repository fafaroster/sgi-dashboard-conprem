# Requirements Document

## Introduction

This document defines the requirements for the SGI Audit Dashboard — an interactive, high-performance visualization tool that transforms the CONPREM GRAU SGI audit findings report (based on ISO 9001:2015, ISO 14001:2015, and ISO 45001:2018) into a strategic decision-making dashboard. The dashboard enables management and quality teams to identify bottlenecks, prioritize corrective actions, and monitor SGI maturity across operational processes in the prestressed concrete sleeper manufacturing facility.

## Glossary

- **Dashboard**: The Streamlit-based web application that displays audit findings interactively
- **Parser**: The module responsible for reading and transforming the Markdown audit report into structured data
- **Pretty_Printer**: The module responsible for serializing structured finding data back into formatted Markdown
- **SGI**: Sistema de Gestión Integrado (Integrated Management System) covering Quality, Environment, and Occupational Safety & Health
- **NCM**: No Conformidad Mayor (Major Non-Conformity) — weighted at 5 points in risk scoring
- **NCm**: No Conformidad Menor (Minor Non-Conformity) — weighted at 2 points in risk scoring
- **ODM**: Oportunidad de Mejora (Opportunity for Improvement) — weighted at 1 point in risk scoring
- **OBS**: Observación (Observation) — weighted at 0.5 points in risk scoring
- **HTS**: Hallazgo Transversal Sistémico (Systemic Transversal Finding) — a finding that affects the entire management system across multiple processes
- **Finding**: A single audit result classified as NCM, NCm, ODM, or OBS with associated metadata
- **Risk_Load_Score**: The weighted sum of findings calculated as (NCM×5 + NCm×2 + ODM×1 + OBS×0.5)
- **Criticality_Rate**: The ratio of major findings to total findings per standard
- **Maturity_Index**: A composite score representing the SGI implementation level per process or zone
- **Process_Zone**: An operational area of CONPREM GRAU (e.g., Logistics, Storage Yard, Manufacturing/Prestressing, Lab, Boilers, Aggregates, Steel Storage, Chemical Storage, Document Management, General/Transversal)
- **Standard**: One of the three ISO norms — ISO 9001:2015, ISO 14001:2015, or ISO 45001:2018
- **Finding_Type**: The classification category of a finding (NCM, NCm, ODM, OBS)
- **Pareto_Chart**: A bar chart ordered by frequency/impact showing cumulative percentage, used to identify the 80/20 distribution
- **Risk_Heatmap**: A matrix visualization showing risk intensity across process zones and standards
- **Data_Pipeline**: The processing chain from raw Markdown input through parsing, normalization, and transformation to dashboard-ready data
- **DataFrame**: A Pandas tabular data structure used internally to store and manipulate findings data

## Requirements

### Requirement 1: Markdown Report Parsing

**User Story:** As a quality engineer, I want the system to automatically parse the SGI audit Markdown report, so that findings data is available for analysis without manual data entry.

#### Acceptance Criteria

1. WHEN a Markdown file containing at least one finding section with a valid finding ID prefix (NCM-, NCm-, ODM-, or OBS-) is provided, THE Parser SHALL extract all findings into a structured DataFrame containing one row per finding with columns: finding ID (string), finding type (one of NCM, NCm, ODM, OBS), description (string, max 2000 characters), affected standard(s) (one or more of ISO 9001:2015, ISO 14001:2015, ISO 45001:2018), process zone (string matching a value from the defined Process_Zone list), clause reference (string in format "X.Y.Z"), and evidence text (string, max 5000 characters)
2. WHEN the Markdown file contains multi-norm findings affecting two or more standards simultaneously, THE Parser SHALL produce one row per affected standard for that finding, duplicating the finding data and varying only the standard column, so that standard-level aggregation counts each association independently
3. IF the Markdown file is malformed or missing one or more required fields (finding ID, finding type, description, affected standard, or process zone), THEN THE Parser SHALL return an error message specifying the line number or section heading where the failure occurred, the name of the missing or malformed field, and a description of the expected format
4. THE Parser SHALL preserve the original finding identifiers (NCM-01 through NCM-15, NCm-01 through NCm-07, ODM-01 through ODM-10, OBS-01 through OBS-05) without modification
5. WHEN a finding is classified as HTS (Hallazgo Transversal Sistémico), THE Parser SHALL flag the finding with a boolean transversal indicator set to true and associate it with every process zone explicitly listed in the finding's description or affected-zones field in the source document
6. IF a finding's clause reference or evidence text field is absent or empty in the source document, THEN THE Parser SHALL set the corresponding DataFrame column to null for that finding and continue parsing without error

### Requirement 2: Structured Data Serialization

**User Story:** As a developer, I want to serialize and deserialize findings data between formats, so that the data pipeline supports reproducible transformations.

#### Acceptance Criteria

1. THE Pretty_Printer SHALL format DataFrame findings back into valid Markdown tables preserving: the original column order (ID, Type, Standard(s), Process Zone, Clause, Description, Evidence), pipe-delimited table syntax, and header separator rows, such that the output is parseable by the Parser without error
2. THE Data_Pipeline SHALL ensure that for any valid DataFrame containing up to 200 findings, applying Parser then Pretty_Printer then Parser produces a DataFrame with identical column names, identical row count, and cell-by-cell string equality to the original DataFrame (round-trip property)
3. WHEN exporting findings data, THE Data_Pipeline SHALL produce a JSON array where each finding is a flat object with snake_case field names matching the DataFrame column names, all date values formatted as ISO 8601 (YYYY-MM-DD), and null represented as JSON null for empty optional fields
4. IF the Pretty_Printer receives a DataFrame with missing required columns or null values in mandatory fields (ID, Type, Process Zone), THEN THE Pretty_Printer SHALL return an error message indicating which rows and columns failed validation without producing partial output
5. WHEN serializing findings that contain optional fields (responsible_party, deadline, estimated_mitigation_cost, corrective_action_status) with null or empty values, THE Data_Pipeline SHALL include those fields in the output with null values in JSON and empty cells in Markdown, preserving the complete schema structure

### Requirement 3: Risk Load Scoring

**User Story:** As a plant manager, I want to see a weighted risk score for each process zone, so that I can allocate resources to the highest-risk areas.

#### Acceptance Criteria

1. THE Dashboard SHALL calculate Risk_Load_Score for each process zone using the formula: (count of NCM × 5) + (count of NCm × 2) + (count of ODM × 1) + (count of OBS × 0.5), displaying the result with exactly one decimal place
2. WHEN a finding affects multiple standards, THE Dashboard SHALL count the finding once per standard for standard-level scoring and once total for process-zone-level scoring
3. THE Dashboard SHALL display each process zone's Risk_Load_Score in the executive summary section, sorted from highest to lowest score
4. WHEN a new finding dataset is loaded, THE Dashboard SHALL recalculate all Risk_Load_Scores within 2 seconds for datasets containing up to 200 findings
5. IF a process zone contains zero findings, THEN THE Dashboard SHALL display a Risk_Load_Score of 0.0 for that zone
6. IF the loaded dataset contains more than 200 findings, THEN THE Dashboard SHALL display a progress indicator during recalculation and complete the operation within 10 seconds

### Requirement 4: Pareto Analysis

**User Story:** As an industrial engineer, I want a Pareto chart that identifies the 80/20 distribution of findings by process zone, so that I can prioritize SGI improvement efforts on the critical few.

#### Acceptance Criteria

1. THE Dashboard SHALL display a Pareto_Chart ordering process zones by descending Risk_Load_Score, rendered as vertical bars with a cumulative percentage line overlay scaled from 0% to 100% on a secondary y-axis
2. THE Dashboard SHALL visually separate the process zones that accumulate up to 80% of the total Risk_Load_Score from the remaining zones using a differentiable color or shading boundary between the two groups
3. WHEN the user applies a filter by standard or finding type, THE Pareto_Chart SHALL recalculate and redraw using only the filtered subset of findings, preserving descending order and cumulative line
4. IF the active filters result in zero matching findings, THEN THE Dashboard SHALL display the Pareto_Chart area with an empty-state message indicating no findings match the current filter criteria
5. THE Dashboard SHALL provide a secondary Pareto_Chart ordering ISO clause references by descending finding count, with a cumulative percentage line overlay and an 80% threshold highlight consistent with the primary Pareto_Chart

### Requirement 5: Risk Heatmap

**User Story:** As a quality manager, I want a risk heatmap showing the intersection of process zones and standards, so that I can visualize where systemic weaknesses concentrate.

#### Acceptance Criteria

1. THE Dashboard SHALL display a Risk_Heatmap with process zones (Logistics, Storage Yard, Manufacturing/Prestressing, Lab, Boilers, Aggregates, Steel Storage, Chemical Storage, Document Management, General/Transversal) on one axis and standards (ISO 9001, ISO 14001, ISO 45001) on the other axis
2. THE Risk_Heatmap SHALL use a sequential color scale where minimum intensity corresponds to a Risk_Load_Score of zero and maximum intensity corresponds to the highest Risk_Load_Score present in the current dataset, and SHALL display the numeric Risk_Load_Score value within each cell
3. WHEN a cell in the Risk_Heatmap contains zero findings, THE Dashboard SHALL display the cell with a neutral color visually distinct from the scored color scale and a value of zero
4. WHEN the user hovers over a Risk_Heatmap cell, THE Dashboard SHALL display a tooltip showing the cell's Risk_Load_Score and the finding count breakdown by type (NCM, NCm, ODM, OBS) for that cell
5. WHEN the user applies a global filter by standard, finding type, or process zone, THE Risk_Heatmap SHALL recalculate cell values and redraw using only the filtered subset of findings within 1 second

### Requirement 6: Criticality Rate per Standard

**User Story:** As a management representative, I want to see the criticality rate for each ISO standard, so that I can report compliance posture to top management.

#### Acceptance Criteria

1. THE Dashboard SHALL calculate Criticality_Rate per standard as: (count of NCM for that standard) / (total findings for that standard), expressed as a value between 0.0% and 100.0%
2. THE Dashboard SHALL display Criticality_Rate as a percentage with one decimal place precision (e.g., "33.3%")
3. THE Dashboard SHALL display a comparative bar chart showing Criticality_Rate for each of the three standards (ISO 9001:2015, ISO 14001:2015, ISO 45001:2018) side by side
4. IF a standard has zero total findings in the current dataset, THEN THE Dashboard SHALL display a Criticality_Rate of 0.0% for that standard instead of performing the division
5. WHEN the user applies filters that result in all findings for a standard being excluded, THE Dashboard SHALL display a Criticality_Rate of 0.0% for that standard

### Requirement 7: SGI Maturity Index

**User Story:** As a continuous improvement specialist, I want an SGI maturity index per process zone, so that I can benchmark process performance and track improvement over time.

#### Acceptance Criteria

1. THE Dashboard SHALL calculate Maturity_Index per process zone as: 100 − ((Risk_Load_Score for zone / maximum possible Risk_Load_Score for zone) × 100), where maximum possible score assumes all findings in that zone are NCM (i.e., finding count × 5)
2. THE Dashboard SHALL display Maturity_Index values on a scale of 0 to 100 with one decimal place precision, where 100 represents zero findings
3. THE Dashboard SHALL render a radar chart comparing Maturity_Index across all process zones, with each axis labeled by zone name and scaled from 0 to 100
4. WHEN a process zone has no findings, THE Dashboard SHALL assign a Maturity_Index of 100.0 to that zone
5. WHEN the user applies global filters, THE Dashboard SHALL recalculate the Maturity_Index for each zone using only the filtered subset and redraw the radar chart within 1 second

### Requirement 8: Executive Summary Panel

**User Story:** As a plant director, I want an executive summary with key metrics at a glance, so that I can assess overall SGI health in under 10 seconds.

#### Acceptance Criteria

1. THE Dashboard SHALL display an executive summary panel containing: total finding count, total Risk_Load_Score (one decimal place), overall compliance health percentage (one decimal place), and count per finding type (NCM, NCm, ODM, OBS)
2. THE Dashboard SHALL display the executive summary panel as the first visible section upon application load, occupying the full viewport width above all other dashboard sections
3. THE Dashboard SHALL calculate overall compliance health as: (1 − (actual Risk_Load_Score / theoretical maximum Risk_Load_Score)) × 100, where theoretical maximum equals total finding count × 5
4. WHEN the dataset contains a systemic transversal finding (HTS), THE Dashboard SHALL display a prominent alert indicator with a red background and warning icon in the executive summary, with text identifying it as a systemic finding
5. IF the dataset is empty or contains zero findings, THEN THE Dashboard SHALL display the executive summary with all values at zero and compliance health at 100.0%

### Requirement 9: Interactive Filters

**User Story:** As an analyst, I want to filter findings by standard, finding type, and process zone, so that I can focus my analysis on specific segments of the audit results.

#### Acceptance Criteria

1. THE Dashboard SHALL provide filter controls for: standard (ISO 9001, ISO 14001, ISO 45001), finding type (NCM, NCm, ODM, OBS), and process zone (Logistics, Storage Yard, Manufacturing/Prestressing, Lab, Boilers, Aggregates, Steel Storage, Chemical Storage, Document Management, General/Transversal), with all filters set to include all values by default on application load
2. WHEN the user selects one or more filter values, THE Dashboard SHALL update all visualizations and metrics to reflect only the filtered subset within 1 second, where a multi-standard finding is included if any of its associated standards matches the selected standard filter
3. THE Dashboard SHALL support simultaneous multi-filter combinations (e.g., ISO 9001 + NCM + Manufacturing zone) applying AND logic between filter categories and OR logic within a single filter category
4. THE Dashboard SHALL display the active filter state in a persistent summary area showing each selected filter value as a labeled indicator that remains visible regardless of scroll position
5. WHEN all filters are cleared, THE Dashboard SHALL restore all visualizations to show the complete dataset within 1 second
6. IF the active filter combination matches zero findings, THEN THE Dashboard SHALL display an empty-state message indicating that no findings match the current filters and SHALL retain the filter controls in their current selection to allow the user to modify the criteria

### Requirement 10: Interactive Findings Table

**User Story:** As an auditor, I want a searchable and sortable findings table with drill-down capability, so that I can inspect individual finding details without switching tools.

#### Acceptance Criteria

1. THE Dashboard SHALL display a findings table with columns: ID, Type, Standard(s), Process Zone, Clause, and Description summary truncated to a maximum of 120 characters with an ellipsis indicator when the full text exceeds that length
2. WHEN the user clicks on a table row, THE Dashboard SHALL display a detail view showing the full finding description, evidence, and affected clauses, and SHALL provide a visible control to return to the findings table
3. THE Dashboard SHALL support sorting by any column in ascending or descending order, with the default sort being by ID in ascending order
4. THE Dashboard SHALL support case-insensitive substring search filtering across finding descriptions and IDs, updating the displayed results after the user has entered at least 2 characters
5. WHEN the user applies global filters, THE findings table SHALL display only findings matching the active filter criteria
6. IF no findings match the current search text or active filters, THEN THE Dashboard SHALL display an empty-state message indicating that no findings match the current criteria

### Requirement 11: Systemic Finding Dedicated Panel

**User Story:** As a quality manager, I want a dedicated panel for the systemic transversal finding (HTS-01/NCM-15), so that I can communicate its cross-process impact clearly to stakeholders.

#### Acceptance Criteria

1. THE Dashboard SHALL display a dedicated panel for HTS-01 showing: the finding description, all affected process zones, all affected standards, and the systemic nature explanation
2. THE Dashboard SHALL visually distinguish the HTS panel from regular finding displays using a distinct border color and background color that differs from other dashboard panels
3. THE Dashboard SHALL display a process-zone impact diagram showing all defined process zones and clearly indicating which are affected versus unaffected by the systemic finding
4. WHEN the HTS finding is absent from the dataset, THE Dashboard SHALL hide the systemic finding panel entirely
5. IF the HTS finding exists but has incomplete metadata, THEN THE Dashboard SHALL display available fields and indicate missing data with placeholder labels rather than hiding the panel or producing an error

### Requirement 12: Corrective Action Plan Timeline

**User Story:** As a project coordinator, I want a timeline visualization for corrective action plans, so that I can track remediation progress against deadlines.

#### Acceptance Criteria

1. THE Dashboard SHALL display a Gantt-style timeline showing up to 50 corrective actions with their planned start dates, deadlines, and current status
2. WHEN a corrective action has fields for responsible party, deadline, and status populated, THE Dashboard SHALL display those fields in the timeline
3. WHEN any of the responsible party, deadline, or status fields are empty or not yet populated for a corrective action, THE Dashboard SHALL display a placeholder indicating "Pending Assignment" for that action
4. THE Dashboard SHALL color-code timeline items by status: not started (gray), in progress (blue), completed (green), overdue (red), where overdue is defined as current date past the deadline AND status is not "completed"
5. WHEN a corrective action's status or deadline is updated, THE Dashboard SHALL reflect the change in the timeline within 5 seconds without requiring a full page reload
6. IF more than 50 corrective actions exist, THEN THE Dashboard SHALL provide scrolling or pagination to access all actions beyond the visible set

### Requirement 13: Dark Mode UI and Visual Design

**User Story:** As a user, I want a dark mode interface with clean vector graphics, so that the dashboard is comfortable to use during extended analysis sessions and presentations.

#### Acceptance Criteria

1. THE Dashboard SHALL render with a dark color theme as the default visual mode, where background surfaces have a relative luminance no greater than 0.05 and foreground text has a relative luminance no less than 0.75
2. THE Dashboard SHALL use vector-based chart rendering (SVG or equivalent) for all visualizations, maintaining no pixelation or rasterization artifacts at browser zoom levels from 50% to 400%
3. THE Dashboard SHALL maintain a minimum contrast ratio of 4.5:1 between normal-size text (below 18pt regular or 14pt bold) and background elements, and a minimum contrast ratio of 3:1 for large text (18pt regular or 14pt bold and above) and for non-text UI components and graphical objects, per WCAG AA standards
4. THE Dashboard SHALL use a modular layout where each visualization section is independently scrollable and collapsible, with all sections expanded by default and each section providing a visible toggle control to collapse or expand its content
5. WHEN a user collapses or expands a visualization section, THE Dashboard SHALL complete the transition within 300 milliseconds and preserve the collapsed or expanded state for the duration of the session

### Requirement 14: Application Performance

**User Story:** As a user, I want the dashboard to load and respond quickly, so that I can perform analysis without waiting.

#### Acceptance Criteria

1. WHEN the application starts with the default dataset (37 findings), THE Dashboard SHALL display all charts and filter controls in an interactive state within 3 seconds from the moment the user initiates the application launch
2. WHEN the user applies a filter selection or clicks a chart element, THE Dashboard SHALL re-render all affected visualizations with updated data within 1 second from the moment of the user action
3. WHEN the application starts with a dataset of up to 200 findings, THE Dashboard SHALL display all charts and filter controls in an interactive state within 3 seconds and respond to filter or chart interactions within 1 second
4. WHEN the user triggers a filter or chart interaction after initial load, THE Data_Pipeline SHALL serve the requested data without re-parsing the source file, ensuring no additional latency beyond the 1-second response time specified in criterion 2
5. IF the dataset exceeds 200 findings, THEN THE Dashboard SHALL display an error message indicating that the dataset size is not supported

### Requirement 15: Data Export

**User Story:** As a management representative, I want to export filtered data and visualizations, so that I can include them in management review presentations.

#### Acceptance Criteria

1. WHEN the user requests a data export and the current filter returns one or more findings, THE Dashboard SHALL generate a CSV file containing the currently filtered findings with all metadata columns, named with the export date and active filter summary
2. WHEN the user requests a visualization export, THE Dashboard SHALL generate PNG image files at a minimum resolution of 1920×1080 pixels, or SVG image files, of all currently displayed charts
3. THE Dashboard SHALL include the active filter configuration as a header section in CSV exports and as embedded metadata in image exports
4. IF the current filter returns zero findings when the user requests a data export, THEN THE Dashboard SHALL display a message indicating that no data is available to export and SHALL NOT generate a file
5. IF an export operation fails to complete, THEN THE Dashboard SHALL display an error message indicating the failure reason and SHALL NOT produce a partial or corrupted file

### Requirement 16: Future Extensibility Fields

**User Story:** As a system administrator, I want the data model to include fields for responsible parties, deadlines, estimated costs, and corrective action status, so that the system can support full CAPA tracking in future iterations.

#### Acceptance Criteria

1. THE Data_Pipeline SHALL include the following optional fields in the findings data model: responsible_party (text, maximum 150 characters), deadline (ISO 8601 date), estimated_mitigation_cost (numeric value from 0.01 to 999,999,999.99 with up to 2 decimal places), corrective_action_status (one of: "open", "in_progress", "completed", "verified", "closed")
2. WHEN optional future fields are empty or null, THE Dashboard SHALL render the corresponding field area with a placeholder label indicating no value has been assigned, without producing errors or preventing display of other populated fields
3. WHEN a deadline field is populated, THE Data_Pipeline SHALL validate that the value is a valid ISO 8601 date (YYYY-MM-DD format) and reject the record with an error message indicating the invalid date format if validation fails
4. IF estimated_mitigation_cost or corrective_action_status fields contain values outside their defined format or allowed values, THEN THE Data_Pipeline SHALL reject the record and return an error message indicating which field failed validation

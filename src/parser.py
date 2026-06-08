"""
Parser module for the SGI Audit Dashboard.

Reads a Markdown-formatted SGI audit findings report and extracts
structured finding data into a Pandas DataFrame. Handles multi-norm
expansion (one row per standard), HTS transversal findings, and
zone/standard name normalization.

Design decisions:
- Regex-based extraction tuned to the specific Markdown table format
- Spanish-to-English zone name mapping for consistent PROCESS_ZONES values
- Abbreviated-to-full standard name mapping (ISO 9001 → ISO 9001:2015)
- Multi-norm findings expanded into one row per standard (Requirement 1.2)
- HTS findings flagged with is_transversal=True, associated with all zones
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import pandas as pd

from src.models import (
    PROCESS_ZONES,
    STANDARDS,
    Finding,
    FindingType,
    ValidationResult,
)


# =============================================================================
# Exception Classes
# =============================================================================


class ParserError(Exception):
    """Raised when the Markdown report cannot be parsed.

    Attributes:
        line_number: The line number in the source file where the error occurred.
        field_name: The name of the missing or malformed field.
        expected_format: A description of the expected format for the field.
    """

    def __init__(
        self,
        message: str,
        line_number: Optional[int] = None,
        field_name: Optional[str] = None,
        expected_format: Optional[str] = None,
    ) -> None:
        self.line_number = line_number
        self.field_name = field_name
        self.expected_format = expected_format
        super().__init__(message)


# =============================================================================
# Mapping Dictionaries
# =============================================================================

# Map abbreviated standard names to their full ISO versions
STANDARD_MAPPING: dict[str, str] = {
    "ISO 9001": "ISO 9001:2015",
    "ISO 9001:2015": "ISO 9001:2015",
    "ISO 14001": "ISO 14001:2015",
    "ISO 14001:2015": "ISO 14001:2015",
    "ISO 45001": "ISO 45001:2018",
    "ISO 45001:2018": "ISO 45001:2018",
}

# Map Spanish process zone names to English PROCESS_ZONES equivalents
ZONE_MAPPING: dict[str, str] = {
    # Logistics variants
    "Logística – Despacho/Carga": "Logistics",
    "Logística/Despacho": "Logistics",
    "Transporte – Logística Nacional": "Logistics",
    "Logística - Despacho/Carga": "Logistics",
    "Logística": "Logistics",
    # Storage Yard variants
    "Patio de Acopio – Producto Terminado": "Storage Yard",
    "Patio de Acopio": "Storage Yard",
    "Patio de Acopio - Producto Terminado": "Storage Yard",
    "Patio Producto Terminado": "Storage Yard",
    # Manufacturing/Prestressing variants
    "Fabricación – Nave de Pretensado": "Manufacturing/Prestressing",
    "Fabricación/Pretensado": "Manufacturing/Prestressing",
    "Fabricación General": "Manufacturing/Prestressing",
    "Nave de Pretensado": "Manufacturing/Prestressing",
    "Nave Interior de Pretensado": "Manufacturing/Prestressing",
    "Fabricación - Nave de Pretensado": "Manufacturing/Prestressing",
    "Moldes y Bancadas": "Manufacturing/Prestressing",
    "Silos de Cemento": "Manufacturing/Prestressing",
    "Nave de Fabricación": "Manufacturing/Prestressing",
    # Lab variants
    "Laboratorio de Ensayos": "Lab",
    "Laboratorio": "Lab",
    # Boilers variants
    "Servicios – Sala de Calderas": "Boilers",
    "Calderas": "Boilers",
    "Calderas/Servicios": "Boilers",
    "Servicios - Sala de Calderas": "Boilers",
    "Calderas – Registro de Anomalías": "Boilers",
    "Calderas - Registro de Anomalías": "Boilers",
    # Aggregates variants
    "Acopio de Áridos – Materias Primas": "Aggregates",
    "Acopio de Áridos": "Aggregates",
    "Planta de Dosificación y Acopios": "Aggregates",
    "Acopio de Áridos - Materias Primas": "Aggregates",
    # Steel Storage variants
    "Almacenamiento – Acero de Pretensado": "Steel Storage",
    "Patio de Almacenamiento Acero": "Steel Storage",
    "Almacenamiento - Acero de Pretensado": "Steel Storage",
    # Chemical Storage variants
    "Almacenamiento – Sustancias Químicas": "Chemical Storage",
    "Zona de Residuos Industriales": "Chemical Storage",
    "Almacenamiento - Sustancias Químicas": "Chemical Storage",
    "Acopio de Áridos – Zona Residuos": "Chemical Storage",
    "Acopio de Áridos - Zona Residuos": "Chemical Storage",
    # Document Management variants
    "Gestión Documental – SGI": "Document Management",
    "Gestión Documental": "Document Management",
    "Gestión Documental - SGI": "Document Management",
    # General/Transversal variants
    "General": "General/Transversal",
    "SGI Transversal": "General/Transversal",
    "Entorno General": "General/Transversal",
    "Entorno General – Calidad del Aire": "General/Transversal",
    "Entorno General - Calidad del Aire": "General/Transversal",
    "Periferia de Planta": "General/Transversal",
    "Oficina de Control de Calidad": "General/Transversal",
    "Fabricación – Controles Operacionales": "Manufacturing/Prestressing",
    "Fabricación - Controles Operacionales": "Manufacturing/Prestressing",
}

# Section header patterns mapping to FindingType values
SECTION_PATTERNS: dict[str, str] = {
    r"##\s*A\.\s*NO CONFORMIDADES MAYORES\s*\(NCM\)": "NCM",
    r"##\s*B\.\s*NO CONFORMIDADES MENORES\s*\(NCm\)": "NCm",
    r"##\s*C\.\s*OPORTUNIDADES DE MEJORA\s*\(OdM\)": "ODM",
    r"##\s*D\.\s*OBSERVACIONES\s*\(OBS\)": "OBS",
    r"##\s*E\.\s*HALLAZGO TRANSVERSAL SIST[ÉE]MICO": "HTS",
}


# =============================================================================
# Internal Helper Functions
# =============================================================================


def _normalize_standard(raw_standard: str) -> str:
    """Normalize a standard name to its full ISO version.

    Args:
        raw_standard: The raw standard string (possibly abbreviated).

    Returns:
        The full standard name (e.g., "ISO 9001:2015").

    Raises:
        ParserError: If the standard name cannot be mapped.
    """
    cleaned = raw_standard.strip()
    if cleaned in STANDARD_MAPPING:
        return STANDARD_MAPPING[cleaned]
    # Attempt partial match
    for key, value in STANDARD_MAPPING.items():
        if key in cleaned:
            return value
    raise ParserError(
        f"Unrecognized standard: '{cleaned}'",
        field_name="standards",
        expected_format="One of: ISO 9001, ISO 14001, ISO 45001 (with optional year)",
    )


def _normalize_zone(raw_zone: str) -> str:
    """Normalize a Spanish process zone name to its English equivalent.

    Args:
        raw_zone: The raw zone name in Spanish.

    Returns:
        The English zone name from PROCESS_ZONES.

    Raises:
        ParserError: If the zone name cannot be mapped.
    """
    cleaned = raw_zone.strip()
    if cleaned in ZONE_MAPPING:
        return ZONE_MAPPING[cleaned]
    # Attempt case-insensitive match
    for key, value in ZONE_MAPPING.items():
        if key.lower() == cleaned.lower():
            return value
    # If already in English PROCESS_ZONES
    if cleaned in PROCESS_ZONES:
        return cleaned
    raise ParserError(
        f"Unrecognized process zone: '{cleaned}'",
        field_name="process_zone",
        expected_format=f"One of: {PROCESS_ZONES}",
    )


def _split_standards(raw_standards: str) -> list[str]:
    """Split a multi-norm field by ' / ' separator and normalize each.

    Args:
        raw_standards: Raw standards string, possibly with ' / ' separator.

    Returns:
        List of normalized standard names.
    """
    parts = [s.strip() for s in raw_standards.split("/")]
    parts = [p for p in parts if p]  # Remove empty parts
    return [_normalize_standard(p) for p in parts]


def _parse_table_rows(lines: list[str]) -> list[list[str]]:
    """Parse pipe-delimited Markdown table rows.

    Skips header and separator rows. Returns list of cell value lists.

    Args:
        lines: The lines of a Markdown table section.

    Returns:
        List of rows, each row being a list of cell strings.
    """
    rows = []
    header_found = False
    separator_found = False

    for line in lines:
        stripped = line.strip()
        if not stripped or not stripped.startswith("|"):
            continue

        # Parse cells from pipe-delimited line
        cells = [c.strip() for c in stripped.split("|")]
        # Remove empty first and last elements from leading/trailing pipes
        if cells and cells[0] == "":
            cells = cells[1:]
        if cells and cells[-1] == "":
            cells = cells[:-1]

        if not cells:
            continue

        # Detect separator row (all cells are dashes/colons)
        if all(re.match(r"^[-:]+$", c) for c in cells):
            separator_found = True
            continue

        # First non-separator row with pipes is the header
        if not header_found:
            header_found = True
            continue

        # Data rows come after header and separator
        if header_found and separator_found:
            rows.append(cells)

    return rows


def _extract_ncm_ncm_findings(
    section_text: str,
    finding_type: str,
    section_start_line: int,
) -> list[dict]:
    """Extract findings from NCM or NCm sections.

    Table columns: N° | Hallazgo Ref. | Proceso / Zona | Norma | Cláusula | Descripción

    Args:
        section_text: The raw text of the section.
        finding_type: "NCM" or "NCm".
        section_start_line: Line number offset in original file.

    Returns:
        List of finding dictionaries.
    """
    lines = section_text.split("\n")
    table_rows = _parse_table_rows(lines)
    findings = []

    for row_idx, cells in enumerate(table_rows):
        if len(cells) < 6:
            raise ParserError(
                f"Incomplete table row in {finding_type} section: expected at least 6 columns, got {len(cells)}",
                line_number=section_start_line + row_idx,
                field_name="table_row",
                expected_format="N° | Hallazgo Ref. | Proceso / Zona | Norma | Cláusula | Descripción",
            )

        finding_id = cells[0].strip()
        raw_zone = cells[2].strip()
        raw_standard = cells[3].strip()
        clause_ref = cells[4].strip() or None
        description = cells[5].strip()

        # Validate finding_id format
        if not re.match(r"^(NCM|NCm|ODM|OBS)-\d{2}$", finding_id):
            raise ParserError(
                f"Invalid finding ID format: '{finding_id}'",
                line_number=section_start_line + row_idx,
                field_name="finding_id",
                expected_format="(NCM|NCm|ODM|OBS)-\\d{2} (e.g., NCM-01)",
            )

        # Validate description is present
        if not description:
            raise ParserError(
                f"Missing description for finding {finding_id}",
                line_number=section_start_line + row_idx,
                field_name="description",
                expected_format="Non-empty text describing the finding",
            )

        # Normalize zone
        try:
            process_zone = _normalize_zone(raw_zone)
        except ParserError as e:
            e.line_number = section_start_line + row_idx
            raise

        # Parse standards (may be multi-norm with " / ")
        try:
            standards = _split_standards(raw_standard)
        except ParserError as e:
            e.line_number = section_start_line + row_idx
            raise

        findings.append({
            "finding_id": finding_id,
            "finding_type": finding_type,
            "description": description,
            "standards": standards,
            "process_zone": process_zone,
            "clause_ref": clause_ref,
            "evidence": None,
            "is_transversal": False,
        })

    return findings


def _extract_odm_findings(
    section_text: str,
    section_start_line: int,
) -> list[dict]:
    """Extract findings from ODM (Oportunidades de Mejora) section.

    Table columns: N° | Hallazgo Ref. | Proceso | Norma Ref. | Descripción de la Oportunidad

    Args:
        section_text: The raw text of the ODM section.
        section_start_line: Line number offset in original file.

    Returns:
        List of finding dictionaries.
    """
    lines = section_text.split("\n")
    table_rows = _parse_table_rows(lines)
    findings = []

    for row_idx, cells in enumerate(table_rows):
        if len(cells) < 5:
            raise ParserError(
                f"Incomplete table row in ODM section: expected at least 5 columns, got {len(cells)}",
                line_number=section_start_line + row_idx,
                field_name="table_row",
                expected_format="N° | Hallazgo Ref. | Proceso | Norma Ref. | Descripción",
            )

        finding_id = cells[0].strip()
        # Normalize OdM to ODM
        finding_id = re.sub(r"^OdM", "ODM", finding_id)
        raw_zone = cells[2].strip()
        raw_standard_clause = cells[3].strip()
        description = cells[4].strip()

        # The ODM section has "Norma Ref." which may include clause info
        # Format: "ISO 9001: 10.3" → standard="ISO 9001", clause="10.3"
        # Or just "ISO 9001" without clause
        clause_ref = None
        if ":" in raw_standard_clause:
            parts = raw_standard_clause.split(":", 1)
            raw_standard = parts[0].strip()
            clause_ref = parts[1].strip() or None
        else:
            raw_standard = raw_standard_clause

        # Validate finding_id format
        if not re.match(r"^(NCM|NCm|ODM|OBS)-\d{2}$", finding_id):
            raise ParserError(
                f"Invalid finding ID format: '{finding_id}'",
                line_number=section_start_line + row_idx,
                field_name="finding_id",
                expected_format="(NCM|NCm|ODM|OBS)-\\d{2} (e.g., ODM-01)",
            )

        # Validate description is present
        if not description:
            raise ParserError(
                f"Missing description for finding {finding_id}",
                line_number=section_start_line + row_idx,
                field_name="description",
                expected_format="Non-empty text describing the opportunity",
            )

        # Normalize zone
        try:
            process_zone = _normalize_zone(raw_zone)
        except ParserError as e:
            e.line_number = section_start_line + row_idx
            raise

        # Parse standards
        try:
            standards = _split_standards(raw_standard)
        except ParserError as e:
            e.line_number = section_start_line + row_idx
            raise

        findings.append({
            "finding_id": finding_id,
            "finding_type": "ODM",
            "description": description,
            "standards": standards,
            "process_zone": process_zone,
            "clause_ref": clause_ref,
            "evidence": None,
            "is_transversal": False,
        })

    return findings


def _extract_obs_findings(
    section_text: str,
    section_start_line: int,
) -> list[dict]:
    """Extract findings from OBS (Observaciones) section.

    Table columns: N° | Hallazgo Ref. | Proceso / Zona | Descripción

    Args:
        section_text: The raw text of the OBS section.
        section_start_line: Line number offset in original file.

    Returns:
        List of finding dictionaries.
    """
    lines = section_text.split("\n")
    table_rows = _parse_table_rows(lines)
    findings = []

    for row_idx, cells in enumerate(table_rows):
        if len(cells) < 4:
            # May be a summary table row — skip rather than error
            continue

        finding_id = cells[0].strip()
        raw_zone = cells[2].strip()
        description = cells[3].strip()

        # Validate finding_id format — skip rows that don't match (summary tables)
        if not re.match(r"^(NCM|NCm|ODM|OBS)-\d{2}$", finding_id):
            continue

        # Validate description is present
        if not description:
            raise ParserError(
                f"Missing description for finding {finding_id}",
                line_number=section_start_line + row_idx,
                field_name="description",
                expected_format="Non-empty text describing the observation",
            )

        # Normalize zone
        try:
            process_zone = _normalize_zone(raw_zone)
        except ParserError as e:
            e.line_number = section_start_line + row_idx
            raise

        # OBS findings have no standard or clause reference in their table
        # Use all standards as default for observations
        findings.append({
            "finding_id": finding_id,
            "finding_type": "OBS",
            "description": description,
            "standards": list(STANDARDS),  # All standards apply
            "process_zone": process_zone,
            "clause_ref": None,
            "evidence": None,
            "is_transversal": False,
        })

    return findings


def _extract_hts_findings(
    section_text: str,
    section_start_line: int,
) -> list[dict]:
    """Extract HTS (Hallazgo Transversal Sistémico) findings.

    HTS findings are systemic and affect all process zones. The section
    typically contains NCM-15 as a systemic finding. We look for a table
    or structured content describing the finding.

    Args:
        section_text: The raw text of the HTS section.
        section_start_line: Line number offset in original file.

    Returns:
        List of finding dictionaries (one per zone for the transversal finding).
    """
    lines = section_text.split("\n")
    findings = []

    # Try to find the finding ID in the section
    finding_id = None
    description = None
    standards = list(STANDARDS)  # HTS affects all standards by default

    # Look for finding ID pattern in text
    id_match = re.search(r"(NCM|NCm|ODM|OBS)-\d{2}", section_text)
    if id_match:
        finding_id = id_match.group(0)

    # Try table-based extraction first
    table_rows = _parse_table_rows(lines)
    if table_rows:
        # If there's a table, extract from it
        for cells in table_rows:
            if len(cells) >= 2:
                # Try to find ID and description from table
                for cell in cells:
                    cell_stripped = cell.strip()
                    if re.match(r"^(NCM|NCm|ODM|OBS)-\d{2}$", cell_stripped):
                        finding_id = cell_stripped
                    elif len(cell_stripped) > 20 and not finding_id:
                        pass  # skip
                    elif len(cell_stripped) > 20:
                        if description is None:
                            description = cell_stripped

            # Try to extract standards from cells
            for cell in cells:
                if "ISO" in cell:
                    try:
                        standards = _split_standards(cell.strip())
                    except ParserError:
                        pass  # Keep default all standards

    # If no table, look for description in paragraph text
    if description is None:
        # Collect non-header, non-empty lines as description
        desc_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            if stripped.startswith("|"):
                continue
            if re.match(r"^[-:]+$", stripped):
                continue
            desc_lines.append(stripped)

        if desc_lines:
            description = " ".join(desc_lines)
            # Truncate to max length if needed
            if len(description) > 2000:
                description = description[:2000]

    # If we still don't have a finding_id, default to NCM-15 for HTS
    if finding_id is None:
        finding_id = "NCM-15"

    if description is None:
        description = "Hallazgo Transversal Sistémico"

    # Determine finding_type from the ID prefix
    finding_type = finding_id.split("-")[0]

    # HTS finding is associated with ALL process zones
    for zone in PROCESS_ZONES:
        findings.append({
            "finding_id": finding_id,
            "finding_type": finding_type,
            "description": description,
            "standards": standards,
            "process_zone": zone,
            "clause_ref": None,
            "evidence": None,
            "is_transversal": True,
        })

    return findings


def _split_into_sections(content: str) -> list[tuple[str, str, int]]:
    """Split file content into sections by finding-type headers.

    Returns:
        List of tuples: (section_text, finding_type, start_line_number)
    """
    lines = content.split("\n")
    sections = []
    current_section_start = None
    current_type = None
    current_start_line = 0

    for i, line in enumerate(lines):
        for pattern, ftype in SECTION_PATTERNS.items():
            if re.match(pattern, line.strip()):
                # Save previous section
                if current_section_start is not None:
                    section_text = "\n".join(lines[current_section_start:i])
                    sections.append((section_text, current_type, current_start_line))
                current_section_start = i
                current_type = ftype
                current_start_line = i + 1  # 1-indexed line number
                break

    # Save last section
    if current_section_start is not None:
        section_text = "\n".join(lines[current_section_start:])
        sections.append((section_text, current_type, current_start_line))

    return sections


# =============================================================================
# Public API
# =============================================================================


def extract_section_findings(
    section_text: str,
    finding_type: str,
) -> list[dict]:
    """Extract all findings of a given type from a section of Markdown text.

    This is a public interface that delegates to the appropriate internal
    extractor based on the finding type. Full implementation in task 2.2.

    Args:
        section_text: The raw Markdown text of one finding-type section.
        finding_type: One of "NCM", "NCm", "ODM", "OBS", "HTS".

    Returns:
        List of finding dictionaries extracted from the section.
    """
    if finding_type in ("NCM", "NCm"):
        return _extract_ncm_ncm_findings(section_text, finding_type, 0)
    elif finding_type == "ODM":
        return _extract_odm_findings(section_text, 0)
    elif finding_type == "OBS":
        return _extract_obs_findings(section_text, 0)
    elif finding_type == "HTS":
        return _extract_hts_findings(section_text, 0)
    else:
        raise ParserError(
            f"Unknown finding type: '{finding_type}'",
            field_name="finding_type",
            expected_format="One of: NCM, NCm, ODM, OBS, HTS",
        )


def validate_finding_structure(finding: dict) -> ValidationResult:
    """Validate that a finding dictionary has all required fields with correct formats.

    Placeholder for full implementation in task 2.2.

    Args:
        finding: Dictionary with finding fields.

    Returns:
        ValidationResult with is_valid=True if all checks pass.
    """
    errors = []

    # Check required fields
    required_fields = ["finding_id", "finding_type", "description", "standards", "process_zone"]
    for field in required_fields:
        if field not in finding or not finding[field]:
            errors.append(f"Missing required field: {field}")

    # Validate finding_id format
    if "finding_id" in finding and finding["finding_id"]:
        if not re.match(r"^(NCM|NCm|ODM|OBS)-\d{2}$", finding["finding_id"]):
            errors.append(
                f"finding_id '{finding['finding_id']}' does not match pattern (NCM|NCm|ODM|OBS)-\\d{{2}}"
            )

    # Validate standards is non-empty list
    if "standards" in finding:
        if not isinstance(finding["standards"], list) or len(finding["standards"]) == 0:
            errors.append("standards must be a non-empty list")

    # Validate process_zone
    if "process_zone" in finding and finding["process_zone"]:
        if finding["process_zone"] not in PROCESS_ZONES:
            errors.append(
                f"process_zone '{finding['process_zone']}' is not in PROCESS_ZONES"
            )

    # Validate clause_ref format if present
    if finding.get("clause_ref"):
        if not re.match(r"^\d+\.\d+(\.\d+)?$", finding["clause_ref"]):
            errors.append(
                f"clause_ref '{finding['clause_ref']}' does not match pattern \\d+.\\d+(.\\d+)?"
            )

    # Validate description length
    if finding.get("description") and len(finding["description"]) > 2000:
        errors.append(f"description exceeds 2000 characters ({len(finding['description'])})")

    # Validate evidence length
    if finding.get("evidence") and len(finding["evidence"]) > 5000:
        errors.append(f"evidence exceeds 5000 characters ({len(finding['evidence'])})")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
    )


def parse_markdown_report(file_path: str) -> pd.DataFrame:
    """Parse a Markdown audit report and return a DataFrame of findings.

    Reads the file, splits by finding-type section headers (NCM, NCm, ODM,
    OBS, HTS), extracts findings from each section's table, normalizes
    zone and standard names, expands multi-norm findings into one row per
    standard, and returns a DataFrame with the full schema.

    Args:
        file_path: Absolute or relative path to the .md file.

    Returns:
        DataFrame with columns: finding_id, finding_type, description,
        standards, process_zone, clause_ref, evidence, is_transversal,
        responsible_party, deadline, estimated_mitigation_cost,
        corrective_action_status.

    Raises:
        ParserError: If the file is malformed, with line_number,
                     field_name, and expected_format attributes.
        FileNotFoundError: If the file does not exist.
    """
    # Read file
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Report file not found: {file_path}")

    content = path.read_text(encoding="utf-8")

    # Split into sections by finding-type headers
    sections = _split_into_sections(content)

    if not sections:
        raise ParserError(
            "No finding sections found in the Markdown file. "
            "Expected headers like '## A. NO CONFORMIDADES MAYORES (NCM)'",
            field_name="section_header",
            expected_format="## A. NO CONFORMIDADES MAYORES (NCM)",
        )

    # Extract findings from each section
    all_findings: list[dict] = []

    for section_text, finding_type, start_line in sections:
        if finding_type in ("NCM", "NCm"):
            findings = _extract_ncm_ncm_findings(section_text, finding_type, start_line)
        elif finding_type == "ODM":
            findings = _extract_odm_findings(section_text, start_line)
        elif finding_type == "OBS":
            findings = _extract_obs_findings(section_text, start_line)
        elif finding_type == "HTS":
            findings = _extract_hts_findings(section_text, start_line)
        else:
            continue

        all_findings.extend(findings)

    # Expand multi-norm findings: one row per standard
    expanded_rows: list[dict] = []

    for finding in all_findings:
        standards_list = finding["standards"]
        if len(standards_list) > 1:
            # Create one row per standard
            for standard in standards_list:
                row = {**finding}
                row["standards"] = standard
                expanded_rows.append(row)
        else:
            row = {**finding}
            row["standards"] = standards_list[0] if standards_list else None
            expanded_rows.append(row)

    # Build DataFrame with complete schema
    df = pd.DataFrame(expanded_rows, columns=[
        "finding_id",
        "finding_type",
        "description",
        "standards",
        "process_zone",
        "clause_ref",
        "evidence",
        "is_transversal",
    ])

    # Add future extensibility columns (Requirement 16)
    df["responsible_party"] = None
    df["deadline"] = None
    df["estimated_mitigation_cost"] = None
    df["corrective_action_status"] = None

    # Ensure proper types
    df["is_transversal"] = df["is_transversal"].astype(bool)

    return df

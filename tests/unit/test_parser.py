"""Unit tests for the parser module (Task 2.1)."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.parser import (
    ParserError,
    STANDARD_MAPPING,
    ZONE_MAPPING,
    _normalize_standard,
    _normalize_zone,
    _split_standards,
    _parse_table_rows,
    extract_section_findings,
    validate_finding_structure,
    parse_markdown_report,
)
from src.models import PROCESS_ZONES, STANDARDS


# =============================================================================
# Test ParserError
# =============================================================================


class TestParserError:
    """Tests for ParserError exception class."""

    def test_parser_error_attributes(self):
        err = ParserError(
            "Test error",
            line_number=42,
            field_name="finding_id",
            expected_format="NCM-\\d{2}",
        )
        assert err.line_number == 42
        assert err.field_name == "finding_id"
        assert err.expected_format == "NCM-\\d{2}"
        assert str(err) == "Test error"

    def test_parser_error_defaults(self):
        err = ParserError("Simple error")
        assert err.line_number is None
        assert err.field_name is None
        assert err.expected_format is None


# =============================================================================
# Test Standard Normalization
# =============================================================================


class TestStandardNormalization:
    """Tests for standard name mapping."""

    def test_abbreviated_to_full(self):
        assert _normalize_standard("ISO 9001") == "ISO 9001:2015"
        assert _normalize_standard("ISO 14001") == "ISO 14001:2015"
        assert _normalize_standard("ISO 45001") == "ISO 45001:2018"

    def test_already_full(self):
        assert _normalize_standard("ISO 9001:2015") == "ISO 9001:2015"
        assert _normalize_standard("ISO 14001:2015") == "ISO 14001:2015"
        assert _normalize_standard("ISO 45001:2018") == "ISO 45001:2018"

    def test_with_whitespace(self):
        assert _normalize_standard("  ISO 9001  ") == "ISO 9001:2015"

    def test_unknown_standard_raises(self):
        with pytest.raises(ParserError) as exc_info:
            _normalize_standard("ISO 99999")
        assert exc_info.value.field_name == "standards"


# =============================================================================
# Test Zone Normalization
# =============================================================================


class TestZoneNormalization:
    """Tests for process zone name mapping."""

    def test_logistics_variants(self):
        assert _normalize_zone("Logística – Despacho/Carga") == "Logistics"
        assert _normalize_zone("Logística/Despacho") == "Logistics"
        assert _normalize_zone("Transporte – Logística Nacional") == "Logistics"

    def test_manufacturing_variants(self):
        assert _normalize_zone("Fabricación – Nave de Pretensado") == "Manufacturing/Prestressing"
        assert _normalize_zone("Fabricación/Pretensado") == "Manufacturing/Prestressing"
        assert _normalize_zone("Nave de Pretensado") == "Manufacturing/Prestressing"
        assert _normalize_zone("Moldes y Bancadas") == "Manufacturing/Prestressing"
        assert _normalize_zone("Nave de Fabricación") == "Manufacturing/Prestressing"

    def test_chemical_storage_variants(self):
        assert _normalize_zone("Almacenamiento – Sustancias Químicas") == "Chemical Storage"
        assert _normalize_zone("Zona de Residuos Industriales") == "Chemical Storage"
        assert _normalize_zone("Acopio de Áridos – Zona Residuos") == "Chemical Storage"

    def test_general_transversal_variants(self):
        assert _normalize_zone("General") == "General/Transversal"
        assert _normalize_zone("SGI Transversal") == "General/Transversal"
        assert _normalize_zone("Periferia de Planta") == "General/Transversal"

    def test_english_zone_passthrough(self):
        for zone in PROCESS_ZONES:
            assert _normalize_zone(zone) == zone

    def test_unknown_zone_raises(self):
        with pytest.raises(ParserError) as exc_info:
            _normalize_zone("Unknown Zone XYZ")
        assert exc_info.value.field_name == "process_zone"


# =============================================================================
# Test Multi-Standard Splitting
# =============================================================================


class TestSplitStandards:
    """Tests for multi-norm field splitting."""

    def test_single_standard(self):
        result = _split_standards("ISO 9001")
        assert result == ["ISO 9001:2015"]

    def test_multi_standard(self):
        result = _split_standards("ISO 9001 / ISO 45001")
        assert result == ["ISO 9001:2015", "ISO 45001:2018"]

    def test_triple_standard(self):
        result = _split_standards("ISO 9001 / ISO 14001 / ISO 45001")
        assert result == ["ISO 9001:2015", "ISO 14001:2015", "ISO 45001:2018"]


# =============================================================================
# Test Table Row Parsing
# =============================================================================


class TestParseTableRows:
    """Tests for Markdown table row extraction."""

    def test_basic_table(self):
        lines = [
            "| N° | ID | Zone | Standard | Clause | Description |",
            "| --- | --- | --- | --- | --- | --- |",
            "| 1 | NCM-01 | Logística | ISO 9001 | 4.4 | Test desc |",
            "| 2 | NCM-02 | Lab | ISO 14001 | 5.1 | Another desc |",
        ]
        rows = _parse_table_rows(lines)
        assert len(rows) == 2
        assert rows[0][1] == "NCM-01"
        assert rows[1][1] == "NCM-02"

    def test_empty_lines_ignored(self):
        lines = [
            "",
            "| N° | ID |",
            "| --- | --- |",
            "",
            "| 1 | NCM-01 |",
            "",
        ]
        rows = _parse_table_rows(lines)
        assert len(rows) == 1


# =============================================================================
# Test parse_markdown_report (Full Integration)
# =============================================================================


class TestParseMarkdownReport:
    """Tests for the main parse_markdown_report function."""

    def _create_temp_report(self, content: str) -> str:
        """Create a temporary Markdown file and return its path."""
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        )
        tmp.write(content)
        tmp.close()
        return tmp.name

    def test_basic_ncm_parsing(self):
        content = """# Informe de Auditoría

## A. NO CONFORMIDADES MAYORES (NCM)

| N° | Hallazgo Ref. | Proceso / Zona | Norma | Cláusula | Descripción del Incumplimiento |
| --- | --- | --- | --- | --- | --- |
| 1 | NCM-01 | Logística – Despacho/Carga | ISO 9001 | 4.4 | Falta de control documental |
| 2 | NCM-02 | Laboratorio de Ensayos | ISO 14001 | 6.1.2 | Residuos no gestionados |
"""
        path = self._create_temp_report(content)
        df = parse_markdown_report(path)

        assert len(df) == 2
        assert df.iloc[0]["finding_id"] == "NCM-01"
        assert df.iloc[0]["finding_type"] == "NCM"
        assert df.iloc[0]["process_zone"] == "Logistics"
        assert df.iloc[0]["standards"] == "ISO 9001:2015"
        assert df.iloc[0]["clause_ref"] == "4.4"
        assert df.iloc[1]["finding_id"] == "NCM-02"
        assert df.iloc[1]["process_zone"] == "Lab"
        assert df.iloc[1]["standards"] == "ISO 14001:2015"

        # Verify schema columns
        expected_columns = [
            "finding_id", "finding_type", "description", "standards",
            "process_zone", "clause_ref", "evidence", "is_transversal",
            "responsible_party", "deadline", "estimated_mitigation_cost",
            "corrective_action_status",
        ]
        assert list(df.columns) == expected_columns

        Path(path).unlink()

    def test_multi_norm_expansion(self):
        """Multi-norm findings produce one row per standard (Req 1.2)."""
        content = """# Informe

## A. NO CONFORMIDADES MAYORES (NCM)

| N° | Hallazgo Ref. | Proceso / Zona | Norma | Cláusula | Descripción del Incumplimiento |
| --- | --- | --- | --- | --- | --- |
| 1 | NCM-01 | Fabricación/Pretensado | ISO 9001 / ISO 45001 | 4.4 | Hallazgo multi-norma |
"""
        path = self._create_temp_report(content)
        df = parse_markdown_report(path)

        # Should have 2 rows (one per standard)
        assert len(df) == 2
        assert df.iloc[0]["finding_id"] == "NCM-01"
        assert df.iloc[0]["standards"] == "ISO 9001:2015"
        assert df.iloc[1]["finding_id"] == "NCM-01"
        assert df.iloc[1]["standards"] == "ISO 45001:2018"

        Path(path).unlink()

    def test_hts_transversal_finding(self):
        """HTS finding is flagged transversal and associated with all zones (Req 1.5)."""
        content = """# Informe

## E. HALLAZGO TRANSVERSAL SISTÉMICO

NCM-15: Falta de implementación del SGI a nivel sistémico.
Afecta a todas las zonas de proceso de la planta.
"""
        path = self._create_temp_report(content)
        df = parse_markdown_report(path)

        # Should have one row per zone (10 zones) × number of standards
        # HTS with all 3 standards → 10 zones × 3 standards = 30 rows
        assert len(df) == 30
        assert all(df["is_transversal"] == True)
        assert all(df["finding_id"] == "NCM-15")
        assert set(df["process_zone"]) == set(PROCESS_ZONES)

        Path(path).unlink()

    def test_ncm_section(self):
        """NCm section parsing."""
        content = """# Informe

## B. NO CONFORMIDADES MENORES (NCm)

| N° | Hallazgo Ref. | Proceso / Zona | Norma | Cláusula | Descripción del Incumplimiento |
| --- | --- | --- | --- | --- | --- |
| 1 | NCm-01 | Calderas | ISO 45001 | 8.1.1 | Falta EPP en zona de calderas |
"""
        path = self._create_temp_report(content)
        df = parse_markdown_report(path)

        assert len(df) == 1
        assert df.iloc[0]["finding_id"] == "NCm-01"
        assert df.iloc[0]["finding_type"] == "NCm"
        assert df.iloc[0]["process_zone"] == "Boilers"
        assert df.iloc[0]["standards"] == "ISO 45001:2018"

        Path(path).unlink()

    def test_odm_section(self):
        """ODM section parsing."""
        content = """# Informe

## C. OPORTUNIDADES DE MEJORA (OdM)

| N° | Hallazgo Ref. | Proceso | Norma Ref. | Descripción de la Oportunidad |
| --- | --- | --- | --- | --- |
| 1 | ODM-01 | Acopio de Áridos | ISO 14001 | Mejorar gestión de áridos |
"""
        path = self._create_temp_report(content)
        df = parse_markdown_report(path)

        assert len(df) == 1
        assert df.iloc[0]["finding_id"] == "ODM-01"
        assert df.iloc[0]["finding_type"] == "ODM"
        assert df.iloc[0]["process_zone"] == "Aggregates"
        assert df.iloc[0]["standards"] == "ISO 14001:2015"

        Path(path).unlink()

    def test_obs_section(self):
        """OBS section parsing."""
        content = """# Informe

## D. OBSERVACIONES (OBS)

| N° | Hallazgo Ref. | Proceso / Zona | Descripción |
| --- | --- | --- | --- |
| 1 | OBS-01 | Periferia de Planta | Observación sobre limpieza general |
"""
        path = self._create_temp_report(content)
        df = parse_markdown_report(path)

        # OBS findings have all standards → 3 rows
        assert len(df) == 3
        assert all(df["finding_id"] == "OBS-01")
        assert df.iloc[0]["finding_type"] == "OBS"
        assert df.iloc[0]["process_zone"] == "General/Transversal"

        Path(path).unlink()

    def test_finding_id_preservation(self):
        """Finding IDs are preserved without modification (Req 1.4)."""
        content = """# Informe

## A. NO CONFORMIDADES MAYORES (NCM)

| N° | Hallazgo Ref. | Proceso / Zona | Norma | Cláusula | Descripción del Incumplimiento |
| --- | --- | --- | --- | --- | --- |
| 1 | NCM-01 | Logística/Despacho | ISO 9001 | 4.4 | Test |
| 2 | NCM-12 | Laboratorio | ISO 14001 | 7.1 | Test2 |
"""
        path = self._create_temp_report(content)
        df = parse_markdown_report(path)

        assert df.iloc[0]["finding_id"] == "NCM-01"
        assert df.iloc[1]["finding_id"] == "NCM-12"

        Path(path).unlink()

    def test_absent_clause_ref_is_null(self):
        """Absent clause_ref sets column to None without error (Req 1.6)."""
        content = """# Informe

## A. NO CONFORMIDADES MAYORES (NCM)

| N° | Hallazgo Ref. | Proceso / Zona | Norma | Cláusula | Descripción del Incumplimiento |
| --- | --- | --- | --- | --- | --- |
| 1 | NCM-01 | Logística/Despacho | ISO 9001 |  | No clause ref here |
"""
        path = self._create_temp_report(content)
        df = parse_markdown_report(path)

        assert df.iloc[0]["clause_ref"] is None

        Path(path).unlink()

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_markdown_report("/nonexistent/path/report.md")

    def test_no_sections_raises_parser_error(self):
        """A file with no finding sections raises ParserError."""
        content = "# Just a title\n\nNo finding sections here.\n"
        path = self._create_temp_report(content)

        with pytest.raises(ParserError) as exc_info:
            parse_markdown_report(path)
        assert "No finding sections found" in str(exc_info.value)

        Path(path).unlink()

    def test_full_report_with_all_sections(self):
        """Test parsing a report with all section types."""
        content = """# Informe de Auditoría SGI

## A. NO CONFORMIDADES MAYORES (NCM)

| N° | Hallazgo Ref. | Proceso / Zona | Norma | Cláusula | Descripción del Incumplimiento |
| --- | --- | --- | --- | --- | --- |
| 1 | NCM-01 | Logística – Despacho/Carga | ISO 9001 / ISO 14001 | 4.4 | Hallazgo multi-norma |
| 2 | NCM-02 | Patio de Acopio | ISO 9001 | 7.1.5 | Otro hallazgo |

## B. NO CONFORMIDADES MENORES (NCm)

| N° | Hallazgo Ref. | Proceso / Zona | Norma | Cláusula | Descripción del Incumplimiento |
| --- | --- | --- | --- | --- | --- |
| 1 | NCm-01 | Calderas/Servicios | ISO 45001 | 8.1.1 | Falta EPP |

## C. OPORTUNIDADES DE MEJORA (OdM)

| N° | Hallazgo Ref. | Proceso | Norma Ref. | Descripción de la Oportunidad |
| --- | --- | --- | --- | --- |
| 1 | ODM-01 | Gestión Documental | ISO 9001 | Mejorar registro |

## D. OBSERVACIONES (OBS)

| N° | Hallazgo Ref. | Proceso / Zona | Descripción |
| --- | --- | --- | --- |
| 1 | OBS-01 | Entorno General | Observación general |

## E. HALLAZGO TRANSVERSAL SISTÉMICO

NCM-15: Hallazgo sistémico transversal afecta a toda la planta.
"""
        path = self._create_temp_report(content)
        df = parse_markdown_report(path)

        # NCM-01 multi-norm: 2 rows, NCM-02: 1 row, NCm-01: 1 row, ODM-01: 1 row
        # OBS-01: 3 rows (all standards), HTS NCM-15: 10 zones × 3 standards = 30
        expected_rows = 2 + 1 + 1 + 1 + 3 + 30
        assert len(df) == expected_rows

        # Verify HTS is transversal
        hts_rows = df[df["is_transversal"] == True]
        assert len(hts_rows) == 30
        assert all(hts_rows["finding_id"] == "NCM-15")

        Path(path).unlink()


# =============================================================================
# Test validate_finding_structure
# =============================================================================


class TestValidateFindingStructure:
    """Tests for validate_finding_structure."""

    def test_valid_finding(self):
        finding = {
            "finding_id": "NCM-01",
            "finding_type": "NCM",
            "description": "Test description",
            "standards": ["ISO 9001:2015"],
            "process_zone": "Logistics",
            "clause_ref": "4.4",
            "evidence": None,
            "is_transversal": False,
        }
        result = validate_finding_structure(finding)
        assert result.is_valid is True
        assert result.errors == []

    def test_missing_finding_id(self):
        finding = {
            "finding_id": "",
            "finding_type": "NCM",
            "description": "Test",
            "standards": ["ISO 9001:2015"],
            "process_zone": "Logistics",
        }
        result = validate_finding_structure(finding)
        assert result.is_valid is False

    def test_invalid_finding_id_format(self):
        finding = {
            "finding_id": "INVALID-01",
            "finding_type": "NCM",
            "description": "Test",
            "standards": ["ISO 9001:2015"],
            "process_zone": "Logistics",
        }
        result = validate_finding_structure(finding)
        assert result.is_valid is False
        assert any("finding_id" in e for e in result.errors)

    def test_invalid_process_zone(self):
        finding = {
            "finding_id": "NCM-01",
            "finding_type": "NCM",
            "description": "Test",
            "standards": ["ISO 9001:2015"],
            "process_zone": "Invalid Zone",
        }
        result = validate_finding_structure(finding)
        assert result.is_valid is False
        assert any("process_zone" in e for e in result.errors)

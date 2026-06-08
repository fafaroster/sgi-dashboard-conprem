"""
Core data model for the SGI Audit Dashboard.

This module defines the fundamental data structures used throughout the
application: finding types, corrective action statuses, process zones,
ISO standards, risk weights, and the Finding dataclass with full
field validation.

Design decisions:
- Enums for type safety on categorical values
- Dataclass for self-documenting, immutable-like structures
- Validation in __post_init__ to guarantee invariants at construction time
- Separate ValidationResult for parser-level error reporting
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


# =============================================================================
# Enums
# =============================================================================


class FindingType(Enum):
    """Classification categories for audit findings.

    Each type carries a different risk weight used in scoring calculations.
    NCM (Major Non-Conformity) is the most severe; OBS (Observation) is
    the least severe.
    """

    NCM = "NCM"   # No Conformidad Mayor (Major Non-Conformity)
    NCm = "NCm"   # No Conformidad Menor (Minor Non-Conformity)
    ODM = "ODM"   # Oportunidad de Mejora (Opportunity for Improvement)
    OBS = "OBS"   # Observación (Observation)


class CorrectiveActionStatus(Enum):
    """Lifecycle states for corrective action plans (CAPA).

    Follows the progression: open → in_progress → completed → verified → closed.
    """

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VERIFIED = "verified"
    CLOSED = "closed"


# =============================================================================
# Constants
# =============================================================================


PROCESS_ZONES: list[str] = [
    "Logistics",
    "Storage Yard",
    "Manufacturing/Prestressing",
    "Lab",
    "Boilers",
    "Aggregates",
    "Steel Storage",
    "Chemical Storage",
    "Document Management",
    "General/Transversal",
]
"""The 10 operational process zones at CONPREM GRAU's facility."""


STANDARDS: list[str] = [
    "ISO 9001:2015",
    "ISO 14001:2015",
    "ISO 45001:2018",
]
"""The three ISO norms covered by the SGI (Integrated Management System)."""


FINDING_WEIGHTS: dict[str, float] = {
    "NCM": 5.0,
    "NCm": 2.0,
    "ODM": 1.0,
    "OBS": 0.5,
}
"""Risk weights per finding type used in Risk_Load_Score calculation."""


# =============================================================================
# Validation patterns (compiled for performance)
# =============================================================================

_FINDING_ID_PATTERN = re.compile(r"^(NCM|NCm|ODM|OBS)-\d{2}$")
"""Valid finding ID format: type prefix followed by a dash and two digits."""

_CLAUSE_REF_PATTERN = re.compile(r"^\d+\.\d+(\.\d+)?$")
"""Valid clause reference format: X.Y or X.Y.Z where X, Y, Z are integers."""

_DESCRIPTION_MAX_LENGTH = 2000
"""Maximum allowed length for finding descriptions."""

_EVIDENCE_MAX_LENGTH = 5000
"""Maximum allowed length for evidence text."""

_RESPONSIBLE_PARTY_MAX_LENGTH = 150
"""Maximum allowed length for the responsible party name."""

_COST_MIN = 0.01
"""Minimum value for estimated mitigation cost (inclusive)."""

_COST_MAX = 999_999_999.99
"""Maximum value for estimated mitigation cost (inclusive)."""


# =============================================================================
# Finding Dataclass
# =============================================================================


@dataclass
class Finding:
    """Represents a single audit finding with all associated metadata.

    Required fields must always be present and valid. Optional fields
    support future CAPA tracking and may be None when not yet populated.

    Validation is enforced in __post_init__ — any constraint violation
    raises a ValueError with a descriptive message.

    Attributes:
        finding_id: Unique identifier (e.g., "NCM-01", "OBS-05").
        finding_type: Classification category from FindingType enum.
        description: Detailed finding description (max 2000 chars).
        standards: One or more ISO standards affected by this finding.
        process_zone: Operational area where the finding was identified.
        clause_ref: ISO clause reference in "X.Y" or "X.Y.Z" format.
        evidence: Supporting evidence text (max 5000 chars).
        is_transversal: True for HTS (systemic transversal) findings.
        responsible_party: Person assigned to resolve (max 150 chars).
        deadline: Target resolution date in ISO 8601 format.
        estimated_mitigation_cost: Estimated cost (0.01–999,999,999.99).
        corrective_action_status: Current CAPA lifecycle state.
    """

    # Required fields
    finding_id: str
    finding_type: FindingType
    description: str
    standards: list[str]
    process_zone: str

    # Optional fields (may be absent in source document)
    clause_ref: Optional[str] = None
    evidence: Optional[str] = None
    is_transversal: bool = False

    # Future extensibility fields (Requirement 16)
    responsible_party: Optional[str] = None
    deadline: Optional[date] = None
    estimated_mitigation_cost: Optional[float] = None
    corrective_action_status: Optional[CorrectiveActionStatus] = None

    def __post_init__(self) -> None:
        """Validate all fields after dataclass initialization.

        Raises:
            ValueError: If any field violates its format or range constraint.
        """
        self._validate_finding_id()
        self._validate_description()
        self._validate_standards()
        self._validate_process_zone()
        self._validate_clause_ref()
        self._validate_evidence()
        self._validate_responsible_party()
        self._validate_deadline()
        self._validate_estimated_mitigation_cost()
        self._validate_corrective_action_status()

    # -------------------------------------------------------------------------
    # Private validation methods
    # -------------------------------------------------------------------------

    def _validate_finding_id(self) -> None:
        """Validate finding_id matches pattern (NCM|NCm|ODM|OBS)-\\d{2}."""
        if not isinstance(self.finding_id, str):
            raise ValueError(
                f"finding_id must be a string, got {type(self.finding_id).__name__}"
            )
        if not _FINDING_ID_PATTERN.match(self.finding_id):
            raise ValueError(
                f"finding_id '{self.finding_id}' does not match required pattern "
                f"'(NCM|NCm|ODM|OBS)-\\d{{2}}' (e.g., 'NCM-01', 'OBS-05')"
            )

    def _validate_description(self) -> None:
        """Validate description is non-empty and within length limit."""
        if not isinstance(self.description, str):
            raise ValueError(
                f"description must be a string, got {type(self.description).__name__}"
            )
        if not self.description.strip():
            raise ValueError("description must not be empty or whitespace-only")
        if len(self.description) > _DESCRIPTION_MAX_LENGTH:
            raise ValueError(
                f"description exceeds maximum length of {_DESCRIPTION_MAX_LENGTH} "
                f"characters (got {len(self.description)})"
            )

    def _validate_standards(self) -> None:
        """Validate standards is a non-empty list of known ISO norms."""
        if not isinstance(self.standards, list) or not self.standards:
            raise ValueError("standards must be a non-empty list")
        for std in self.standards:
            if std not in STANDARDS:
                raise ValueError(
                    f"standard '{std}' is not recognized. "
                    f"Valid standards: {STANDARDS}"
                )

    def _validate_process_zone(self) -> None:
        """Validate process_zone is in the defined PROCESS_ZONES list."""
        if self.process_zone not in PROCESS_ZONES:
            raise ValueError(
                f"process_zone '{self.process_zone}' is not recognized. "
                f"Valid zones: {PROCESS_ZONES}"
            )

    def _validate_clause_ref(self) -> None:
        """Validate clause_ref matches pattern \\d+\\.\\d+(\\.\\d+)? if set."""
        if self.clause_ref is None:
            return
        if not isinstance(self.clause_ref, str):
            raise ValueError(
                f"clause_ref must be a string or None, "
                f"got {type(self.clause_ref).__name__}"
            )
        if not _CLAUSE_REF_PATTERN.match(self.clause_ref):
            raise ValueError(
                f"clause_ref '{self.clause_ref}' does not match required pattern "
                f"'\\d+.\\d+(.\\d+)?' (e.g., '4.4', '9.1.2')"
            )

    def _validate_evidence(self) -> None:
        """Validate evidence is within length limit if set."""
        if self.evidence is None:
            return
        if not isinstance(self.evidence, str):
            raise ValueError(
                f"evidence must be a string or None, "
                f"got {type(self.evidence).__name__}"
            )
        if len(self.evidence) > _EVIDENCE_MAX_LENGTH:
            raise ValueError(
                f"evidence exceeds maximum length of {_EVIDENCE_MAX_LENGTH} "
                f"characters (got {len(self.evidence)})"
            )

    def _validate_responsible_party(self) -> None:
        """Validate responsible_party is within length limit if set."""
        if self.responsible_party is None:
            return
        if not isinstance(self.responsible_party, str):
            raise ValueError(
                f"responsible_party must be a string or None, "
                f"got {type(self.responsible_party).__name__}"
            )
        if len(self.responsible_party) > _RESPONSIBLE_PARTY_MAX_LENGTH:
            raise ValueError(
                f"responsible_party exceeds maximum length of "
                f"{_RESPONSIBLE_PARTY_MAX_LENGTH} characters "
                f"(got {len(self.responsible_party)})"
            )

    def _validate_deadline(self) -> None:
        """Validate deadline is a valid date object if set.

        Accepts both date objects and ISO 8601 strings (YYYY-MM-DD).
        If a string is provided, it is parsed and stored as a date object.
        """
        if self.deadline is None:
            return

        if isinstance(self.deadline, str):
            # Attempt to parse ISO 8601 date string
            try:
                parsed_date = datetime.strptime(self.deadline, "%Y-%m-%d").date()
                # Replace string with actual date object
                object.__setattr__(self, "deadline", parsed_date)
            except ValueError:
                raise ValueError(
                    f"deadline '{self.deadline}' is not a valid ISO 8601 date. "
                    f"Expected format: YYYY-MM-DD (e.g., '2025-06-30')"
                )
        elif not isinstance(self.deadline, date):
            raise ValueError(
                f"deadline must be a date object, ISO 8601 string, or None, "
                f"got {type(self.deadline).__name__}"
            )

    def _validate_estimated_mitigation_cost(self) -> None:
        """Validate cost is within range [0.01, 999,999,999.99] if set."""
        if self.estimated_mitigation_cost is None:
            return

        if not isinstance(self.estimated_mitigation_cost, (int, float)):
            raise ValueError(
                f"estimated_mitigation_cost must be a numeric value or None, "
                f"got {type(self.estimated_mitigation_cost).__name__}"
            )

        cost = float(self.estimated_mitigation_cost)
        if cost < _COST_MIN or cost > _COST_MAX:
            raise ValueError(
                f"estimated_mitigation_cost {cost} is out of valid range "
                f"[{_COST_MIN}, {_COST_MAX}]"
            )

    def _validate_corrective_action_status(self) -> None:
        """Validate corrective_action_status is a valid enum value if set."""
        if self.corrective_action_status is None:
            return

        if isinstance(self.corrective_action_status, str):
            # Attempt to coerce string to enum
            try:
                status = CorrectiveActionStatus(self.corrective_action_status)
                object.__setattr__(self, "corrective_action_status", status)
            except ValueError:
                valid_values = [s.value for s in CorrectiveActionStatus]
                raise ValueError(
                    f"corrective_action_status '{self.corrective_action_status}' "
                    f"is not valid. Allowed values: {valid_values}"
                )
        elif not isinstance(self.corrective_action_status, CorrectiveActionStatus):
            raise ValueError(
                f"corrective_action_status must be a CorrectiveActionStatus enum, "
                f"string, or None, got "
                f"{type(self.corrective_action_status).__name__}"
            )


# =============================================================================
# ValidationResult Dataclass
# =============================================================================


@dataclass
class ValidationResult:
    """Result of validating a finding's structure during parsing.

    Used by the parser module to collect and report field-level
    validation errors without raising exceptions immediately. This
    allows batch processing of multiple findings with error aggregation.

    Attributes:
        is_valid: True if all validation checks passed.
        errors: List of human-readable error descriptions.
        line_number: Source file line number where the finding starts.
        section_heading: The Markdown section heading containing the finding.
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    line_number: Optional[int] = None
    section_heading: Optional[str] = None

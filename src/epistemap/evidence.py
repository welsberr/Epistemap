from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .confidence import ConfidenceAssessment


EvidenceStance = Literal["support", "challenge", "neutral", "revision"]
SourceFamilyDependence = Literal["record_only", "independent", "dependent", "discounted"]


def deterministic_json(payload: Any) -> str:
    """Return canonical JSON for hashes and cross-repository fixture checks."""

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def deterministic_hash(payload: Any) -> str:
    return hashlib.sha256(deterministic_json(payload).encode("utf-8")).hexdigest()


def derive_evidence_identity(
    *,
    explicit_evidence_id: str = "",
    artifact_id: str = "",
    fragment_id: str = "",
    graph_edge_id: str = "",
    provenance: Mapping[str, Any] | None = None,
) -> str:
    """Derive a stable evidence identity without assigning evidential meaning."""

    if explicit_evidence_id:
        return explicit_evidence_id
    if artifact_id and fragment_id:
        digest = deterministic_hash({"artifact_id": artifact_id, "fragment_id": fragment_id})
        return f"evidence:artifact-fragment:{digest}"
    if graph_edge_id:
        return f"evidence:graph-edge:{graph_edge_id}"
    digest = deterministic_hash(provenance or {})
    return f"evidence:provenance:{digest}"


class EvidenceReference(BaseModel):
    schema_version: str = "1.0"
    source_record_id: str = ""
    artifact_id: str = ""
    fragment_id: str = ""
    graph_edge_id: str = ""
    source_family_id: str = ""
    uri: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceWeightingPolicy(BaseModel):
    schema_version: str = "1.0"
    policy_id: str
    method_name: str
    method_version: str
    missing_weight_default: float | None = Field(default=None, ge=0.0)
    source_family_dependence: SourceFamilyDependence = "record_only"
    source_family_discount: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("missing_weight_default", "source_family_discount")
    @classmethod
    def _finite_optional_float(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("weighting policy floats must be finite")
        return value

    @model_validator(mode="after")
    def _versioned_policy(self) -> "EvidenceWeightingPolicy":
        if not self.policy_id or not self.method_name or not self.method_version:
            raise ValueError("weighting policy must include policy_id, method_name, and method_version")
        return self


class EvidenceUnit(BaseModel):
    schema_version: str = "1.0"
    unit_id: str = ""
    subject_claim_id: str
    stance: EvidenceStance
    references: list[EvidenceReference] = Field(default_factory=list)
    source_family_ids: list[str] = Field(default_factory=list)
    input_assessments: list[ConfidenceAssessment] = Field(default_factory=list)
    raw_weight: float | None = Field(default=None, ge=0.0)
    effective_weight: float | None = Field(default=None, ge=0.0)
    deduplication_key: str = ""
    deduplication_rationale: str = ""
    policy_id: str
    method_name: str
    method_version: str
    revision_of_unit_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("raw_weight", "effective_weight")
    @classmethod
    def _finite_optional_weight(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("evidence weights must be finite")
        return value

    @model_validator(mode="after")
    def _coherent_unit(self) -> "EvidenceUnit":
        if not self.subject_claim_id:
            raise ValueError("evidence unit must include subject_claim_id")
        if not self.policy_id or not self.method_name or not self.method_version:
            raise ValueError("evidence unit must include policy_id, method_name, and method_version")
        if self.stance == "revision" and not self.revision_of_unit_ids:
            raise ValueError("revision evidence must identify revised evidence unit ids")
        if self.stance != "revision" and self.revision_of_unit_ids:
            raise ValueError("revision_of_unit_ids are only valid for revision evidence")
        if not self.unit_id:
            ref = self.references[0] if self.references else EvidenceReference(metadata=self.metadata)
            self.unit_id = derive_evidence_identity(
                artifact_id=ref.artifact_id,
                fragment_id=ref.fragment_id,
                graph_edge_id=ref.graph_edge_id,
                provenance={
                    "subject_claim_id": self.subject_claim_id,
                    "stance": self.stance,
                    "references": [item.model_dump(mode="json") for item in self.references],
                    "metadata": self.metadata,
                },
            )
        if not self.deduplication_key:
            self.deduplication_key = self.unit_id
        return self

    def deterministic_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def deterministic_json(self) -> str:
        return deterministic_json(self.deterministic_payload())

    def content_hash(self) -> str:
        return deterministic_hash(self.deterministic_payload())


class EvidenceLedgerDiagnostic(BaseModel):
    schema_version: str = "1.0"
    severity: Literal["info", "warning", "error"]
    code: str
    message: str
    unit_id: str = ""
    subject_claim_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceLedger(BaseModel):
    schema_version: str = "1.0"
    ledger_id: str
    subject_claim_ids: list[str] = Field(default_factory=list)
    units: list[EvidenceUnit] = Field(default_factory=list)
    weighting_policy: EvidenceWeightingPolicy
    diagnostics: list[EvidenceLedgerDiagnostic] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_units(self) -> "EvidenceLedger":
        seen: set[str] = set()
        unit_ids = {unit.unit_id for unit in self.units}
        declared_subjects = set(self.subject_claim_ids)
        for unit in self.units:
            if unit.unit_id in seen:
                raise ValueError(f"duplicate evidence unit id: {unit.unit_id}")
            seen.add(unit.unit_id)
            if declared_subjects and unit.subject_claim_id not in declared_subjects:
                raise ValueError(f"evidence unit references undeclared subject: {unit.subject_claim_id}")
            for revised_id in unit.revision_of_unit_ids:
                if revised_id not in unit_ids:
                    raise ValueError(f"revision evidence references missing unit id: {revised_id}")
        return self

    def deterministic_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def deterministic_json(self) -> str:
        return deterministic_json(self.deterministic_payload())

    def content_hash(self) -> str:
        return deterministic_hash(self.deterministic_payload())

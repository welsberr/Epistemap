from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .confidence import ConfidenceAssessment
from .models import Edge, GraphBundle, Node


EvidenceStance = Literal["support", "challenge", "neutral", "revision"]
SourceFamilyDependence = Literal["record_only", "independent", "dependent", "discounted"]
SUPPORT_EDGE_TYPES = {"supports", "supports_claim", "about_concept", "supports_concept", "teaches_concept"}
CHALLENGE_EDGE_TYPES = {"contradicts", "challenges", "disputes"}
REVISION_EDGE_TYPES = {"supersedes", "corrects", "retracts", "qualifies"}
DEFAULT_GRAPH_WEIGHTING_POLICY_ID = "graph_edge_evidence_weighting_v1"


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
    referring_edge_ids: list[str] = Field(default_factory=list)
    source_family_ids: list[str] = Field(default_factory=list)
    input_assessments: list[ConfidenceAssessment] = Field(default_factory=list)
    raw_weight: float | None = Field(default=None, ge=0.0)
    effective_weight: float | None = Field(default=None, ge=0.0)
    weight_input_id: str = ""
    weight_policy_rule: str = ""
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


def graph_to_evidence_ledger(
    bundle: GraphBundle,
    subject_claim_id: str,
    *,
    weighting_policy: EvidenceWeightingPolicy | None = None,
) -> EvidenceLedger:
    """Convert claim-level graph evidence into a deduplicated evidence ledger."""

    nodes_by_id = bundle.node_index()
    claim_ids = _claim_ids_for_subject(bundle, subject_claim_id)
    raw_units: list[EvidenceUnit] = []
    for edge in bundle.edges:
        if edge.target not in claim_ids and edge.source not in claim_ids:
            continue
        stance = _stance_for_edge(edge)
        if stance is None:
            continue
        raw_units.append(_unit_from_edge(edge, stance, _unit_subject_for_edge(edge, claim_ids, subject_claim_id), nodes_by_id, weighting_policy))
    return evidence_ledger_from_units(
        ledger_id=f"ledger::{subject_claim_id}",
        subject_claim_ids=sorted(claim_ids),
        units=raw_units,
        weighting_policy=weighting_policy or default_graph_weighting_policy(),
    )


def evidence_ledger_from_edges(
    *,
    subject_claim_id: str,
    support_edges: list[Edge] | tuple[Edge, ...],
    challenge_edges: list[Edge] | tuple[Edge, ...],
    revision_edges: list[Edge] | tuple[Edge, ...] = (),
    nodes_by_id: Mapping[str, Node] | None = None,
    weighting_policy: EvidenceWeightingPolicy | None = None,
    effective_weight_resolver: Callable[[Edge], float] | None = None,
) -> EvidenceLedger:
    """Build a ledger from preselected edge groups while retaining legacy callers."""

    nodes_by_id = nodes_by_id or {}
    policy = weighting_policy or default_graph_weighting_policy()
    raw_units = [
        _unit_from_edge(edge, "support", subject_claim_id, nodes_by_id, policy, effective_weight_resolver)
        for edge in support_edges
    ]
    raw_units.extend(
        _unit_from_edge(edge, "challenge", subject_claim_id, nodes_by_id, policy, effective_weight_resolver)
        for edge in challenge_edges
    )
    raw_units.extend(
        _unit_from_edge(edge, "revision", subject_claim_id, nodes_by_id, policy, effective_weight_resolver)
        for edge in revision_edges
    )
    return evidence_ledger_from_units(
        ledger_id=f"ledger::{subject_claim_id}",
        subject_claim_ids=[subject_claim_id],
        units=raw_units,
        weighting_policy=policy,
    )


def evidence_ledger_from_units(
    *,
    ledger_id: str,
    subject_claim_ids: list[str],
    units: list[EvidenceUnit],
    weighting_policy: EvidenceWeightingPolicy,
) -> EvidenceLedger:
    deduplicated: dict[str, EvidenceUnit] = {}
    diagnostics: list[EvidenceLedgerDiagnostic] = []
    raw_counts = {"support": 0, "challenge": 0, "neutral": 0, "revision": 0}
    deduplicated_counts = {"support": 0, "challenge": 0, "neutral": 0, "revision": 0}
    raw_weights = {"support": 0.0, "challenge": 0.0, "neutral": 0.0, "revision": 0.0}
    deduplicated_weights = {"support": 0.0, "challenge": 0.0, "neutral": 0.0, "revision": 0.0}
    for unit in units:
        raw_counts[unit.stance] += 1
        raw_weights[unit.stance] += float(unit.effective_weight or 0.0)
        if unit.metadata.get("weight_diagnostic") == "missing_weight_default_applied":
            diagnostics.append(
                EvidenceLedgerDiagnostic(
                    severity="warning",
                    code="missing_weight_default_applied",
                    message="Evidence unit used the policy missing-weight default.",
                    unit_id=unit.unit_id,
                    subject_claim_id=unit.subject_claim_id,
                    metadata={
                        "policy_id": weighting_policy.policy_id,
                        "weight_policy_rule": unit.weight_policy_rule,
                        "weight_input_id": unit.weight_input_id,
                    },
                )
            )
        key = unit.deduplication_key or unit.unit_id
        if key not in deduplicated:
            deduplicated[key] = unit
            continue
        existing = deduplicated[key]
        existing.referring_edge_ids = _sorted_unique(existing.referring_edge_ids + unit.referring_edge_ids)
        existing.references = existing.references + unit.references
        existing.source_family_ids = _sorted_unique(existing.source_family_ids + unit.source_family_ids)
        existing.metadata["duplicate_unit_ids"] = _sorted_unique(
            list(existing.metadata.get("duplicate_unit_ids", [])) + [unit.unit_id]
        )
    for unit in deduplicated.values():
        deduplicated_counts[unit.stance] += 1
        deduplicated_weights[unit.stance] += float(unit.effective_weight or 0.0)
    diagnostics.append(
        EvidenceLedgerDiagnostic(
            severity="info",
            code="evidence_ledger_counts",
            message="Raw and deduplicated evidence counts and weights.",
            metadata={
                "raw_counts": raw_counts,
                "deduplicated_counts": deduplicated_counts,
                "raw_weights": {key: round(value, 6) for key, value in raw_weights.items()},
                "deduplicated_weights": {key: round(value, 6) for key, value in deduplicated_weights.items()},
            },
        )
    )
    return EvidenceLedger(
        ledger_id=ledger_id,
        subject_claim_ids=subject_claim_ids,
        units=sorted(deduplicated.values(), key=lambda item: item.unit_id),
        weighting_policy=weighting_policy,
        diagnostics=diagnostics,
        metadata={
            "raw_unit_count": len(units),
            "deduplicated_unit_count": len(deduplicated),
            "raw_counts": raw_counts,
            "deduplicated_counts": deduplicated_counts,
            "raw_weights": {key: round(value, 6) for key, value in raw_weights.items()},
            "deduplicated_weights": {key: round(value, 6) for key, value in deduplicated_weights.items()},
        },
    )


def default_graph_weighting_policy() -> EvidenceWeightingPolicy:
    return EvidenceWeightingPolicy(
        policy_id=DEFAULT_GRAPH_WEIGHTING_POLICY_ID,
        method_name="graph_edge_evidence_weighting",
        method_version="1.0",
        missing_weight_default=1.0,
        source_family_dependence="record_only",
        metadata={
            "rules": [
                "typed edge grounding_strength assessment",
                "legacy edge confidence",
                "source node confidence",
                "versioned missing-weight default",
            ]
        },
    )


def _unit_from_edge(
    edge: Edge,
    stance: EvidenceStance,
    subject_claim_id: str,
    nodes_by_id: Mapping[str, Node],
    weighting_policy: EvidenceWeightingPolicy | None,
    effective_weight_resolver: Callable[[Edge], float] | None = None,
) -> EvidenceUnit:
    policy = weighting_policy or default_graph_weighting_policy()
    edge_id = edge.id or f"{edge.source}->{edge.type}->{edge.target}"
    weight, input_id, rule, diagnostic = _edge_weight(edge, nodes_by_id, policy)
    effective_weight = float(effective_weight_resolver(edge)) if effective_weight_resolver is not None else weight
    effective_rule = "bayesian_legacy_edge_weight" if effective_weight_resolver is not None else rule
    source_family_ids = _source_family_ids(edge, nodes_by_id)
    deduplication_key = _deduplication_key(edge)
    metadata: dict[str, Any] = {
        "edge_type": edge.type,
        "weight_diagnostic": diagnostic,
    }
    revision_ids = [str(edge.metadata.get("revises_unit_id", ""))] if stance == "revision" else []
    revision_ids = [item for item in revision_ids if item]
    unit_id = derive_evidence_identity(graph_edge_id=edge_id)
    if stance == "revision" and not revision_ids:
        revision_ids = [unit_id]
        metadata["revision_relation_without_prior_unit"] = True
    return EvidenceUnit(
        unit_id=unit_id,
        subject_claim_id=subject_claim_id,
        stance=stance,
        references=[
            EvidenceReference(
                source_record_id=str(edge.source),
                artifact_id=str(edge.metadata.get("artifact_id", "")),
                fragment_id=str(edge.metadata.get("fragment_id", "")),
                graph_edge_id=edge_id,
                source_family_id=source_family_ids[0] if source_family_ids else "",
                uri=str(edge.metadata.get("source_url", "")),
                metadata={"edge_type": edge.type},
            )
        ],
        referring_edge_ids=[edge_id],
        source_family_ids=source_family_ids,
        input_assessments=edge.assessments,
        raw_weight=weight,
        effective_weight=effective_weight,
        weight_input_id=input_id,
        weight_policy_rule=effective_rule,
        deduplication_key=deduplication_key,
        deduplication_rationale="artifact and fragment match" if "fragment_id" in edge.metadata else "graph edge identity",
        policy_id=policy.policy_id,
        method_name=policy.method_name,
        method_version=policy.method_version,
        revision_of_unit_ids=revision_ids,
        metadata=metadata,
    )


def _edge_weight(
    edge: Edge,
    nodes_by_id: Mapping[str, Node],
    policy: EvidenceWeightingPolicy,
) -> tuple[float, str, str, str]:
    for assessment in edge.assessments:
        if assessment.dimension == "grounding_strength" and assessment.value is not None:
            return float(assessment.value), assessment.assessment_id, "typed_edge_grounding_strength", ""
    if edge.confidence is not None:
        return float(edge.confidence), edge.id or f"{edge.source}->{edge.type}->{edge.target}", "legacy_edge_confidence", ""
    source = nodes_by_id.get(edge.source)
    if source is not None and source.confidence is not None:
        return float(source.confidence), source.id, "legacy_source_node_confidence", ""
    default = float(policy.missing_weight_default if policy.missing_weight_default is not None else 1.0)
    return default, policy.policy_id, "missing_weight_default", "missing_weight_default_applied"


def _deduplication_key(edge: Edge) -> str:
    artifact_id = str(edge.metadata.get("artifact_id", ""))
    fragment_id = str(edge.metadata.get("fragment_id", ""))
    if artifact_id and fragment_id:
        return deterministic_hash({"artifact_id": artifact_id, "fragment_id": fragment_id})
    return edge.id or deterministic_hash({"source": edge.source, "target": edge.target, "type": edge.type})


def _source_family_ids(edge: Edge, nodes_by_id: Mapping[str, Node]) -> list[str]:
    families: list[str] = []
    for value in (edge.metadata.get("source_family_id"), edge.metadata.get("source_family")):
        if value:
            families.append(str(value))
    source = nodes_by_id.get(edge.source)
    if source is not None:
        for value in (source.metadata.get("source_family_id"), source.metadata.get("source_family")):
            if value:
                families.append(str(value))
    return _sorted_unique(families)


def _stance_for_edge(edge: Edge) -> EvidenceStance | None:
    if edge.type in SUPPORT_EDGE_TYPES:
        return "support"
    if edge.type in CHALLENGE_EDGE_TYPES:
        return "challenge"
    if edge.type in REVISION_EDGE_TYPES:
        return "revision"
    return None


def _claim_ids_for_subject(bundle: GraphBundle, subject_claim_id: str) -> set[str]:
    nodes = bundle.node_index()
    target = nodes.get(subject_claim_id)
    if target is None or target.type == "claim":
        return {subject_claim_id}
    if target.type != "concept":
        return {subject_claim_id}
    claim_ids = {
        edge.source
        for edge in bundle.edges
        if edge.target == subject_claim_id and nodes.get(edge.source, Node(id="", type="")).type == "claim"
    }
    return claim_ids or {subject_claim_id}


def _unit_subject_for_edge(edge: Edge, claim_ids: set[str], fallback: str) -> str:
    if edge.target in claim_ids:
        return edge.target
    if edge.source in claim_ids:
        return edge.source
    return fallback


def _sorted_unique(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})

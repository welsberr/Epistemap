from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ConfidenceDimension = Literal[
    "extraction_fidelity",
    "identity_resolution",
    "grounding_strength",
    "source_reliability",
    "evidential_support",
    "reviewer_endorsement",
    "response_correctness",
    "evidence_coverage",
]

STANDARD_CONFIDENCE_DIMENSIONS: set[str] = set(ConfidenceDimension.__args__)

ConfidenceBand = Literal[
    "unknown",
    "very_low",
    "low",
    "moderate",
    "high",
    "very_high",
]


class ConfidenceInterval(BaseModel):
    level: float = Field(ge=0.0, le=1.0)
    lower: float = Field(ge=0.0, le=1.0)
    upper: float = Field(ge=0.0, le=1.0)
    method: str

    @field_validator("level", "lower", "upper")
    @classmethod
    def _finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("interval values must be finite")
        return value

    @model_validator(mode="after")
    def _bounds_ordered(self) -> "ConfidenceInterval":
        if self.lower > self.upper:
            raise ValueError("interval.lower must be <= interval.upper")
        return self


class AssessmentMethodRef(BaseModel):
    name: str
    version: str
    policy_id: str = ""


class ConfidenceAssessment(BaseModel):
    schema_version: str = "1.0"
    assessment_id: str
    subject_id: str
    dimension: str
    value: float | None = Field(default=None, ge=0.0, le=1.0)
    band: ConfidenceBand = "unknown"
    interval: ConfidenceInterval | None = None
    assessor_id: str = ""
    method: AssessmentMethodRef
    basis_record_ids: list[str] = Field(default_factory=list)
    source_family_ids: list[str] = Field(default_factory=list)
    basis_hash: str = ""
    rationale: str = ""
    valid_at: str = ""
    recorded_at: str
    supersedes_assessment_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("value")
    @classmethod
    def _finite_value(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("assessment value must be finite")
        return value

    @field_validator("dimension")
    @classmethod
    def _known_or_namespaced_dimension(cls, value: str) -> str:
        if value in STANDARD_CONFIDENCE_DIMENSIONS or ":" in value:
            return value
        raise ValueError(f"unknown confidence dimension: {value}")

    @field_validator("recorded_at")
    @classmethod
    def _recorded_at_iso8601(cls, value: str) -> str:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("recorded_at must be an ISO-8601 timestamp") from exc
        return value

    @model_validator(mode="after")
    def _coherent_value_band_interval(self) -> "ConfidenceAssessment":
        if self.value is None and self.band != "unknown":
            raise ValueError('band must be "unknown" when value is None')
        if self.value is not None and self.interval is not None:
            if self.value < self.interval.lower or self.value > self.interval.upper:
                raise ValueError("assessment value must lie inside interval")
        return self


def assessments_for(
    subject: Any,
    dimension: str | None = None,
) -> list[ConfidenceAssessment]:
    assessments = list(getattr(subject, "assessments", []) or [])
    if dimension is None:
        return assessments
    return [assessment for assessment in assessments if assessment.dimension == dimension]


def active_assessments(
    subject: Any,
    dimension: str | None = None,
) -> list[ConfidenceAssessment]:
    assessments = assessments_for(subject, dimension)
    superseded_ids = {item.supersedes_assessment_id for item in assessments if item.supersedes_assessment_id}
    return [item for item in assessments if item.assessment_id not in superseded_ids]


def latest_assessment(
    subject: Any,
    dimension: str | None = None,
) -> ConfidenceAssessment | None:
    assessments = active_assessments(subject, dimension)
    if not assessments:
        return None
    return max(assessments, key=lambda item: datetime.fromisoformat(item.recorded_at.replace("Z", "+00:00")))


def confidence_band(value: float | None) -> ConfidenceBand:
    if value is None:
        return "unknown"
    if value < 0.2:
        return "very_low"
    if value < 0.4:
        return "low"
    if value < 0.7:
        return "moderate"
    if value < 0.9:
        return "high"
    return "very_high"


def validate_assessment_lineage(
    assessments: Iterable[ConfidenceAssessment],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[str] = set()
    all_ids = set()
    for assessment in assessments:
        if assessment.assessment_id in seen:
            findings.append(
                {
                    "severity": "error",
                    "code": "duplicate_assessment_id",
                    "assessment_id": assessment.assessment_id,
                    "message": "Assessment id appears more than once.",
                }
            )
        seen.add(assessment.assessment_id)
        all_ids.add(assessment.assessment_id)
        if not assessment.method.name or not assessment.method.version:
            findings.append(
                {
                    "severity": "error",
                    "code": "missing_assessment_method",
                    "assessment_id": assessment.assessment_id,
                    "message": "Assessment method must include name and version.",
                }
            )
    for assessment in assessments:
        supersedes = assessment.supersedes_assessment_id
        if supersedes and supersedes not in all_ids:
            findings.append(
                {
                    "severity": "error",
                    "code": "dangling_assessment_supersession",
                    "assessment_id": assessment.assessment_id,
                    "supersedes_assessment_id": supersedes,
                    "message": "Assessment supersedes an id that is not present in the bundle.",
                }
            )
    return findings

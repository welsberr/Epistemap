from __future__ import annotations

import pytest
from pydantic import ValidationError

from epistemap import (
    AssessmentMethodRef,
    AssessmentValidationPolicy,
    ConfidenceAssessment,
    ConfidenceInterval,
    Edge,
    GraphBundle,
    Node,
    active_assessments,
    assessments_for,
    confidence_band,
    latest_assessment,
    to_cytoscape_json,
    validate_assessment_readiness,
)


def _method() -> AssessmentMethodRef:
    return AssessmentMethodRef(name="unit-test", version="1")


def test_confidence_assessment_validates_dimension_time_band_and_interval() -> None:
    assessment = ConfidenceAssessment(
        assessment_id="assess::1",
        subject_id="claim::a",
        dimension="reviewer_endorsement",
        value=0.0,
        band="very_low",
        interval=ConfidenceInterval(level=0.95, lower=0.0, upper=0.1, method="exact-zero"),
        method=_method(),
        recorded_at="2026-07-25T12:00:00Z",
    )

    assert assessment.value == 0.0
    assert confidence_band(assessment.value) == "very_low"

    with pytest.raises(ValidationError):
        ConfidenceAssessment(
            assessment_id="assess::bad-dimension",
            subject_id="claim::a",
            dimension="trust",
            method=_method(),
            recorded_at="2026-07-25T12:00:00Z",
        )

    with pytest.raises(ValidationError):
        ConfidenceAssessment(
            assessment_id="assess::bad-band",
            subject_id="claim::a",
            dimension="example:custom",
            band="low",
            method=_method(),
            recorded_at="2026-07-25T12:00:00Z",
        )

    with pytest.raises(ValidationError):
        ConfidenceAssessment(
            assessment_id="assess::bad-time",
            subject_id="claim::a",
            dimension="example:custom",
            method=_method(),
            recorded_at="not-a-time",
        )


def test_assessment_helpers_keep_superseded_records_queryable() -> None:
    first = ConfidenceAssessment(
        assessment_id="assess::old",
        subject_id="claim::a",
        dimension="grounding_strength",
        value=0.4,
        band="moderate",
        method=_method(),
        recorded_at="2026-07-25T12:00:00Z",
    )
    second = ConfidenceAssessment(
        assessment_id="assess::new",
        subject_id="claim::a",
        dimension="grounding_strength",
        value=0.8,
        band="high",
        method=_method(),
        recorded_at="2026-07-25T13:00:00Z",
        supersedes_assessment_id="assess::old",
    )
    node = Node(id="claim::a", type="claim", assessments=[first, second])

    assert assessments_for(node, "grounding_strength") == [first, second]
    assert active_assessments(node, "grounding_strength") == [second]
    assert latest_assessment(node, "grounding_strength") == second


def test_validation_checks_assessment_lineage_and_legacy_mapping_policy() -> None:
    assessment = ConfidenceAssessment(
        assessment_id="assess::same",
        subject_id="claim::a",
        dimension="reviewer_endorsement",
        value=0.75,
        band="high",
        method=_method(),
        recorded_at="2026-07-25T12:00:00Z",
    )
    bundle = GraphBundle(
        graph_id="confidence-contract",
        nodes=[
            Node(id="claim::a", type="claim", title="Claim", confidence=0.75, assessments=[assessment]),
            Node(id="source::s", type="source", title="Source"),
        ],
        edges=[
            Edge(
                source="source::s",
                target="claim::a",
                type="supports",
                evidence_ids=["source::s"],
                metadata={"available_at": "2026-07-25"},
                assessments=[assessment],
            )
        ],
    )

    report = validate_assessment_readiness(
        bundle,
        AssessmentValidationPolicy(require_temporal_metadata_for_temporal_edges=False),
    )
    codes = {finding["code"] for finding in report["findings"]}

    assert "duplicate_assessment_id" in codes
    assert "legacy_confidence_without_mapping_policy" in codes

    bundle.metadata["legacy_confidence_mapping_policy"] = {
        "legacy_node_confidence": "reviewer_endorsement compatibility copy"
    }
    report = validate_assessment_readiness(
        bundle,
        AssessmentValidationPolicy(require_temporal_metadata_for_temporal_edges=False),
    )
    codes = {finding["code"] for finding in report["findings"]}

    assert "legacy_confidence_without_mapping_policy" not in codes


def test_exporters_include_typed_assessments_without_requiring_legacy_confidence() -> None:
    assessment = ConfidenceAssessment(
        assessment_id="assess::edge",
        subject_id="source::s--supports--claim::a",
        dimension="evidential_support",
        value=0.8,
        band="high",
        method=_method(),
        basis_record_ids=["source::s"],
        recorded_at="2026-07-25T12:00:00Z",
    )
    bundle = GraphBundle(
        graph_id="typed-only",
        nodes=[Node(id="claim::a", type="claim")],
        edges=[Edge(source="source::s", target="claim::a", type="supports", assessments=[assessment])],
    )

    assert bundle.model_dump_legacy()["edges"][0]["assessments"][0]["dimension"] == "evidential_support"
    assert to_cytoscape_json(bundle)["edges"][0]["data"]["assessments"][0]["assessment_id"] == "assess::edge"

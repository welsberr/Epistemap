from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from epistemap import (
    AssessmentMethodRef,
    ConfidenceAssessment,
    ConfidenceInterval,
    Edge,
    GraphBundle,
    Node,
    active_assessments,
    latest_assessment,
    load_graph_bundle,
    to_cytoscape_json,
    to_jsonld,
    validate_assessment_readiness,
    write_graph_bundle,
)


def _method() -> AssessmentMethodRef:
    return AssessmentMethodRef(name="fixture_method", version="1.0", policy_id="fixture_policy")


def _assessment(assessment_id: str, subject_id: str, value: float | None = 0.8) -> ConfidenceAssessment:
    return ConfidenceAssessment(
        assessment_id=assessment_id,
        subject_id=subject_id,
        dimension="grounding_strength",
        value=value,
        band="unknown" if value is None else "high",
        interval=None
        if value is None
        else ConfidenceInterval(level=0.95, lower=0.2, upper=0.9, method="fixture_normal_approx"),
        method=_method(),
        basis_record_ids=["basis::1"],
        recorded_at="2026-07-25T12:00:00+00:00",
    )


def test_legacy_missing_and_explicit_zero_survive_round_trip(tmp_path):
    path = tmp_path / "graph.json"
    bundle = GraphBundle(
        graph_id="confidence_fixture",
        nodes=[
            Node(id="claim::missing", type="claim"),
            Node(id="claim::zero", type="claim", confidence=0.0),
        ],
        edges=[
            Edge(source="claim::missing", target="claim::zero", type="related_to"),
            Edge(source="claim::zero", target="claim::missing", type="supports_claim", confidence=0.0),
        ],
    )

    write_graph_bundle(bundle, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "confidence" not in payload["nodes"][0]
    assert payload["nodes"][1]["confidence"] == 0.0
    assert "confidence" not in payload["edges"][0]
    assert payload["edges"][1]["confidence"] == 0.0

    loaded = load_graph_bundle(path)
    assert loaded.nodes[0].confidence is None
    assert loaded.nodes[1].confidence == 0.0
    assert loaded.edges[0].confidence is None
    assert loaded.edges[1].confidence == 0.0


def test_typed_assessments_validate_and_export_without_flattening():
    assessment = _assessment("assess::1", "edge::1")
    bundle = GraphBundle(
        graph_id="typed_fixture",
        metadata={"legacy_confidence_mapping_policy": "fixture_policy"},
        nodes=[
            Node(id="source::1", type="source", title="Source"),
            Node(id="claim::1", type="claim", title="Claim"),
        ],
        edges=[
            Edge(
                id="edge::1",
                source="source::1",
                target="claim::1",
                type="supports_claim",
                confidence=0.0,
                assessments=[assessment],
                evidence_ids=["basis::1"],
            )
        ],
    )

    report = validate_assessment_readiness(bundle)
    assert report["summary"]["error"] == 0
    assert "legacy_confidence_without_mapping_policy" not in {item["code"] for item in report["findings"]}

    cytoscape = to_cytoscape_json(bundle)
    assert cytoscape["edges"][0]["data"]["confidence"] == 0.0
    assert cytoscape["edges"][0]["data"]["assessments"][0]["dimension"] == "grounding_strength"

    jsonld = to_jsonld(bundle)
    exported_edge = next(item for item in jsonld["@graph"] if item["@id"] == "edge::1")
    assert exported_edge["confidence"] == 0.0
    assert exported_edge["assessments"][0]["assessment_id"] == "assess::1"


def test_namespaced_dimensions_are_allowed_but_unknown_plain_dimensions_fail():
    assessment = _assessment("assess::topic", "topic::1")
    assessment.dimension = "citegeist:topic_relevance"
    assert assessment.dimension == "citegeist:topic_relevance"

    with pytest.raises(ValidationError):
        ConfidenceAssessment(
            assessment_id="assess::bad",
            subject_id="claim::1",
            dimension="topic_relevance",
            value=0.5,
            band="moderate",
            method=_method(),
            recorded_at="2026-07-25T12:00:00+00:00",
        )


def test_lineage_and_latest_helpers_exclude_superseded_assessments():
    older = _assessment("assess::older", "claim::1", value=0.4)
    newer = _assessment("assess::newer", "claim::1", value=0.7)
    newer.recorded_at = "2026-07-25T13:00:00+00:00"
    newer.supersedes_assessment_id = "assess::older"
    node = Node(id="claim::1", type="claim", assessments=[older, newer])

    assert [item.assessment_id for item in active_assessments(node)] == ["assess::newer"]
    assert latest_assessment(node).assessment_id == "assess::newer"

    bundle = GraphBundle(graph_id="lineage", nodes=[node])
    assert validate_assessment_readiness(bundle)["summary"]["error"] == 0

    broken = _assessment("assess::broken", "claim::1")
    broken.supersedes_assessment_id = "missing"
    report = validate_assessment_readiness(GraphBundle(graph_id="broken", nodes=[Node(id="claim::1", type="claim", assessments=[broken])]))
    assert "dangling_assessment_supersession" in {item["code"] for item in report["findings"]}

from __future__ import annotations

import json
from pathlib import Path

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
    assessments_for,
    latest_assessment,
    load_graph_bundle,
    to_cytoscape_json,
    to_jsonld,
    validate_assessment_readiness,
    write_graph_bundle,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "confidence"
RAW_FIXTURE_ROOT = FIXTURE_ROOT / "raw"
EXPECTED_FIXTURE_ROOT = FIXTURE_ROOT / "expected"
MATRIX_PATH = Path(__file__).parents[1] / "docs" / "confidence-compatibility-matrix.md"
FIELD_INVENTORY_PATH = Path(__file__).parents[1] / "docs" / "confidence-field-inventory.json"


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


def _raw_fixture_paths() -> list[Path]:
    return sorted(RAW_FIXTURE_ROOT.glob("*.json"))


def _fixture_id(path: Path) -> str:
    return json.loads(path.read_text(encoding="utf-8"))["metadata"]["fixture_id"]


@pytest.mark.parametrize("fixture_path", _raw_fixture_paths(), ids=_fixture_id)
def test_confidence_contract_fixtures_round_trip_to_expected_payloads(fixture_path):
    fixture_id = _fixture_id(fixture_path)
    expected_path = EXPECTED_FIXTURE_ROOT / fixture_path.name

    assert expected_path.exists(), f"{fixture_id} lacks expected normalized fixture"

    bundle = GraphBundle.model_validate_json(fixture_path.read_text(encoding="utf-8"))
    assert bundle.metadata["fixture_id"] == fixture_id
    assert bundle.model_dump_legacy() == json.loads(expected_path.read_text(encoding="utf-8"))


def test_confidence_contract_fixture_matrix_is_complete():
    matrix = MATRIX_PATH.read_text(encoding="utf-8")
    raw_ids = {_fixture_id(path) for path in _raw_fixture_paths()}
    expected_ids = {_fixture_id(path) for path in sorted(EXPECTED_FIXTURE_ROOT.glob("*.json"))}

    assert raw_ids
    assert raw_ids == expected_ids
    for fixture_id in raw_ids:
        assert f"`{fixture_id}`" in matrix


def test_confidence_field_inventory_declares_owner_and_disposition():
    inventory = json.loads(FIELD_INVENTORY_PATH.read_text(encoding="utf-8"))
    field_ids = {item["id"] for item in inventory["fields"]}

    assert {"Epistemap", "CiteGeist", "GroundRecall", "Didactopus"} <= set(inventory["scope"])
    assert len(field_ids) == len(inventory["fields"])
    for item in inventory["fields"]:
        assert item["repository"] in inventory["scope"]
        assert item["owner"]
        assert item["meaning"]
        assert item["missing_behavior"]
        assert item["disposition"]


def test_fixture_missing_and_explicit_zero_remain_distinct():
    missing = GraphBundle.model_validate_json(
        (RAW_FIXTURE_ROOT / "epistemap_legacy_missing.json").read_text(encoding="utf-8")
    )
    zero = GraphBundle.model_validate_json(
        (RAW_FIXTURE_ROOT / "epistemap_legacy_explicit_zero.json").read_text(encoding="utf-8")
    )

    assert missing.nodes[0].confidence is None
    assert "confidence" not in missing.model_dump_legacy()["nodes"][0]
    assert zero.nodes[0].confidence == 0.0
    assert zero.edges[0].confidence == 0.0
    assert zero.model_dump_legacy()["nodes"][0]["confidence"] == 0.0
    assert zero.model_dump_legacy()["edges"][0]["confidence"] == 0.0


def test_fixture_ambiguous_legacy_mapping_reports_warning():
    bundle = GraphBundle.model_validate_json(
        (RAW_FIXTURE_ROOT / "didactopus_ambiguous_legacy_mapping.json").read_text(encoding="utf-8")
    )
    report = validate_assessment_readiness(bundle)

    assert "legacy_confidence_without_mapping_policy" in {item["code"] for item in report["findings"]}


def test_fixture_superseded_lineage_preserves_history_and_active_value():
    bundle = GraphBundle.model_validate_json(
        (RAW_FIXTURE_ROOT / "groundrecall_superseded_lineage.json").read_text(encoding="utf-8")
    )
    node = bundle.nodes[0]

    assert [item.assessment_id for item in assessments_for(node)] == [
        "groundrecall::assessment::old",
        "groundrecall::assessment::new",
    ]
    assert [item.assessment_id for item in active_assessments(node)] == ["groundrecall::assessment::new"]
    assert latest_assessment(node).value == 0.75


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

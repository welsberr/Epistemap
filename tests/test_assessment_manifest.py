from __future__ import annotations

import pytest

from epistemap import (
    assessment_manifest,
    read_assessment_manifest,
    validate_assessment_manifest,
    write_assessment_manifest,
)


def test_assessment_manifest_round_trips_with_default_policies(tmp_path) -> None:
    manifest = assessment_manifest(
        assessment_id="detective-plain-001",
        graph_file="epistemap_graph.json",
        assessment_file="bayesian_assessment.json",
        validation_file="assessment_validation.json",
        bayesian_prior_profile="adversarial_aware",
        graph_extraction_policy={"name": "one_hop_claim_neighborhood", "depth": 1},
        experiment_id="detective-fair-play-001",
        condition="kg-assisted",
        corpus="open-detective-fiction",
        created_by="codex",
    )
    destination = tmp_path / "assessment_manifest.json"

    write_assessment_manifest(manifest, destination)
    loaded = read_assessment_manifest(destination)
    validation = validate_assessment_manifest(loaded)

    assert loaded["manifest_kind"] == "epistemap_assessment"
    assert loaded["schema_version"] == "0.1"
    assert loaded["assessment_id"] == "detective-plain-001"
    assert loaded["bayesian_prior_profile"] == "adversarial_aware"
    assert loaded["graph_extraction_policy"]["depth"] == 1
    assert loaded["evidence_weighting_policy"]["name"] == "confidence_weighted_edges"
    assert validation["summary"]["status"] == "pass"


def test_assessment_manifest_accepts_string_policy_names() -> None:
    manifest = assessment_manifest(
        assessment_id="source-quality-ablation",
        graph_file="graph.json",
        graph_extraction_policy="claim_neighborhood",
        evidence_weighting_policy="flat_edges",
        temporal_policy="narrative_order",
        reliability_treatment="hidden_from_subject",
        validation_policy="strict_experiment_inputs",
    )

    assert manifest["graph_extraction_policy"] == {"name": "claim_neighborhood"}
    assert manifest["evidence_weighting_policy"] == {"name": "flat_edges"}
    assert manifest["temporal_policy"] == {"name": "narrative_order"}
    assert manifest["reliability_treatment"] == {"name": "hidden_from_subject"}
    assert manifest["validation_policy"] == {"name": "strict_experiment_inputs"}


def test_assessment_manifest_validation_surfaces_missing_audit_paths() -> None:
    manifest = assessment_manifest(assessment_id="minimal", graph_file="graph.json")
    validation = validate_assessment_manifest(manifest)
    codes = {finding["code"] for finding in validation["findings"]}

    assert validation["summary"]["status"] == "pass"
    assert codes == {"missing_assessment_file", "missing_validation_file"}
    assert validation["summary"]["info"] == 2


def test_assessment_manifest_rejects_bad_manifest_kind(tmp_path) -> None:
    destination = tmp_path / "manifest.json"
    destination.write_text('{"manifest_kind": "wrong"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="not an Epistemap assessment manifest"):
        read_assessment_manifest(destination)


def test_assessment_manifest_requires_identifiers() -> None:
    with pytest.raises(ValueError, match="assessment_id"):
        assessment_manifest(assessment_id="", graph_file="graph.json")
    with pytest.raises(ValueError, match="graph_file"):
        assessment_manifest(assessment_id="x", graph_file="")

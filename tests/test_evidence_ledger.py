from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from epistemap import (
    AssessmentMethodRef,
    ConfidenceAssessment,
    Edge,
    EvidenceLedger,
    EvidenceReference,
    EvidenceUnit,
    EvidenceWeightingPolicy,
    GraphBundle,
    Node,
    derive_evidence_identity,
    graph_to_evidence_ledger,
)


def _policy() -> EvidenceWeightingPolicy:
    return EvidenceWeightingPolicy(
        policy_id="fixture_weighting_v1",
        method_name="fixture_weighting",
        method_version="1.0",
        source_family_dependence="record_only",
    )


def _assessment(value: float | None = 0.0) -> ConfidenceAssessment:
    return ConfidenceAssessment(
        assessment_id="assessment::zero",
        subject_id="edge::1",
        dimension="grounding_strength",
        value=value,
        band="unknown" if value is None else "very_low",
        method=AssessmentMethodRef(name="fixture_assessor", version="1.0", policy_id="fixture_assessor_v1"),
        recorded_at="2026-07-25T12:00:00+00:00",
    )


def _unit(unit_id: str = "unit::1", *, stance: str = "support") -> EvidenceUnit:
    return EvidenceUnit(
        unit_id=unit_id,
        subject_claim_id="claim::1",
        stance=stance,
        references=[
            EvidenceReference(
                source_record_id="source::1",
                artifact_id="artifact::1",
                fragment_id="fragment::1",
                graph_edge_id="edge::1",
                source_family_id="family::publisher",
            )
        ],
        source_family_ids=["family::publisher"],
        input_assessments=[_assessment(0.0)],
        raw_weight=None,
        effective_weight=None,
        deduplication_key="artifact::1#fragment::1",
        deduplication_rationale="same artifact fragment",
        policy_id="fixture_weighting_v1",
        method_name="fixture_extraction",
        method_version="1.0",
    )


def test_ledger_serialization_and_hashing_are_deterministic() -> None:
    ledger = EvidenceLedger(
        ledger_id="ledger::1",
        subject_claim_ids=["claim::1"],
        units=[_unit()],
        weighting_policy=_policy(),
    )
    same = EvidenceLedger.model_validate_json(ledger.deterministic_json())

    assert ledger.deterministic_json() == same.deterministic_json()
    assert ledger.content_hash() == same.content_hash()


def test_identity_derivation_order_is_explicit_then_fragment_then_edge_then_provenance() -> None:
    assert derive_evidence_identity(explicit_evidence_id="evidence::explicit") == "evidence::explicit"
    assert derive_evidence_identity(artifact_id="artifact::1", fragment_id="fragment::1").startswith(
        "evidence:artifact-fragment:"
    )
    assert derive_evidence_identity(graph_edge_id="edge::1") == "evidence:graph-edge:edge::1"
    assert derive_evidence_identity(provenance={"source": "fixture"}).startswith("evidence:provenance:")


def test_missing_weights_remain_missing_and_explicit_zero_assessments_survive() -> None:
    ledger = EvidenceLedger(
        ledger_id="ledger::missing-weights",
        subject_claim_ids=["claim::1"],
        units=[_unit()],
        weighting_policy=_policy(),
    )

    assert ledger.units[0].raw_weight is None
    assert ledger.units[0].effective_weight is None
    assert ledger.units[0].input_assessments[0].value == 0.0


def test_source_family_dependence_is_representable_without_discounting() -> None:
    policy = EvidenceWeightingPolicy(
        policy_id="source_family_record_only_v1",
        method_name="record_source_families",
        method_version="1.0",
        source_family_dependence="record_only",
        source_family_discount=None,
    )
    unit = _unit()

    assert policy.source_family_dependence == "record_only"
    assert policy.source_family_discount is None
    assert unit.source_family_ids == ["family::publisher"]
    assert unit.references[0].source_family_id == "family::publisher"


def test_revision_evidence_is_separate_from_challenge_evidence() -> None:
    original = _unit("unit::original")
    revision = EvidenceUnit(
        unit_id="unit::revision",
        subject_claim_id="claim::1",
        stance="revision",
        references=[EvidenceReference(graph_edge_id="edge::revision")],
        policy_id="fixture_weighting_v1",
        method_name="fixture_revision_extraction",
        method_version="1.0",
        revision_of_unit_ids=["unit::original"],
    )
    ledger = EvidenceLedger(
        ledger_id="ledger::revision",
        subject_claim_ids=["claim::1"],
        units=[original, revision],
        weighting_policy=_policy(),
    )

    assert ledger.units[1].stance == "revision"
    with pytest.raises(ValidationError):
        EvidenceUnit(
            unit_id="unit::bad-challenge",
            subject_claim_id="claim::1",
            stance="challenge",
            policy_id="fixture_weighting_v1",
            method_name="fixture_revision_extraction",
            method_version="1.0",
            revision_of_unit_ids=["unit::original"],
        )


def test_ledger_validates_duplicate_ids_missing_subjects_dangling_revisions_and_unversioned_methods() -> None:
    with pytest.raises(ValidationError):
        EvidenceLedger(
            ledger_id="ledger::duplicates",
            subject_claim_ids=["claim::1"],
            units=[_unit("unit::same"), _unit("unit::same")],
            weighting_policy=_policy(),
        )

    with pytest.raises(ValidationError):
        EvidenceLedger(
            ledger_id="ledger::unknown-subject",
            subject_claim_ids=["claim::other"],
            units=[_unit()],
            weighting_policy=_policy(),
        )

    with pytest.raises(ValidationError):
        EvidenceLedger(
            ledger_id="ledger::dangling",
            subject_claim_ids=["claim::1"],
            units=[
                EvidenceUnit(
                    unit_id="unit::revision",
                    subject_claim_id="claim::1",
                    stance="revision",
                    policy_id="fixture_weighting_v1",
                    method_name="fixture_revision_extraction",
                    method_version="1.0",
                    revision_of_unit_ids=["unit::missing"],
                )
            ],
            weighting_policy=_policy(),
        )

    with pytest.raises(ValidationError):
        EvidenceWeightingPolicy(policy_id="missing_method_version", method_name="fixture", method_version="")

    with pytest.raises(ValidationError):
        EvidenceUnit(
            unit_id="unit::unversioned",
            subject_claim_id="claim::1",
            stance="support",
            policy_id="fixture_weighting_v1",
            method_name="fixture",
            method_version="",
        )


def test_graph_to_ledger_deduplicates_same_fragment_and_preserves_referring_edges() -> None:
    bundle = GraphBundle.model_validate_json(
        (Path(__file__).parent / "fixtures" / "confidence" / "raw" / "epistemap_deduplicated_graph_edges.json").read_text(
            encoding="utf-8"
        )
    )

    ledger = graph_to_evidence_ledger(bundle, "claim::main")
    support_unit = next(unit for unit in ledger.units if unit.stance == "support")

    assert ledger.metadata["raw_counts"]["support"] == 2
    assert ledger.metadata["deduplicated_counts"]["support"] == 1
    assert sorted(support_unit.referring_edge_ids) == ["edge::support-a", "edge::support-b"]
    assert support_unit.source_family_ids == ["family::journal"]
    assert support_unit.weight_input_id == "edge::support-a"
    assert support_unit.weight_policy_rule == "legacy_edge_confidence"


def test_graph_to_ledger_reports_missing_weight_defaults_and_revision_counts_separately() -> None:
    bundle = GraphBundle.model_validate_json(
        (Path(__file__).parent / "fixtures" / "confidence" / "raw" / "epistemap_deduplicated_graph_edges.json").read_text(
            encoding="utf-8"
        )
    )

    ledger = graph_to_evidence_ledger(bundle, "claim::main")
    challenge = next(unit for unit in ledger.units if unit.stance == "challenge")
    revision = next(unit for unit in ledger.units if unit.stance == "revision")

    assert challenge.effective_weight == 1.0
    assert challenge.weight_policy_rule == "missing_weight_default"
    assert "missing_weight_default_applied" in {diagnostic.code for diagnostic in ledger.diagnostics}
    assert ledger.metadata["raw_counts"]["challenge"] == 1
    assert ledger.metadata["raw_counts"]["revision"] == 1
    assert revision.revision_of_unit_ids == ["evidence:graph-edge:edge::support-a"]
    assert ledger.metadata["deduplicated_counts"]["challenge"] == 1


def test_graph_to_ledger_lists_component_claims_for_concept_conversion() -> None:
    bundle = GraphBundle(
        graph_id="concept-components",
        nodes=[
            Node(id="claim::component", type="claim", title="Component"),
            Node(id="concept::topic", type="concept", title="Topic"),
        ],
        edges=[
            Edge(
                id="edge::component-topic",
                source="claim::component",
                target="concept::topic",
                type="about_concept",
                confidence=0.9,
            )
        ],
    )

    ledger = graph_to_evidence_ledger(bundle, "concept::topic")

    assert ledger.subject_claim_ids == ["claim::component"]
    assert ledger.units[0].subject_claim_id == "claim::component"

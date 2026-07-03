from __future__ import annotations

import pytest

from epistemap import (
    detective_annotation_fair_play_diagnostic,
    detective_annotation_graph_bundle,
    detective_corpus_summary,
    detective_recognition_g_row,
    detective_story_annotation,
    read_detective_story_annotation,
    validate_detective_story_annotation,
    write_detective_story_annotation,
)


def _annotation() -> dict:
    return detective_story_annotation(
        story_id="story::blue-carbuncle",
        title="The Blue Carbuncle",
        author="Arthur Conan Doyle",
        publication_year=1892,
        source_url="https://example.org/blue-carbuncle",
        source_license="public_domain",
        public_domain=True,
        narrative_unit="scene",
        reveal_point=9,
        fair_play_status="fair_play",
        manifest_file="assessment_manifest.json",
        validation_file="assessment_validation.json",
        graph_file="epistemap_graph.json",
        claims=[
            {
                "claim_id": "claim::innocent",
                "text": "The accused man stole the jewel.",
                "speaker": "police",
                "truth_status": "false",
                "narrative_anchor": "scene-1",
                "introduced_at": 1,
            },
            {
                "claim_id": "claim::goose",
                "text": "The jewel travelled through the goose.",
                "truth_status": "true",
                "narrative_anchor": "scene-5",
                "introduced_at": 5,
            },
        ],
        decisive_evidence=[
            {
                "evidence_id": "evidence::goose-chain",
                "text": "The chain of custody shows the jewel entered the goose before the accused found it.",
                "contradicts_claim_id": "claim::innocent",
                "available_at": 7,
                "narrative_anchor": "scene-7",
                "access_scope": "reader_available",
            }
        ],
    )


def test_detective_story_annotation_round_trips_and_validates(tmp_path) -> None:
    annotation = _annotation()
    destination = tmp_path / "annotation.json"

    write_detective_story_annotation(annotation, destination)
    loaded = read_detective_story_annotation(destination)
    validation = validate_detective_story_annotation(loaded)

    assert loaded["annotation_kind"] == "epistemap_detective_story_annotation"
    assert loaded["story_id"] == "story::blue-carbuncle"
    assert loaded["claims"][0]["truth_status"] == "false"
    assert validation["summary"]["status"] == "pass"
    assert validation["summary"]["false_claim_count"] == 1


def test_detective_story_annotation_validation_flags_unfair_evidence() -> None:
    annotation = detective_story_annotation(
        story_id="story::unfair",
        title="Unfair Reveal",
        reveal_point=5,
        fair_play_status="late_decisive_evidence",
        claims=[{"claim_id": "claim::alibi", "text": "The alibi is sound.", "truth_status": "false"}],
        decisive_evidence=[
            {
                "evidence_id": "evidence::diary",
                "text": "The diary contradicts the alibi.",
                "contradicts_claim_id": "claim::alibi",
                "available_at": 6,
                "access_scope": "detective_only",
            }
        ],
    )

    validation = validate_detective_story_annotation(annotation)
    codes = {finding["code"] for finding in validation["findings"]}

    assert validation["summary"]["status"] == "warning"
    assert "decisive_evidence_after_reveal" in codes
    assert "decisive_evidence_not_reader_available" in codes
    assert "missing_sidecar_reference" in codes


def test_detective_story_annotation_requires_core_fields() -> None:
    with pytest.raises(ValueError, match="story_id"):
        detective_story_annotation(story_id="", title="Missing")
    with pytest.raises(ValueError, match="title"):
        detective_story_annotation(story_id="story::x", title="")
    with pytest.raises(ValueError, match="fair_play_status"):
        detective_story_annotation(story_id="story::x", title="X", fair_play_status="bad")


def test_detective_recognition_g_row_uses_decisive_evidence_window() -> None:
    row = detective_recognition_g_row(
        _annotation(),
        claim_id="claim::innocent",
        y=1,
        p=0.8,
        env="K",
        run_id="run-1",
        subject_id="model-a",
        condition="kg-assisted",
        phase="post",
        response="The accused cannot have stolen it.",
        recognized_at=8,
    )

    assert row["item_id"] == "story::blue-carbuncle"
    assert row["claim_id"] == "claim::innocent"
    assert row["source_anchor"] == "scene-1"
    assert row["contradiction_available_at"] == 7
    assert row["recognized_at"] == 8
    assert row["recognition_lag"] == 1.0
    assert row["fair_play_rating"] == "fair_play"
    assert row["evaluation_target"] == "detective_contradiction_recognition"
    assert row["decisive_evidence_id"] == "evidence::goose-chain"


def test_detective_annotation_graph_bundle_feeds_temporal_fair_play_diagnostic() -> None:
    annotation = _annotation()
    graph = detective_annotation_graph_bundle(annotation)
    report = detective_annotation_fair_play_diagnostic(annotation)

    assert graph.graph_id == "story::blue-carbuncle::detective-annotation-graph"
    assert {node.id for node in graph.nodes} >= {
        "story::blue-carbuncle",
        "claim::innocent",
        "evidence::goose-chain",
    }
    assert {
        (edge.source, edge.target, edge.type)
        for edge in graph.edges
    } >= {("evidence::goose-chain", "claim::innocent", "contradicts")}
    assert report["rating"] == "fair"
    assert report["claims"][0]["claim_id"] == "claim::innocent"
    assert report["claims"][0]["first_decisive_evidence"]["time"] == "7"
    assert report["annotation"]["fair_play_status"] == "fair_play"


def test_detective_corpus_summary_counts_validation_status() -> None:
    clean = _annotation()
    incomplete = detective_story_annotation(
        story_id="story::incomplete",
        title="Incomplete",
        fair_play_status="ambiguous",
    )

    summary = detective_corpus_summary([clean, incomplete])

    assert summary["summary_kind"] == "epistemap_detective_corpus_summary"
    assert summary["story_count"] == 2
    assert summary["status_counts"]["pass"] == 1
    assert summary["status_counts"]["error"] == 1
    assert summary["fair_play_status_counts"]["fair_play"] == 1

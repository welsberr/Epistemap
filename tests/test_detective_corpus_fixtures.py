from __future__ import annotations

from pathlib import Path

from epistemap import (
    detective_annotation_fair_play_diagnostic,
    detective_annotation_graph_bundle,
    detective_corpus_summary,
    detective_recognition_g_row,
    read_detective_story_annotation,
    validate_detective_story_annotation,
)


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "examples" / "detective_corpus" / "candidates"


def _fixtures() -> list[dict]:
    return [
        read_detective_story_annotation(path)
        for path in sorted(FIXTURE_DIR.glob("*.json"))
    ]


def test_detective_corpus_candidate_fixtures_validate() -> None:
    annotations = _fixtures()

    assert len(annotations) >= 4
    for annotation in annotations:
        report = validate_detective_story_annotation(annotation)
        assert report["summary"]["error"] == 0


def test_detective_corpus_candidate_fixture_summary_tracks_controls() -> None:
    summary = detective_corpus_summary(_fixtures())

    assert summary["story_count"] >= 4
    assert summary["fair_play_status_counts"]["fair_play"] >= 3
    assert summary["fair_play_status_counts"]["withheld_decisive_evidence"] >= 1
    assert summary["status_counts"].get("error", 0) == 0


def test_detective_candidate_fixture_can_emit_recognition_g_row() -> None:
    annotation = next(
        item for item in _fixtures() if item["fair_play_status"] == "fair_play"
    )
    claim = next(
        item
        for item in annotation["claims"]
        if item["truth_status"] in {"false", "misleading", "contradicted"}
    )
    evidence = next(
        item
        for item in annotation["decisive_evidence"]
        if item["contradicts_claim_id"] == claim["claim_id"]
    )

    row = detective_recognition_g_row(
        annotation,
        claim_id=claim["claim_id"],
        y=1,
        p=0.8,
        env="candidate_fixture",
        run_id="fixture-smoke",
        subject_id="test-reader",
        condition="fair-play",
        phase="pilot",
        response="recognized contradiction",
        recognized_at=evidence["available_at"],
    )

    assert row["claim_id"] == claim["claim_id"]
    assert row["contradiction_available_at"] == evidence["available_at"]
    assert row["recognition_lag"] == 0
    assert row["fair_play_rating"] == "fair_play"


def test_detective_candidate_fixtures_feed_temporal_fair_play_diagnostics() -> None:
    diagnostics = {
        annotation["story_id"]: detective_annotation_fair_play_diagnostic(annotation)
        for annotation in _fixtures()
    }

    fair_reports = [
        report
        for report in diagnostics.values()
        if report["annotation"]["fair_play_status"] == "fair_play"
    ]
    control = diagnostics["story::purloined-letter-control"]

    assert fair_reports
    assert all(report["rating"] == "fair" for report in fair_reports)
    assert control["rating"] == "unfair"
    assert "hidden_or_private_decisive_evidence" in control["claims"][0]["failures"]


def test_detective_candidate_fixture_graphs_preserve_public_source_provenance() -> None:
    annotation = _fixtures()[0]
    graph = detective_annotation_graph_bundle(annotation)

    story_node = graph.node_index()[annotation["story_id"]]
    assert story_node.provenance[0].source_url == annotation["source_url"]
    assert graph.metadata["fair_play_status"] == annotation["fair_play_status"]
    assert graph.metadata["summary"]["claim_count"] == len(annotation["claims"])

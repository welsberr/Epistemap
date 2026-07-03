from __future__ import annotations

from pathlib import Path

from epistemap import (
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

from __future__ import annotations

import csv
from io import StringIO

import pytest

from epistemap import (
    apply_detective_anchor_review,
    detective_annotation_fair_play_diagnostic,
    detective_annotation_graph_bundle,
    detective_anchor_review_template,
    detective_anchor_review_template_csv,
    detective_corpus_summary,
    detective_g_collection_template,
    detective_g_collection_template_csv,
    detective_g_experiment_manifest_from_rows,
    detective_g_run_sheets,
    detective_recognition_g_row,
    detective_story_annotation,
    merge_detective_g_run_sheets,
    read_detective_story_annotation,
    unblind_detective_g_run_sheets,
    validate_detective_g_collection_rows,
    validate_detective_story_annotation,
    write_blinded_detective_g_run_sheets,
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


def test_detective_anchor_review_template_lists_claims_and_evidence() -> None:
    template = detective_anchor_review_template(_annotation())
    csv_text = detective_anchor_review_template_csv(template)

    assert template["template_kind"] == "epistemap_detective_anchor_review_template"
    assert template["row_count"] == 3
    assert [row["artifact_kind"] for row in template["rows"]] == [
        "claim",
        "claim",
        "decisive_evidence",
    ]
    assert {row["review_status"] for row in template["rows"]} == {"needs_review"}
    assert template["rows"][0]["current_narrative_anchor"] == "scene-1"
    assert "reviewed_source_quote" in csv_text.splitlines()[0]
    assert "The accused man stole the jewel." in csv_text


def test_detective_anchor_review_template_preserves_completed_review_metadata() -> None:
    annotation = _annotation()
    annotation["claims"][0]["metadata"]["anchor_review"] = {
        "review_status": "reviewed",
        "reviewed_source_locator": "page 1 paragraph 2",
        "reviewed_source_quote": "The accused man stole the jewel.",
        "reviewed_narrative_anchor": "reviewed opening inquiry",
        "reviewer": "Reviewer",
        "reviewed_at": "2026-07-04",
    }

    template = detective_anchor_review_template(annotation)
    row = template["rows"][0]

    assert row["review_status"] == "reviewed"
    assert row["reviewed_source_locator"] == "page 1 paragraph 2"
    assert row["reviewed_narrative_anchor"] == "reviewed opening inquiry"
    assert row["reviewer"] == "Reviewer"


def test_apply_detective_anchor_review_updates_annotation_metadata() -> None:
    annotation = _annotation()
    review_rows = [
        {
            "artifact_id": "claim::innocent",
            "review_status": "reviewed",
            "reviewed_source_locator": "page 1 paragraph 2",
            "reviewed_source_quote": "The accused man stole the jewel.",
            "reviewed_narrative_anchor": "reviewed opening inquiry",
            "reviewer": "Reviewer",
            "reviewed_at": "2026-07-04",
        },
        {
            "artifact_id": "claim::goose",
            "review_status": "reviewed",
            "reviewed_source_locator": "page 5 paragraph 1",
            "reviewed_source_quote": "The jewel travelled through the goose.",
            "reviewed_narrative_anchor": "reviewed goose chain",
            "reviewer": "Reviewer",
            "reviewed_at": "2026-07-04",
        },
        {
            "artifact_id": "evidence::goose-chain",
            "review_status": "reviewed",
            "reviewed_source_locator": "page 7 paragraph 3",
            "reviewed_source_quote": "The chain of custody shows the jewel entered the goose.",
            "reviewed_narrative_anchor": "reviewed evidence chain",
            "reviewer": "Reviewer",
            "reviewed_at": "2026-07-04",
        },
    ]

    result = apply_detective_anchor_review(annotation, review_rows, review_source="review.csv")
    updated = result["annotation"]

    assert result["summary"]["status"] == "reviewed"
    assert result["summary"]["applied_row_count"] == 3
    assert updated["metadata"]["annotation_status"] == "human_anchor_reviewed"
    assert updated["metadata"]["anchor_review"]["source_file"] == "review.csv"
    assert updated["claims"][0]["narrative_anchor"] == "reviewed opening inquiry"
    assert updated["claims"][0]["metadata"]["anchor_review"]["reviewed_source_locator"] == "page 1 paragraph 2"


def test_detective_g_collection_template_uses_treatments_phases_and_claims(tmp_path) -> None:
    diagnostic_path = tmp_path / "sidecars" / "story" / "fair_play_diagnostic.json"
    diagnostic_path.parent.mkdir(parents=True)
    diagnostic_path.write_text(
        """
{
  "claims": [
    {
      "claim_id": "claim::false",
      "first_decisive_evidence": {"time": "7"},
      "rating": "fair"
    }
  ],
  "rating": "fair"
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    graph_path = tmp_path / "sidecars" / "story" / "epistemap_graph.json"
    graph_path.write_text(
        """
{
  "nodes": [
    {
      "id": "claim::false",
      "metadata": {
        "narrative_anchor": "provisional anchor",
        "anchor_review": {
          "reviewed_narrative_anchor": "reviewed source anchor"
        }
      }
    }
  ],
  "edges": []
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    treatment = {
        "experiment_id": "detective-pilot",
        "evaluation_target": "detective_contradiction_recognition",
        "treatments": [{"condition": "plain-reading"}, {"condition": "graph-assisted"}],
        "phases": ["pre-reveal", "post-reveal"],
        "fair_play_policy": {"admit_ratings": ["fair"], "control_ratings": ["unfair"]},
    }
    corpus = {
        "sidecars": [
            {
                "story_id": "story::sample",
                "title": "Sample Story",
                "fair_play_status": "fair_play",
                "fair_play_rating": "fair",
                "graph_file": "story/epistemap_graph.json",
                "fair_play_diagnostic_file": "story/fair_play_diagnostic.json",
            }
        ]
    }

    template = detective_g_collection_template(
        treatment,
        corpus,
        sidecar_base_dir=tmp_path / "sidecars",
    )
    csv_text = detective_g_collection_template_csv(template)

    assert template["template_kind"] == "epistemap_detective_g_collection_template"
    assert template["row_count"] == 4
    assert {row["condition"] for row in template["rows"]} == {"plain-reading", "graph-assisted"}
    assert {row["phase"] for row in template["rows"]} == {"pre-reveal", "post-reveal"}
    assert template["rows"][0]["claim_id"] == "claim::false"
    assert template["rows"][0]["source_anchor"] == "reviewed source anchor"
    assert template["rows"][0]["contradiction_available_at"] == "7"
    assert template["rows"][0]["template_role"] == "primary"
    assert "story_title" in csv_text.splitlines()[0]
    assert "Sample Story" in csv_text


def test_validate_detective_g_collection_rows_flags_incomplete_and_invalid_rows() -> None:
    rows = [
        {
            "condition": "plain-reading",
            "phase": "pre-reveal",
            "item_id": "story::sample",
            "claim_id": "claim::sample",
            "env": "K",
            "source_anchor": "scene 1",
            "contradiction_available_at": "7",
            "fair_play_rating": "fair",
            "y": "",
            "p": "",
        },
        {
            "condition": "plain-reading",
            "phase": "post-reveal",
            "item_id": "story::sample",
            "claim_id": "claim::sample",
            "env": "K",
            "source_anchor": "scene 1",
            "contradiction_available_at": "7",
            "fair_play_rating": "fair",
            "y": "2",
            "p": "1.2",
        },
    ]

    report = validate_detective_g_collection_rows(rows)
    codes = {finding["code"] for finding in report["findings"]}

    assert report["summary"]["status"] == "error"
    assert "missing_completed_g_field" in codes
    assert "invalid_y_value" in codes
    assert "invalid_probability_value" in codes


def test_validate_detective_g_collection_rows_accepts_completed_rows() -> None:
    report = validate_detective_g_collection_rows(
        [
            {
                "condition": "plain-reading",
                "phase": "post-reveal",
                "item_id": "story::sample",
                "claim_id": "claim::sample",
                "env": "K",
                "source_anchor": "scene 1",
                "contradiction_available_at": "7",
                "recognized_at": "8",
                "recognition_lag": "1.0",
                "fair_play_rating": "fair",
                "y": "1",
                "p": "0.8",
                "response": "recognized contradiction",
            }
        ]
    )

    assert report["summary"]["status"] == "pass"
    assert report["summary"]["finding_count"] == 0


def test_detective_g_experiment_manifest_from_rows_records_context() -> None:
    manifest = detective_g_experiment_manifest_from_rows(
        [
            {
                "condition": "plain-reading",
                "phase": "post-reveal",
                "fair_play_rating": "fair",
            },
            {
                "condition": "graph-assisted",
                "phase": "pre-reveal",
                "fair_play_rating": "unfair",
            },
        ],
        experiment_id="detective-pilot",
        row_file="rows.csv",
        name="Detective pilot",
        corpus="detective_corpus",
    )

    assert manifest["manifest_kind"] == "epistemap_g_experiment"
    assert manifest["experiment_id"] == "detective-pilot"
    assert manifest["conditions"] == ["graph-assisted", "plain-reading"]
    assert manifest["phases"] == ["post-reveal", "pre-reveal"]
    assert manifest["row_count"] == 2
    assert manifest["metadata"]["fair_play_ratings"] == ["fair", "unfair"]


def test_detective_g_run_sheets_fill_subjects_and_shuffle_rows() -> None:
    rows = [
        {
            "condition": "plain-reading",
            "phase": "pre-reveal",
            "item_id": "story::a",
            "claim_id": "claim::a",
            "env": "K",
            "source_anchor": "scene 1",
            "contradiction_available_at": "7",
            "fair_play_rating": "fair",
        },
        {
            "condition": "plain-reading",
            "phase": "post-reveal",
            "item_id": "story::b",
            "claim_id": "claim::b",
            "env": "K",
            "source_anchor": "scene 2",
            "contradiction_available_at": "8",
            "fair_play_rating": "fair",
        },
        {
            "condition": "graph-assisted",
            "phase": "pre-reveal",
            "item_id": "story::c",
            "claim_id": "claim::c",
            "env": "K",
            "source_anchor": "scene 3",
            "contradiction_available_at": "9",
            "fair_play_rating": "fair",
        },
    ]

    packet = detective_g_run_sheets(
        rows,
        run_id_prefix="pilot",
        subject_prefix="reader",
        subjects_per_condition=2,
        conditions=["plain-reading"],
        seed=13,
    )

    assert packet["packet_kind"] == "epistemap_detective_g_run_sheets"
    assert packet["sheet_count"] == 2
    assert packet["row_count"] == 4
    assert packet["sheets"][0]["run_id"] == "pilot-plain-reading-01"
    assert packet["sheets"][0]["subject_id"] == "reader-plain-reading-01"
    assert {row["condition"] for row in packet["sheets"][0]["rows"]} == {"plain-reading"}
    assert {row["run_id"] for row in packet["sheets"][0]["rows"]} == {"pilot-plain-reading-01"}


def test_merge_detective_g_run_sheets_writes_rows_and_validation(tmp_path) -> None:
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    header = (
        "run_id,subject_id,condition,phase,item_id,claim_id,env,y,p,answer,response,"
        "source_anchor,recognized_at,contradiction_available_at,recognition_lag,fair_play_rating"
    )
    first.write_text(
        header
        + "\n"
        + "run-1,reader-1,plain-reading,post-reveal,story::a,claim::a,K,1,0.8,,recognized,scene 1,8,7,1.0,fair\n",
        encoding="utf-8",
    )
    second.write_text(
        header
        + "\n"
        + "run-2,reader-2,graph-assisted,post-reveal,story::a,claim::a,K,1,0.9,,recognized,scene 1,7,7,0.0,fair\n",
        encoding="utf-8",
    )
    output = tmp_path / "merged.csv"

    report = merge_detective_g_run_sheets([tmp_path], output)

    assert report["report_kind"] == "epistemap_detective_g_run_sheet_merge"
    assert report["source_count"] == 2
    assert report["row_count"] == 2
    assert report["validation"]["summary"]["status"] == "pass"
    assert "run-1,reader-1" in output.read_text(encoding="utf-8")


def test_blind_and_unblind_detective_g_run_sheets_round_trip(tmp_path) -> None:
    source = tmp_path / "run.csv"
    source.write_text(
        "\n".join(
            [
                "run_id,subject_id,condition,phase,item_id,claim_id,env,y,p,answer,response,source_anchor,recognized_at,contradiction_available_at,recognition_lag,fair_play_rating,experiment_id,evaluation_target,story_title,fair_play_status,graph_file,fair_play_diagnostic_file,template_role",
                "run-1,reader-1,plain-reading,pre-reveal,story::a,claim::a,K,,,,,scene 1,,7,,fair,exp,detective,Story A,fair_play,graph.json,diagnostic.json,primary",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    blinded_dir = tmp_path / "blinded"

    packet = write_blinded_detective_g_run_sheets([source], blinded_dir)

    blinded_path = blinded_dir / "run.blinded.csv"
    blinded_text = blinded_path.read_text(encoding="utf-8")
    assert packet["sheet_count"] == 1
    assert "fair_play_rating" not in blinded_text.splitlines()[0]
    assert "graph_file" not in blinded_text.splitlines()[0]
    assert "row_key" in blinded_text.splitlines()[0]

    public_rows = list(csv.DictReader(StringIO(blinded_text)))
    public_rows[0]["y"] = "1"
    public_rows[0]["p"] = "0.8"
    public_rows[0]["response"] = "recognized"
    public_rows[0]["recognized_at"] = "8"
    output_text = StringIO()
    writer = csv.DictWriter(output_text, fieldnames=list(public_rows[0].keys()), lineterminator="\n")
    writer.writeheader()
    writer.writerows(public_rows)
    blinded_path.write_text(output_text.getvalue(), encoding="utf-8")
    output = tmp_path / "unblinded.csv"
    report = unblind_detective_g_run_sheets([blinded_path], blinded_dir / "detective_g_blinding_key.json", output)

    merged = output.read_text(encoding="utf-8")
    assert report["validation"]["summary"]["status"] == "pass"
    assert "plain-reading" in merged
    assert "fair" in merged

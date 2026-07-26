from __future__ import annotations

import json
import sys
from pathlib import Path

from epistemap import Edge, GraphBundle, Node, write_graph_bundle
from epistemap.cli import main
from epistemap.grounding_effect import (
    g_evaluation_row,
    g_experiment_manifest,
    g_experiment_summary,
    write_g_experiment_manifest,
    write_g_rows_csv,
)


def test_cli_g_summary_writes_summary(tmp_path, monkeypatch, capsys) -> None:
    rows_path = tmp_path / "g_rows.csv"
    manifest_path = tmp_path / "g_manifest.json"
    summary_path = tmp_path / "g_summary.json"
    markdown_path = tmp_path / "g_summary.md"
    write_g_rows_csv(
        [
            g_evaluation_row(y=1, p=0.9, env="C", condition="plain"),
            g_evaluation_row(y=0, p=0.1, env="C", condition="plain"),
            g_evaluation_row(y=1, p=0.8, env="K", condition="plain"),
            g_evaluation_row(y=0, p=0.2, env="K", condition="plain"),
        ],
        rows_path,
    )
    write_g_experiment_manifest(
        g_experiment_manifest(
            experiment_id="cli-summary",
            row_file="g_rows.csv",
            evaluation_target="recognition",
        ),
        manifest_path,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "g-summary",
            str(rows_path),
            "--manifest",
            str(manifest_path),
            "--out",
            str(summary_path),
            "--out-md",
            str(markdown_path),
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["manifest"]["experiment_id"] == "cli-summary"
    assert summary_path.exists()
    assert "# Epistemap G Summary" in markdown_path.read_text(encoding="utf-8")


def test_cli_g_summary_can_require_consistent_manifest(tmp_path, monkeypatch, capsys) -> None:
    rows_path = tmp_path / "g_rows.csv"
    manifest_path = tmp_path / "g_manifest.json"
    write_g_rows_csv(
        [
            g_evaluation_row(y=1, p=0.9, env="C", condition="plain"),
            g_evaluation_row(y=1, p=0.8, env="K", condition="plain"),
        ],
        rows_path,
    )
    write_g_experiment_manifest(
        g_experiment_manifest(
            experiment_id="cli-inconsistent-summary",
            row_file="g_rows.csv",
            evaluation_target="recognition",
            row_count=3,
        ),
        manifest_path,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "g-summary",
            str(rows_path),
            "--manifest",
            str(manifest_path),
            "--require-consistent",
        ],
    )

    try:
        main()
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected inconsistent summary to exit with status 2")
    payload = json.loads(capsys.readouterr().out)
    assert "manifest row_count does not match actual row count" in payload["warnings"]


def test_cli_g_compare_writes_comparison(tmp_path, monkeypatch, capsys) -> None:
    weak_path = tmp_path / "weak.json"
    strong_path = tmp_path / "strong.json"
    comparison_path = tmp_path / "comparison.json"
    markdown_path = tmp_path / "comparison.md"
    weak_path.write_text(
        json.dumps(
            g_experiment_summary(
                [
                    g_evaluation_row(y=1, p=0.9, env="C"),
                    g_evaluation_row(y=0, p=0.1, env="C"),
                    g_evaluation_row(y=1, p=0.6, env="K"),
                    g_evaluation_row(y=0, p=0.4, env="K"),
                ],
                manifest={"experiment_id": "weak", "evaluation_target": "recognition"},
            )
        ),
        encoding="utf-8",
    )
    strong_path.write_text(
        json.dumps(
            g_experiment_summary(
                [
                    g_evaluation_row(y=1, p=0.9, env="C"),
                    g_evaluation_row(y=0, p=0.1, env="C"),
                    g_evaluation_row(y=1, p=0.9, env="K"),
                    g_evaluation_row(y=0, p=0.1, env="K"),
                ],
                manifest={"experiment_id": "strong", "evaluation_target": "recognition"},
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "g-compare",
            str(weak_path),
            str(strong_path),
            "--baseline-id",
            "weak",
            "--out",
            str(comparison_path),
            "--out-md",
            str(markdown_path),
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["summaries"][0]["experiment_id"] == "strong"
    assert comparison_path.exists()
    assert "# Epistemap G Comparison" in markdown_path.read_text(encoding="utf-8")


def test_cli_g_compare_can_require_compatible_inputs(tmp_path, monkeypatch, capsys) -> None:
    recognition_path = tmp_path / "recognition.json"
    translation_path = tmp_path / "translation.json"
    recognition_path.write_text(
        json.dumps(
            g_experiment_summary(
                [
                    g_evaluation_row(y=1, p=0.9, env="C"),
                    g_evaluation_row(y=0, p=0.1, env="C"),
                    g_evaluation_row(y=1, p=0.8, env="K"),
                    g_evaluation_row(y=0, p=0.2, env="K"),
                ],
                manifest={"experiment_id": "recognition", "evaluation_target": "recognition"},
            )
        ),
        encoding="utf-8",
    )
    translation_path.write_text(
        json.dumps(
            g_experiment_summary(
                [
                    g_evaluation_row(y=1, p=0.9, env="C"),
                    g_evaluation_row(y=0, p=0.1, env="C"),
                    g_evaluation_row(y=1, p=0.9, env="K"),
                    g_evaluation_row(y=0, p=0.1, env="K"),
                ],
                manifest={"experiment_id": "translation", "evaluation_target": "translation"},
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "g-compare",
            str(recognition_path),
            str(translation_path),
            "--require-compatible",
        ],
    )

    try:
        main()
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected incompatible comparison to exit with status 2")
    payload = json.loads(capsys.readouterr().out)
    assert "mixed evaluation targets; compare G values only with caution" in payload["warnings"]


def test_cli_detective_sidecars_writes_graphs_and_diagnostics(tmp_path, monkeypatch, capsys) -> None:
    fixture_dir = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "detective_corpus"
        / "candidates"
    )
    out_dir = tmp_path / "sidecars"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "detective-sidecars",
            str(fixture_dir / "blue-carbuncle.json"),
            str(fixture_dir / "purloined-letter-control.json"),
            "--out-dir",
            str(out_dir),
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["sidecar_count"] == 2
    assert payload["fair_play_rating_counts"] == {"fair": 1, "unfair": 1}
    assert (out_dir / "detective_corpus_sidecars.json").exists()
    assert (out_dir / "blue-carbuncle" / "epistemap_graph.json").exists()
    assert (out_dir / "purloined-letter-control" / "fair_play_diagnostic.json").exists()


def test_cli_detective_treatment_writes_manifest(tmp_path, monkeypatch, capsys) -> None:
    treatment_path = tmp_path / "detective_treatment.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "detective-treatment",
            "--experiment-id",
            "detective-fair-play-001",
            "--corpus-sidecars",
            "examples/detective_corpus/sidecars/detective_corpus_sidecars.json",
            "--out",
            str(treatment_path),
            "--name",
            "Detective fair-play pilot",
            "--created-by",
            "pytest",
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["manifest_kind"] == "epistemap_detective_treatment"
    assert payload["experiment_id"] == "detective-fair-play-001"
    assert [item["condition"] for item in payload["treatments"]] == ["plain-reading", "graph-assisted"]
    assert treatment_path.exists()


def test_cli_bayesian_assessment_writes_json_and_markdown(tmp_path, monkeypatch, capsys) -> None:
    graph_path = tmp_path / "graph.json"
    assessment_path = tmp_path / "reports" / "bayesian_assessment.json"
    markdown_path = tmp_path / "reports" / "bayesian_assessment.md"
    write_graph_bundle(
        GraphBundle(
            graph_id="cli-bayesian",
            nodes=[
                Node(id="claim::main", type="claim", title="Main claim"),
                Node(
                    id="obs::paper",
                    type="observation",
                    status="grounded",
                    metadata={"source_quality": "peer_reviewed"},
                ),
            ],
            edges=[
                Edge(
                    source="obs::paper",
                    target="claim::main",
                    type="supports_claim",
                    confidence=0.9,
                )
            ],
        ),
        graph_path,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "bayesian-assessment",
            str(graph_path),
            "--out",
            str(assessment_path),
            "--out-md",
            str(markdown_path),
            "--node-type",
            "claim",
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    written = json.loads(assessment_path.read_text(encoding="utf-8"))
    assert payload["report_kind"] == "epistemap_bayesian_assessment_report"
    assert payload["graph_id"] == "cli-bayesian"
    assert payload["summary"]["node_count"] == 1
    assert payload == written
    assert "# Epistemap Bayesian Assessment" in markdown_path.read_text(encoding="utf-8")


def test_cli_detective_g_template_writes_collection_csv(tmp_path, monkeypatch, capsys) -> None:
    diagnostic_path = tmp_path / "sidecars" / "sample" / "fair_play_diagnostic.json"
    diagnostic_path.parent.mkdir(parents=True)
    diagnostic_path.write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "claim_id": "claim::sample::false",
                        "first_decisive_evidence": {"time": "4"},
                        "rating": "fair",
                    }
                ],
                "rating": "fair",
            }
        ),
        encoding="utf-8",
    )
    corpus_path = tmp_path / "sidecars" / "detective_corpus_sidecars.json"
    corpus_path.write_text(
        json.dumps(
            {
                "sidecar_manifest_kind": "epistemap_detective_corpus_sidecars",
                "sidecars": [
                    {
                        "story_id": "story::sample",
                        "title": "Sample Story",
                        "fair_play_status": "fair_play",
                        "fair_play_rating": "fair",
                        "graph_file": "sample/epistemap_graph.json",
                        "fair_play_diagnostic_file": "sample/fair_play_diagnostic.json",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    treatment_path = tmp_path / "detective_treatment.json"
    treatment_path.write_text(
        json.dumps(
            {
                "manifest_kind": "epistemap_detective_treatment",
                "experiment_id": "detective-template",
                "evaluation_target": "detective_contradiction_recognition",
                "corpus_sidecar_manifest": str(corpus_path),
                "treatments": [{"condition": "plain-reading"}],
                "phases": ["pre-reveal", "post-reveal"],
                "fair_play_policy": {"admit_ratings": ["fair"], "control_ratings": ["unfair"]},
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "g_collection_template.csv"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "detective-g-template",
            "--treatment",
            str(treatment_path),
            "--out",
            str(output_path),
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    output = output_path.read_text(encoding="utf-8")
    assert payload["template_kind"] == "epistemap_detective_g_collection_template"
    assert payload["row_count"] == 2
    assert "claim::sample::false" in output
    assert "story_title" in output.splitlines()[0]


def test_cli_detective_anchor_template_writes_review_csv(tmp_path, monkeypatch, capsys) -> None:
    fixture_dir = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "detective_corpus"
        / "candidates"
    )
    output_path = tmp_path / "anchor_review.csv"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "detective-anchor-template",
            str(fixture_dir / "blue-carbuncle.json"),
            str(fixture_dir / "red-headed-league.json"),
            "--out",
            str(output_path),
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    output = output_path.read_text(encoding="utf-8")
    assert payload["template_kind"] == "epistemap_detective_corpus_anchor_review_template"
    assert payload["story_count"] == 2
    assert payload["row_count"] == 6
    assert "reviewed_source_quote" in output.splitlines()[0]
    assert "claim::blue-carbuncle::baker-stole-jewel" in output


def test_cli_detective_apply_anchor_review_writes_updated_annotations(tmp_path, monkeypatch, capsys) -> None:
    annotation_path = tmp_path / "annotation.json"
    annotation_path.write_text(
        json.dumps(
            {
                "annotation_kind": "epistemap_detective_story_annotation",
                "story_id": "story::sample",
                "title": "Sample",
                "narrative_unit": "scene",
                "reveal_point": 5,
                "fair_play_status": "fair_play",
                "claims": [
                    {
                        "claim_id": "claim::sample::false",
                        "text": "A false claim.",
                        "truth_status": "false",
                        "narrative_anchor": "old anchor",
                    }
                ],
                "decisive_evidence": [
                    {
                        "evidence_id": "evidence::sample::decisive",
                        "text": "Decisive evidence.",
                        "contradicts_claim_id": "claim::sample::false",
                        "available_at": 4,
                        "narrative_anchor": "old evidence anchor",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    review_path = tmp_path / "review.csv"
    review_path.write_text(
        "\n".join(
            [
                "artifact_id,review_status,reviewed_source_locator,reviewed_source_quote,reviewed_narrative_anchor,reviewer,reviewed_at",
                "claim::sample::false,reviewed,page 1,A false claim.,reviewed claim anchor,Reviewer,2026-07-04",
                "evidence::sample::decisive,reviewed,page 2,Decisive evidence.,reviewed evidence anchor,Reviewer,2026-07-04",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "reviewed"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "detective-apply-anchor-review",
            str(annotation_path),
            "--review-csv",
            str(review_path),
            "--out-dir",
            str(out_dir),
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    updated = json.loads((out_dir / "annotation.json").read_text(encoding="utf-8"))
    assert payload["report_kind"] == "epistemap_detective_anchor_review_application"
    assert payload["applied_row_count"] == 2
    assert payload["missing_row_count"] == 0
    assert updated["metadata"]["annotation_status"] == "human_anchor_reviewed"
    assert updated["claims"][0]["narrative_anchor"] == "reviewed claim anchor"
    assert updated["decisive_evidence"][0]["metadata"]["anchor_review"]["reviewer"] == "Reviewer"


def test_cli_detective_validate_g_rows_writes_report_and_can_require_pass(tmp_path, monkeypatch, capsys) -> None:
    rows_path = tmp_path / "rows.csv"
    report_path = tmp_path / "validation.json"
    rows_path.write_text(
        "\n".join(
            [
                "condition,phase,item_id,claim_id,env,y,p,response,source_anchor,recognized_at,contradiction_available_at,recognition_lag,fair_play_rating",
                "plain-reading,post-reveal,story::sample,claim::sample,K,1,0.8,recognized,scene 1,8,7,1.0,fair",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "detective-validate-g-rows",
            str(rows_path),
            "--out",
            str(report_path),
            "--require-pass",
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    written = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["summary"]["status"] == "pass"
    assert payload == written


def test_cli_detective_validate_g_rows_require_pass_exits_for_incomplete_rows(tmp_path, monkeypatch, capsys) -> None:
    rows_path = tmp_path / "rows.csv"
    rows_path.write_text(
        "\n".join(
            [
                "condition,phase,item_id,claim_id,env,y,p,source_anchor,contradiction_available_at,fair_play_rating",
                "plain-reading,pre-reveal,story::sample,claim::sample,K,,,scene 1,7,fair",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "detective-validate-g-rows",
            str(rows_path),
            "--require-pass",
        ],
    )

    try:
        main()
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("expected incomplete detective G rows to exit with status 2")
    payload = json.loads(capsys.readouterr().out)
    assert payload["summary"]["status"] == "error"


def test_cli_detective_g_manifest_writes_manifest_from_rows(tmp_path, monkeypatch, capsys) -> None:
    rows_path = tmp_path / "rows.csv"
    manifest_path = tmp_path / "g_manifest.json"
    rows_path.write_text(
        "\n".join(
            [
                "condition,phase,item_id,claim_id,env,y,p,response,source_anchor,recognized_at,contradiction_available_at,recognition_lag,fair_play_rating",
                "plain-reading,post-reveal,story::sample,claim::sample,K,1,0.8,recognized,scene 1,8,7,1.0,fair",
                "graph-assisted,post-reveal,story::sample,claim::sample,K,1,0.9,recognized,scene 1,7,7,0.0,fair",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "detective-g-manifest",
            str(rows_path),
            "--experiment-id",
            "detective-manifest",
            "--out",
            str(manifest_path),
            "--name",
            "Detective manifest",
            "--corpus",
            "detective",
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    written = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["manifest_kind"] == "epistemap_g_experiment"
    assert payload["experiment_id"] == "detective-manifest"
    assert payload["row_count"] == 2
    assert payload == written


def test_cli_detective_run_sheets_writes_manifest_and_subject_csvs(tmp_path, monkeypatch, capsys) -> None:
    template_path = tmp_path / "template.csv"
    out_dir = tmp_path / "runs"
    template_path.write_text(
        "\n".join(
            [
                "run_id,subject_id,condition,phase,item_id,claim_id,env,y,p,answer,response,source_anchor,recognized_at,contradiction_available_at,recognition_lag,fair_play_rating,experiment_id,evaluation_target,story_title,fair_play_status,graph_file,fair_play_diagnostic_file,template_role",
                ",,plain-reading,pre-reveal,story::sample,claim::sample,K,,,,,scene 1,,7,,fair,exp,detective_contradiction_recognition,Sample,fair_play,graph.json,diagnostic.json,primary",
                ",,graph-assisted,pre-reveal,story::sample,claim::sample,K,,,,,scene 1,,7,,fair,exp,detective_contradiction_recognition,Sample,fair_play,graph.json,diagnostic.json,primary",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "detective-run-sheets",
            str(template_path),
            "--out-dir",
            str(out_dir),
            "--run-id-prefix",
            "pilot",
            "--subject-prefix",
            "reader",
            "--subjects-per-condition",
            "1",
            "--condition",
            "plain-reading",
            "--seed",
            "5",
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    manifest = json.loads((out_dir / "detective_g_run_sheets.json").read_text(encoding="utf-8"))
    sheet_path = out_dir / "pilot-plain-reading-01.csv"
    sheet = sheet_path.read_text(encoding="utf-8")
    assert payload["packet_kind"] == "epistemap_detective_g_run_sheets"
    assert payload["sheet_count"] == 1
    assert payload == manifest
    assert sheet_path.exists()
    assert "pilot-plain-reading-01,reader-plain-reading-01" in sheet
    assert ",K,,,,,scene 1" in sheet


def test_cli_detective_merge_run_sheets_writes_rows_csv(tmp_path, monkeypatch, capsys) -> None:
    sheets_dir = tmp_path / "sheets"
    sheets_dir.mkdir()
    sheet_path = sheets_dir / "pilot-plain-reading-01.csv"
    output_path = tmp_path / "merged.csv"
    sheet_path.write_text(
        "\n".join(
            [
                "run_id,subject_id,condition,phase,item_id,claim_id,env,y,p,answer,response,source_anchor,recognized_at,contradiction_available_at,recognition_lag,fair_play_rating,experiment_id,evaluation_target,story_title,fair_play_status,graph_file,fair_play_diagnostic_file,template_role",
                "pilot-plain-reading-01,reader-plain-reading-01,plain-reading,pre-reveal,story::sample,claim::sample,K,,,,,scene 1,,7,,fair,exp,detective_contradiction_recognition,Sample,fair_play,graph.json,diagnostic.json,primary",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "detective-merge-run-sheets",
            str(sheets_dir),
            "--out",
            str(output_path),
            "--allow-template",
            "--require-pass",
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    merged = output_path.read_text(encoding="utf-8")
    assert payload["report_kind"] == "epistemap_detective_g_run_sheet_merge"
    assert payload["source_count"] == 1
    assert payload["validation"]["summary"]["status"] == "pass"
    assert "pilot-plain-reading-01,reader-plain-reading-01" in merged


def test_cli_detective_blind_run_sheets_writes_public_csv_and_key(tmp_path, monkeypatch, capsys) -> None:
    sheets_dir = tmp_path / "sheets"
    sheets_dir.mkdir()
    source = sheets_dir / "run-1.csv"
    out_dir = tmp_path / "blinded"
    source.write_text(
        "\n".join(
            [
                "run_id,subject_id,condition,phase,item_id,claim_id,env,y,p,answer,response,source_anchor,recognized_at,contradiction_available_at,recognition_lag,fair_play_rating,experiment_id,evaluation_target,story_title,fair_play_status,graph_file,fair_play_diagnostic_file,template_role",
                "run-1,reader-1,plain-reading,pre-reveal,story::sample,claim::sample,K,,,,,scene 1,,7,,fair,exp,detective,Sample,fair_play,graph.json,diagnostic.json,primary",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "detective-blind-run-sheets",
            str(sheets_dir),
            "--out-dir",
            str(out_dir),
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    public_csv = (out_dir / "run-1.blinded.csv").read_text(encoding="utf-8")
    assert payload["packet_kind"] == "epistemap_detective_g_blinded_run_sheets"
    assert (out_dir / "detective_g_blinding_key.json").exists()
    assert "row_key" in public_csv.splitlines()[0]
    assert "fair_play_rating" not in public_csv.splitlines()[0]
    assert "graph_file" not in public_csv.splitlines()[0]


def test_cli_detective_unblind_run_sheets_rehydrates_canonical_rows(tmp_path, monkeypatch, capsys) -> None:
    key_path = tmp_path / "key.json"
    completed_path = tmp_path / "completed.blinded.csv"
    output_path = tmp_path / "rows.csv"
    key_path.write_text(
        json.dumps(
            {
                "key_kind": "epistemap_detective_g_blinding_key",
                "rows_by_key": {
                    "run-1::001": {
                        "run_id": "run-1",
                        "subject_id": "reader-1",
                        "condition": "plain-reading",
                        "phase": "post-reveal",
                        "item_id": "story::sample",
                        "claim_id": "claim::sample",
                        "env": "K",
                        "source_anchor": "scene 1",
                        "contradiction_available_at": "7",
                        "fair_play_rating": "fair",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    completed_path.write_text(
        "\n".join(
            [
                "run_id,subject_id,story_title,phase,item_id,source_anchor,y,p,answer,response,recognized_at,row_key",
                "run-1,reader-1,Sample,post-reveal,story::sample,scene 1,1,0.8,,recognized,8,run-1::001",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "epistemap",
            "detective-unblind-run-sheets",
            str(completed_path),
            "--key-file",
            str(key_path),
            "--out",
            str(output_path),
            "--require-pass",
        ],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    output = output_path.read_text(encoding="utf-8")
    assert payload["report_kind"] == "epistemap_detective_g_blinded_run_sheet_unblind"
    assert payload["validation"]["summary"]["status"] == "pass"
    assert "plain-reading" in output
    assert "1.0" in output

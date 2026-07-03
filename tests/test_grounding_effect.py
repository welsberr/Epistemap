from __future__ import annotations

import json

from epistemap import (
    Edge,
    G_ROW_FIELDS,
    GraphBundle,
    Node,
    delta_g,
    g_experiment_comparison,
    g_experiment_manifest,
    g_evaluation_row,
    g_estimate,
    g_experiment_summary,
    g_experiment_summary_from_files,
    g_rows_to_csv,
    graph_with_component_reliability,
    normalize_g_evaluation_row,
    read_g_experiment_manifest,
    read_g_rows_csv,
    reliability_level_sensitivity,
    g_summary_comparison,
    g_summary_comparison_from_files,
    write_g_experiment_manifest,
    write_g_rows_csv,
)


def _rows(*, target_confidence: float) -> list[dict]:
    return [
        {"y": 1, "p": 0.9, "env": "C"},
        {"y": 0, "p": 0.1, "env": "C"},
        {"y": 1, "p": target_confidence, "env": "K"},
        {"y": 0, "p": 1.0 - target_confidence, "env": "K"},
    ]


def test_g_estimate_combines_truth_tracking_discrimination_and_robustness() -> None:
    grounded = g_estimate(_rows(target_confidence=0.9))
    uncalibrated = g_estimate(_rows(target_confidence=0.5))

    assert grounded["G"] > uncalibrated["G"]
    assert grounded["components"]["S_T"]["point"] > uncalibrated["components"]["S_T"]["point"]
    assert grounded["components"]["S_D"]["point"] == 1.0
    assert grounded["components"]["S_R"]["point"] == 1.0


def test_g_estimate_accepts_one_shot_iterables() -> None:
    rows = (row for row in _rows(target_confidence=0.9))

    estimate = g_estimate(rows)

    assert estimate["n"] == {"clean": 2, "target": 2}
    assert estimate["G"] > 0


def test_delta_g_reports_normalized_gain() -> None:
    effect = delta_g(_rows(target_confidence=0.5), _rows(target_confidence=0.9))

    assert effect["delta_G"] > 0
    assert effect["normalized_delta_G"] > 0
    assert effect["before"]["G"] < effect["after"]["G"]


def test_g_evaluation_row_normalizes_and_preserves_temporal_fields() -> None:
    row = g_evaluation_row(
        y=True,
        p=0.85,
        env="K",
        run_id="run-1",
        subject_id="reader-7",
        condition="kg-assisted",
        item_id="story-3",
        claim_id="claim::alibi",
        recognized_at=42,
        contradiction_available_at=37,
        recognition_lag=5,
        fair_play_rating="available_before_reveal",
        metadata={"genre": "detective"},
    )

    assert row["y"] == 1
    assert row["p"] == 0.85
    assert row["recognition_lag"] == 5
    assert row["fair_play_rating"] == "available_before_reveal"
    assert row["genre"] == "detective"
    assert g_estimate([{"y": 1, "p": 0.9, "env": "C"}, {"y": 0, "p": 0.1, "env": "C"}, row])["n"]["target"] == 1


def test_normalize_g_evaluation_row_accepts_mapping_rows() -> None:
    row = normalize_g_evaluation_row(
        {"y": 0, "p": "0.2", "env": "K", "claim_id": "claim::x", "corpus": "bench"}
    )

    assert row["y"] == 0
    assert row["p"] == 0.2
    assert row["claim_id"] == "claim::x"
    assert row["corpus"] == "bench"


def test_g_rows_to_csv_uses_stable_header_with_extra_fields() -> None:
    rows = [
        g_evaluation_row(y=1, p=0.9, env="C", claim_id="claim::true", metadata={"corpus": "bench"}),
        g_evaluation_row(y=0, p=0.1, env="K", claim_id="claim::false", metadata={"corpus": "bench"}),
    ]

    csv_text = g_rows_to_csv(rows)

    assert csv_text.splitlines()[0].split(",")[: len(G_ROW_FIELDS)] == list(G_ROW_FIELDS)
    assert "corpus" in csv_text.splitlines()[0]
    assert "claim::true" in csv_text


def test_write_g_rows_csv_writes_to_path(tmp_path) -> None:
    destination = tmp_path / "g-rows.csv"

    write_g_rows_csv(
        [g_evaluation_row(y=1, p=0.9, env="K", metadata={"source": "story, chapter 4"})],
        destination,
    )

    assert destination.read_text(encoding="utf-8").startswith("run_id,subject_id,condition")
    assert '"story, chapter 4"' in destination.read_text(encoding="utf-8")


def test_read_g_rows_csv_round_trips_rows(tmp_path) -> None:
    destination = tmp_path / "g-rows.csv"
    write_g_rows_csv(
        [
            g_evaluation_row(y=1, p=0.9, env="C", condition="plain", metadata={"source": "chapter 1"}),
            g_evaluation_row(y=0, p=0.2, env="K", condition="plain", metadata={"source": "chapter 2"}),
        ],
        destination,
    )

    rows = read_g_rows_csv(destination)

    assert rows[0]["y"] == 1
    assert rows[0]["p"] == 0.9
    assert rows[1]["env"] == "K"
    assert rows[1]["source"] == "chapter 2"


def test_g_experiment_manifest_records_row_context(tmp_path) -> None:
    manifest = g_experiment_manifest(
        experiment_id="detective-fair-play-001",
        name="Detective fair-play recognition",
        row_file="g_rows.csv",
        evaluation_target="contradiction_recognition",
        corpus="open-detective-fiction",
        conditions=["plain-reading", "kg-assisted"],
        phases=["chapter", "denouement"],
        reliability_treatment="source-visible",
        temporal_assumptions={"clock": "narrative_order"},
        fair_play_policy={"requires_prior_decisive_evidence": True},
        row_count=12,
        metadata={"reviewer": "human"},
    )
    destination = tmp_path / "manifest.json"

    write_g_experiment_manifest(manifest, destination)

    text = destination.read_text(encoding="utf-8")
    assert manifest["manifest_kind"] == "epistemap_g_experiment"
    assert manifest["conditions"] == ["plain-reading", "kg-assisted"]
    assert manifest["fair_play_policy"]["requires_prior_decisive_evidence"] is True
    assert '"row_file": "g_rows.csv"' in text
    assert read_g_experiment_manifest(destination)["experiment_id"] == "detective-fair-play-001"


def test_g_experiment_summary_groups_rows_by_condition() -> None:
    rows = [
        g_evaluation_row(y=1, p=0.9, env="C", condition="plain"),
        g_evaluation_row(y=0, p=0.1, env="C", condition="plain"),
        g_evaluation_row(y=1, p=0.6, env="K", condition="plain"),
        g_evaluation_row(y=0, p=0.4, env="K", condition="plain"),
        g_evaluation_row(y=1, p=0.9, env="C", condition="kg"),
        g_evaluation_row(y=0, p=0.1, env="C", condition="kg"),
        g_evaluation_row(y=1, p=0.9, env="K", condition="kg"),
        g_evaluation_row(y=0, p=0.1, env="K", condition="kg"),
    ]

    summary = g_experiment_summary(
        rows,
        manifest={"experiment_id": "detective-fair-play-001"},
        group_by="condition",
    )

    assert summary["summary_kind"] == "epistemap_g_experiment_summary"
    assert summary["row_count"] == 8
    assert summary["manifest"]["experiment_id"] == "detective-fair-play-001"
    assert summary["groups"]["kg"]["G"] > summary["groups"]["plain"]["G"]
    assert "not a source-truth" in summary["interpretation"]


def test_g_experiment_summary_from_files_writes_summary(tmp_path) -> None:
    rows_path = tmp_path / "g_rows.csv"
    manifest_path = tmp_path / "g_manifest.json"
    summary_path = tmp_path / "nested" / "g_summary.json"
    rows = [
        g_evaluation_row(y=1, p=0.9, env="C", condition="plain"),
        g_evaluation_row(y=0, p=0.1, env="C", condition="plain"),
        g_evaluation_row(y=1, p=0.8, env="K", condition="plain"),
        g_evaluation_row(y=0, p=0.2, env="K", condition="plain"),
    ]
    manifest = g_experiment_manifest(
        experiment_id="file-summary",
        row_file="g_rows.csv",
        evaluation_target="recognition",
    )
    write_g_rows_csv(rows, rows_path)
    write_g_experiment_manifest(manifest, manifest_path)

    summary = g_experiment_summary_from_files(rows_path, manifest_json=manifest_path, out_json=summary_path)

    assert summary["manifest"]["experiment_id"] == "file-summary"
    assert summary_path.exists()


def test_g_summary_comparison_ranks_experiments_against_baseline() -> None:
    weak = g_experiment_summary(
        _rows(target_confidence=0.6),
        manifest={"experiment_id": "plain", "name": "Plain reading", "evaluation_target": "recognition"},
    )
    strong = g_experiment_summary(
        _rows(target_confidence=0.9),
        manifest={"experiment_id": "kg", "name": "KG assisted", "evaluation_target": "recognition"},
    )

    comparison = g_summary_comparison([weak, strong], baseline_id="plain")

    assert comparison["comparison_kind"] == "epistemap_g_summary_comparison"
    assert comparison["baseline_id"] == "plain"
    assert comparison["summaries"][0]["experiment_id"] == "kg"
    assert comparison["summaries"][0]["rank"] == 1
    assert comparison["summaries"][0]["delta_from_baseline"] > 0
    assert "not a source-truth" in comparison["interpretation"]


def test_g_summary_comparison_from_files_writes_comparison(tmp_path) -> None:
    weak_path = tmp_path / "weak.json"
    strong_path = tmp_path / "strong.json"
    comparison_path = tmp_path / "comparison.json"
    weak = g_experiment_summary(
        _rows(target_confidence=0.6),
        manifest={"experiment_id": "plain", "evaluation_target": "recognition"},
    )
    strong = g_experiment_summary(
        _rows(target_confidence=0.9),
        manifest={"experiment_id": "kg", "evaluation_target": "recognition"},
    )
    weak_path.write_text(json.dumps(weak), encoding="utf-8")
    strong_path.write_text(json.dumps(strong), encoding="utf-8")

    comparison = g_summary_comparison_from_files([weak_path, strong_path], baseline_id="plain", out_json=comparison_path)

    assert comparison["summaries"][0]["experiment_id"] == "kg"
    assert comparison_path.exists()


def test_g_experiment_comparison_builds_summaries_from_rows() -> None:
    comparison = g_experiment_comparison(
        [
            {
                "manifest": {"experiment_id": "plain", "evaluation_target": "recognition"},
                "rows": _rows(target_confidence=0.55),
            },
            {
                "manifest": {"experiment_id": "kg", "evaluation_target": "recognition"},
                "rows": _rows(target_confidence=0.9),
            },
        ],
        baseline_id="plain",
    )

    assert comparison["group_by"] == "condition"
    assert comparison["summaries"][0]["experiment_id"] == "kg"
    assert comparison["summaries"][0]["delta_from_baseline"] > 0


def test_g_summary_comparison_preserves_metric_warnings() -> None:
    summary = g_experiment_summary(
        [g_evaluation_row(y=1, p=0.8, env="K", condition="target-only")],
        manifest={"experiment_id": "target-only", "evaluation_target": "recognition"},
    )

    comparison = g_summary_comparison([summary])

    assert comparison["summaries"][0]["warning"] == "both clean and target environments are required"


def test_reliability_level_sensitivity_is_counterfactual_not_verdict() -> None:
    sensitivity = reliability_level_sensitivity(
        {
            "low": _rows(target_confidence=0.55),
            "high": _rows(target_confidence=0.9),
        },
        baseline_level="low",
    )

    assert sensitivity["baseline_level"] == "low"
    assert sensitivity["effects"]["high"]["delta_from_baseline"] > 0
    assert "not a truth score" in sensitivity["interpretation"]


def test_graph_with_component_reliability_sets_counterfactual_metadata_on_copy() -> None:
    bundle = GraphBundle(
        nodes=[Node(id="claim::a", type="claim"), Node(id="source::s", type="source")],
        edges=[Edge(id="edge::support", source="source::s", target="claim::a", type="supports")],
    )

    changed_node = graph_with_component_reliability(bundle, "claim::a", "low")
    changed_edge = graph_with_component_reliability(bundle, "edge::support", 0.25)

    assert bundle.nodes[0].metadata == {}
    assert changed_node.nodes[0].metadata["counterfactual_reliability"] == "low"
    assert changed_edge.edges[0].metadata["counterfactual_reliability"] == 0.25
    assert changed_edge.metadata["counterfactuals"][0]["component_found"] is True

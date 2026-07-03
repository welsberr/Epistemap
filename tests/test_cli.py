from __future__ import annotations

import json
import sys
from pathlib import Path

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
